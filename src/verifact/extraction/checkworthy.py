"""Separating factual claims from opinion, instruction, question and rhetoric.

Owner: P2 (FR-09). Everything that reaches the verification engine costs
retrieval and inference, and - worse - a verdict on an opinion is meaningless.
"The film is beautiful" cannot be SUPPORTED or CONTRADICTED by evidence.

Deliberately biased towards keeping claims. A false negative here (a real claim
dropped) is invisible: the claim silently never gets verified. A false positive
(an opinion kept) is visible: it comes back UNVERIFIABLE, which is the correct
answer for a subjective statement anyway. Measured rates for both directions go
in the test report rather than being assumed.
"""

from __future__ import annotations

import re

from verifact.contracts import ClaimType

#: First-person and evaluative stance markers.
_OPINION_MARKERS = frozenset(
    {
        "believe",
        "believes",
        "believed",
        "think",
        "thinks",
        "thought",
        "feel",
        "feels",
        "suppose",
        "guess",
        "reckon",
        "doubt",
        "hope",
        "fear",
        "prefer",
        "love",
        "hate",
        "seems",
        "seem",
        "seemed",
        "appears",
        "arguably",
        "presumably",
        "supposedly",
    }
)

#: Evaluative adjectives and adverbs: not verifiable against a source.
_EVALUATIVE = frozenset(
    {
        "beautiful",
        "ugly",
        "best",
        "worst",
        "greatest",
        "terrible",
        "wonderful",
        "amazing",
        "awful",
        "boring",
        "exciting",
        "interesting",
        "brilliant",
        "stupid",
        "elegant",
        "clumsy",
        "delicious",
        "disgusting",
        "overrated",
        "underrated",
        "impressive",
        "disappointing",
        "remarkable",
        "fascinating",
        "important",
    }
)

#: Normative modals: a statement about what *ought* to be, not what *is*.
_NORMATIVE = frozenset({"should", "ought", "must", "shall", "deserve", "deserves"})

_RHETORICAL_OPENERS = (
    "of course",
    "needless to say",
    "as everyone knows",
    "it goes without saying",
    "obviously",
    "clearly",
    "undoubtedly",
    "let us be honest",
    "let's be honest",
)

_FIRST_PERSON = re.compile(r"\b(i|we|my|our|me|us)\b", re.I)
_FINITE_VERB_HINT = re.compile(
    r"\b(is|are|was|were|has|have|had|does|do|did|can|could|will|would|may|might|"
    r"became|becomes|contains|includes|won|lost|founded|created|born|died|opened|"
    r"published|discovered|invented|launched|measures|equals|boils|melts)\b",
    re.I,
)


def classify(text: str, spacy_sent: object | None = None) -> tuple[ClaimType, bool]:
    """Return `(claim_type, checkworthy)` for one proposition.

    Args:
        text: the proposition text.
        spacy_sent: a parsed span, used only to detect an imperative reliably.
    """
    stripped = text.strip()
    low = stripped.lower()
    words = set(re.findall(r"[a-z']+", low))

    if stripped.endswith("?"):
        return ClaimType.QUESTION, False

    if any(low.startswith(opener) for opener in _RHETORICAL_OPENERS):
        return ClaimType.RHETORICAL, False

    if words & _NORMATIVE:
        # "Vaccines should be free" is a value judgement, not a fact to check.
        return ClaimType.OPINION, False

    if words & _OPINION_MARKERS or words & _EVALUATIVE:
        return ClaimType.OPINION, False

    if _FIRST_PERSON.search(low) and not _FINITE_VERB_HINT.search(low):
        return ClaimType.OPINION, False

    if _is_imperative(stripped, spacy_sent):
        return ClaimType.INSTRUCTION, False

    # A fragment with no verb asserts nothing ("The Eiffel Tower in Paris").
    if not _has_verb(stripped, spacy_sent):
        return ClaimType.RHETORICAL, False

    return ClaimType.FACTUAL, True


def _is_imperative(text: str, spacy_sent: object | None) -> bool:
    if spacy_sent is not None:
        toks = [t for t in spacy_sent if not t.is_punct]  # type: ignore[attr-defined]
        if toks and toks[0].pos_ == "VERB" and toks[0].tag_ == "VB":
            has_subject = any(t.dep_ in ("nsubj", "nsubjpass") for t in spacy_sent)  # type: ignore[attr-defined]
            return not has_subject
        return False
    first = re.findall(r"[A-Za-z']+", text)
    if not first:
        return False
    return first[0].lower() in {
        "note",
        "see",
        "consider",
        "remember",
        "ignore",
        "click",
        "install",
        "run",
        "add",
        "remove",
        "use",
        "try",
        "check",
        "ensure",
        "do",
        "don't",
        "please",
    }


def _has_verb(text: str, spacy_sent: object | None) -> bool:
    if spacy_sent is not None:
        return any(t.pos_ in ("VERB", "AUX") for t in spacy_sent)  # type: ignore[attr-defined]
    return bool(_FINITE_VERB_HINT.search(text))
