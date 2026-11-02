"""Integration tests across module boundaries. Owner: P1 (EPIC 9.2).

These run the real stages wired together, on the offline lexical backends with a
local corpus, so they are deterministic and need no network. They test the
things unit tests structurally cannot: that the contracts line up, that
persistence round-trips, and that one failing claim does not void a run.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from verifact.config import Settings
from verifact.contracts import RunStatus, VerdictStatus
from verifact.db import repository, session_scope
from verifact.db.models import Base
from verifact.db.session import init_engine
from verifact.input import build_document
from verifact.orchestrator import run_analysis

CORPUS = Path("tests/fixtures/local_corpus.jsonl")
ASOF = date(2026, 11, 1)
SAMPLE = (
    "The Eiffel Tower was completed in 1950. "
    "The Eiffel Tower is located in Paris. "
    "I think it is the most beautiful monument in Europe. "
    "Zqxthuloa Brennigan invented the flibbertigibbet."
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        api={"auth_enabled": False},
        retrieval={"backend": "lexical", "offline": True},
        verification={"backend": "lexical"},
        kg={"enabled": False},
    )


@pytest.fixture
def db(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = init_engine(f"sqlite+pysqlite:///{tmp_path / 'it.db'}")
    Base.metadata.create_all(engine)
    return engine


def test_pipeline_runs_end_to_end(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    doc = build_document(SAMPLE, asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)
    assert run.status is RunStatus.DONE
    assert run.claims
    assert run.verdicts
    assert run.annotated_text


def test_every_checkworthy_claim_gets_a_verdict(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    doc = build_document(SAMPLE, asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)
    checkworthy = [c for c in run.claims if c.checkworthy]
    assert len(run.verdicts) == len(checkworthy)
    assert {v.claim_id for v in run.verdicts} == {c.id for c in checkworthy}


def test_opinions_are_kept_but_not_verified(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    """The dashboard needs to show what was skipped and why."""
    doc = build_document(SAMPLE, asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)
    skipped = [c for c in run.claims if not c.checkworthy]
    assert skipped
    verdict_ids = {v.claim_id for v in run.verdicts}
    assert all(c.id not in verdict_ids for c in skipped)


def test_fabricated_claim_is_not_contradicted(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    """FR-30 across the whole wired pipeline."""
    doc = build_document("Zqxthuloa Brennigan invented the flibbertigibbet in 1623.", asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)
    assert all(v.status is not VerdictStatus.CONTRADICTED for v in run.verdicts)


def test_results_round_trip_through_the_database(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    """FR-61: what comes back out must match what went in."""
    doc = build_document(SAMPLE, asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)
    with session_scope() as session:
        loaded = repository.load_run(session, run.id)
    assert loaded.id == run.id
    assert loaded.status is RunStatus.DONE
    assert len(loaded.claims) == len(run.claims)
    assert len(loaded.verdicts) == len(run.verdicts)
    assert loaded.annotated_text == run.annotated_text
    original = {v.claim_id: v.status for v in run.verdicts}
    reloaded = {v.claim_id: v.status for v in loaded.verdicts}
    assert original == reloaded


def test_component_scores_survive_persistence(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    """FR-31 end to end: scores are useless if the database drops them."""
    doc = build_document("The Eiffel Tower is 330 metres tall.", asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)
    with session_scope() as session:
        loaded = repository.load_run(session, run.id)
    before = run.verdicts[0].component_scores
    after = loaded.verdicts[0].component_scores
    assert before == after


def test_provenance_is_persisted(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    doc = build_document(SAMPLE, asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)
    with session_scope() as session:
        loaded = repository.load_run(session, run.id)
    assert loaded.provenance is not None
    assert loaded.provenance.config_hash == run.provenance.config_hash  # type: ignore[union-attr]
    assert loaded.provenance.model_versions["nli"] == "lexical-fallback"


def test_one_failing_claim_does_not_void_the_run(
    settings: Settings, db, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """The failure-isolation row of the architecture doc, actually exercised."""
    import verifact.orchestrator.pipeline as pipeline

    calls = {"n": 0}
    real = pipeline.verify_claim

    def flaky(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated stage failure")
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(pipeline, "verify_claim", flaky)
    doc = build_document(SAMPLE, asof=ASOF)
    run = run_analysis(doc, settings, corpus_path=CORPUS)

    assert run.status is RunStatus.DONE
    failed = [v for v in run.verdicts if v.error]
    assert len(failed) == 1
    assert "simulated stage failure" in (failed[0].error or "")
    # The others still completed.
    assert len([v for v in run.verdicts if not v.error]) >= 1


def test_determinism_across_runs(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    """NFR-06. Same input, same config - identical verdicts."""
    first = run_analysis(build_document(SAMPLE, asof=ASOF), settings, corpus_path=CORPUS)
    second = run_analysis(build_document(SAMPLE, asof=ASOF), settings, corpus_path=CORPUS)
    assert [c.text for c in first.claims] == [c.text for c in second.claims]
    assert [v.status for v in first.verdicts] == [v.status for v in second.verdicts]
    assert [round(v.confidence, 6) for v in first.verdicts] == [
        round(v.confidence, 6) for v in second.verdicts
    ]
    assert first.annotated_text == second.annotated_text


def test_config_hash_changes_when_a_decision_threshold_changes(settings: Settings) -> None:
    """A result is only reproducible if its hash tracks what can change it."""
    other = settings.model_copy(
        update={"verification": settings.verification.model_copy(update={"tau_sup": 0.5})}
    )
    assert settings.config_hash() != other.config_hash()


def test_config_hash_ignores_operational_settings(settings: Settings) -> None:
    """Changing the log level must not mark every past result irreproducible."""
    noisier = settings.model_copy(
        update={"log": settings.log.model_copy(update={"level": "DEBUG"})}
    )
    assert settings.config_hash() == noisier.config_hash()


def test_stale_run_sweep_marks_interrupted_runs_failed(settings: Settings, db) -> None:  # type: ignore[no-untyped-def]
    """ADR-004 is explicit that a killed task is not retried; it must not hang."""
    from datetime import UTC, datetime, timedelta

    from verifact.orchestrator.pipeline import build_provenance

    doc = build_document("A fact about Paris.", asof=ASOF)
    with session_scope() as session:
        repository.create_run(session, doc, build_provenance(settings, {}))
        repository.set_run_status(session, doc.id, RunStatus.RUNNING)
    with session_scope() as session:
        swept = repository.sweep_stale_runs(session, datetime.now(UTC) + timedelta(minutes=1))
        assert swept == 1
        assert repository.load_run(session, doc.id).status is RunStatus.FAILED
