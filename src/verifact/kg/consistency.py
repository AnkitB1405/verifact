"""Knowledge-graph consistency checking: the `KGCheck` producer.

Owner: P3 (FR-23, FR-24, FR-25).

The single most important rule in this module, and arguably in the project:

    **An absent relation yields MISSING, never CONTRADICTED.**

Wikidata not holding a fact is silence, not denial. `shiralkar2017streams` is
limited precisely by conflating the two: a sparse region of the graph gives a
low score for a true fact. Our aggregation rule therefore never lets MISSING
contribute to a CONTRADICTED verdict.

Disambiguation is done **by relation, not by popularity**. When a mention is
ambiguous, every candidate sense is tried, and:

* any candidate for which the relation holds  -> SUPPORTED. The claim asserts
  something true of one sense, which is enough.
* every candidate carries the relation with a conflicting value -> CONTRADICTED.
  Contradiction requires that *no* reading of the mention satisfies the claim.
* no candidate carries the relation at all -> MISSING.

That ordering means ambiguity can never manufacture a false CONTRADICTED, which
is the failure mode we care most about avoiding.
"""

from __future__ import annotations

from verifact.config import KGSettings, get_settings
from verifact.contracts import Claim, Entity, KGCheck, KGStatus, Triple
from verifact.errors import RetrievalError
from verifact.kg.linking import link_entity
from verifact.kg.predicates import Predicate, get_predicates
from verifact.kg.subgraph import build_subgraph, labelled_path, reaches
from verifact.logging import get_logger
from verifact.retrieval.clients import wikidata
from verifact.retrieval.clients.http import SafeClient

_log = get_logger(__name__)

#: How many senses of an ambiguous subject to try. Bounds cost; the calls are
#: cached, so a repeat run is free.
MAX_SUBJECT_CANDIDATES = 3


def _subject_for(claim: Claim, predicate: Predicate) -> Entity | None:
    """The entity acting as the relation's subject.

    The subject is the entity immediately *before* the relation phrase, not
    simply the first entity in the claim. In "Python was created by Guido van
    Rossum" only "Guido van Rossum" may be recognised by NER, and treating it as
    the subject asks the graph whether Guido has a creator - which returns
    MISSING and quietly checks the wrong thing.
    """
    span = predicate.match_span(claim.text)
    ordered = sorted(claim.entities, key=lambda e: e.char_start)
    if span is None:
        return ordered[0] if ordered else None
    before = [e for e in ordered if e.char_start < span[0]]
    if before:
        return before[-1]
    # No recognised entity before the relation: use the text preceding it as a
    # surface form, so the subject is still the right side of the sentence.
    head = claim.text[: span[0]].strip().strip(",")
    if not head:
        return None
    return Entity(surface=head, char_start=0, char_end=len(head), label="INFERRED")


def _objects_for(claim: Claim, predicate: Predicate) -> list[Entity]:
    """Entities after the relation phrase - the candidate objects."""
    span = predicate.match_span(claim.text)
    ordered = sorted(claim.entities, key=lambda e: e.char_start)
    if span is None:
        return ordered[1:]
    after = [e for e in ordered if e.char_start >= span[1]]
    return after or ordered[1:]


def _not_applicable(claim: Claim, note: str) -> KGCheck:
    return KGCheck(claim_id=claim.id, status=KGStatus.NOT_APPLICABLE, notes=note)


def _year(iso: str) -> str | None:
    """Leading year of an ISO-ish string, including Wikidata's '+1889-01-01T..'."""
    cleaned = iso.lstrip("+")
    head = cleaned.split("-")[0]
    return head if head.isdigit() and len(head) == 4 else None


def _quantity_matches(claimed: float, amount: str, tolerance: float) -> bool:
    try:
        actual = float(amount.lstrip("+"))
    except ValueError:
        return False
    scale = max(abs(actual), 1.0)
    return abs(actual - claimed) / scale <= tolerance


def _compare_time(values: list[dict[str, str]], claimed_iso: str) -> tuple[bool, str]:
    want = _year(claimed_iso)
    if want is None:
        return False, "claim date not parseable to a year"
    for value in values:
        if value.get("type") != "time":
            continue
        got = _year(str(value.get("time", "")))
        if got == want:
            return True, f"graph date {got} matches the claim"
    seen = [_year(str(v.get("time", ""))) or "?" for v in values if v.get("type") == "time"]
    return False, f"claim says {want}, graph holds {seen}"


def _compare_quantity(
    values: list[dict[str, str]], claimed: float, tolerance: float
) -> tuple[bool, str]:
    amounts = [str(v.get("amount", "")) for v in values if v.get("type") == "quantity"]
    # Wikidata often holds several values for one property (the Eiffel Tower is
    # 300 m, 324 m or 330 m depending on the antenna). Report the closest match
    # rather than the first, so the explanation names the value that justified
    # the verdict.
    best: tuple[float, str] | None = None
    for amount in amounts:
        try:
            actual = float(amount.lstrip("+"))
        except ValueError:
            continue
        error = abs(actual - claimed) / max(abs(actual), 1.0)
        if best is None or error < best[0]:
            best = (error, amount)
    if best is not None and best[0] <= tolerance:
        return True, f"graph value {best[1]} matches {claimed} within {tolerance:.0%}"
    return False, f"claim says {claimed}, graph holds {amounts}"


def _compare_entity(
    client: SafeClient,
    subject_qid: str,
    values: list[dict[str, str]],
    object_surface: str,
    predicate: Predicate,
    cfg: KGSettings,
) -> tuple[bool, str, list[list[str]]]:
    """Does the relation point at the claimed object, directly or transitively?"""
    object_link = link_entity(client, object_surface)
    targets = object_link.candidates or ([object_link.qid] if object_link.qid else [])
    if not targets:
        return False, f"object {object_surface!r} could not be linked", []

    direct = {str(v["qid"]) for v in values if v.get("type") == "entity" and v.get("qid")}
    hit = direct & set(targets)
    if hit:
        qid = sorted(hit)[0]
        return True, f"direct statement to {qid}", [[subject_qid, qid]]

    if predicate.transitive:
        graph = build_subgraph(client, subject_qid, predicate.pids, cfg)
        for target in targets:
            path = reaches(graph, subject_qid, target, cfg.max_hops)
            if path:
                return (
                    True,
                    f"reached {target} in {len(path) - 1} hops",
                    [labelled_path(graph, path)],
                )

    return False, f"relation points to {sorted(direct)}, not to {targets[:3]}", []


def _check_one_subject(
    client: SafeClient,
    subject_qid: str,
    predicate: Predicate,
    claim: Claim,
    cfg: KGSettings,
) -> tuple[KGStatus, str, list[list[str]]]:
    """Evaluate the claim against one candidate sense of the subject."""
    try:
        entity = wikidata.fetch_entity(client, subject_qid)
    except RetrievalError as exc:
        return KGStatus.NOT_APPLICABLE, f"subject {subject_qid} unavailable: {exc}", []

    statements = wikidata.statements(entity)
    values = [v for pid in predicate.pids for v in statements.get(pid, [])]
    label = wikidata.label_of(entity) or subject_qid
    if not values:
        # The decisive branch: silence, not denial.
        return (
            KGStatus.MISSING,
            f"{label} ({subject_qid}) has no {predicate.name} statement "
            f"({'/'.join(predicate.pids)}); absence is not contradiction",
            [],
        )

    if predicate.value_type == "time":
        dates = [t.iso for t in claim.temporal if t.iso]
        if not dates:
            return KGStatus.NOT_APPLICABLE, "claim has no parseable date to compare", []
        ok, note = _compare_time(values, dates[0])
        return (KGStatus.SUPPORTED if ok else KGStatus.CONTRADICTED), f"{label}: {note}", []

    if predicate.value_type == "quantity":
        numbers = [n.value for n in claim.numerics if n.value is not None]
        if not numbers:
            return KGStatus.NOT_APPLICABLE, "claim has no numeric value to compare", []
        ok, note = _compare_quantity(values, numbers[0], predicate.tolerance)
        return (KGStatus.SUPPORTED if ok else KGStatus.CONTRADICTED), f"{label}: {note}", []

    objects = _objects_for(claim, predicate)
    if not objects:
        return KGStatus.NOT_APPLICABLE, "claim names no object entity to compare", []
    ok, note, paths = _compare_entity(
        client, subject_qid, values, objects[0].surface, predicate, cfg
    )
    return (KGStatus.SUPPORTED if ok else KGStatus.CONTRADICTED), f"{label}: {note}", paths


def check_claim(
    claim: Claim,
    client: SafeClient | None = None,
    settings: KGSettings | None = None,
) -> KGCheck:
    """Check one claim against the knowledge graph.

    Returns NOT_APPLICABLE when the claim's relation is outside the supported
    predicate set, when the subject cannot be linked, or when the comparison
    cannot be made. None of those are evidence against the claim.
    """
    cfg = settings or get_settings().kg
    if not cfg.enabled:
        return _not_applicable(claim, "kg checking disabled by configuration")

    predicate = get_predicates().find(claim.text)
    if predicate is None:
        return _not_applicable(claim, "no supported predicate matches this claim")
    if not claim.entities:
        return _not_applicable(claim, "claim names no entity to use as subject")

    own_client = client is None
    client = client or SafeClient()
    try:
        subject = _subject_for(claim, predicate)
        if subject is None:
            return _not_applicable(claim, "could not identify the relation's subject")
        link = link_entity(client, subject.surface)
        senses = (link.candidates or ([link.qid] if link.qid else []))[:MAX_SUBJECT_CANDIDATES]
        if not senses:
            return _not_applicable(claim, f"subject {subject.surface!r} could not be linked")

        results: list[tuple[KGStatus, str, list[list[str]]]] = [
            _check_one_subject(client, qid, predicate, claim, cfg) for qid in senses
        ]

        triples = [
            Triple(
                subject=subject.surface,
                predicate=predicate.name,
                object=(
                    _objects_for(claim, predicate)[0].surface
                    if predicate.value_type == "entity" and _objects_for(claim, predicate)
                    else (
                        claim.temporal[0].surface
                        if predicate.value_type == "time" and claim.temporal
                        else (claim.numerics[0].surface if claim.numerics else "")
                    )
                ),
                subject_qid=senses[0],
            )
        ]

        # Any sense satisfying the relation is enough; contradiction requires
        # that every sense carrying the relation conflicts.
        supported = [r for r in results if r[0] is KGStatus.SUPPORTED]
        contradicted = [r for r in results if r[0] is KGStatus.CONTRADICTED]
        missing = [r for r in results if r[0] is KGStatus.MISSING]

        if supported:
            status, note, paths = supported[0]
        elif contradicted and not missing:
            status, note, paths = contradicted[0]
            if len(contradicted) > 1:
                note = f"all {len(contradicted)} candidate senses conflict; " + note
        elif missing:
            status, note, paths = missing[0]
        else:
            status, note, paths = results[0]

        if link.ambiguous and status is KGStatus.CONTRADICTED:
            note = f"[subject was ambiguous: {link.candidates[:3]}] {note}"

        _log.info(
            "kg check complete",
            extra={
                "claim_id": claim.id,
                "predicate": predicate.name,
                "status": status.value,
                "n_senses_tried": len(senses),
            },
        )
        return KGCheck(
            claim_id=claim.id,
            status=status,
            triples_checked=triples,
            path_evidence=paths,
            notes=note,
        )
    finally:
        if own_client:
            client.close()
