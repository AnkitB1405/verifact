"""Stage S2: natural language inference, passage against claim.

Owner: P4 (FR-27).

Direction matters and is a real source of bugs: the **passage is the premise**
and the **claim is the hypothesis**. Asking "does the claim entail the passage?"
answers a different question and gives different numbers, so the order is
asserted in a test rather than trusted to a comment.

The label order is read from the model's own `id2label` and never hardcoded.
`cross-encoder/nli-deberta-v3-small` happens to order them
`{0: contradiction, 1: entailment, 2: neutral}` - not the alphabetical or
intuitive order - and a wrong assumption here would invert every verdict in the
system while leaving all the plumbing tests green.

Known weakness, measured in EA-05: this checkpoint assigns high *contradiction*
probability to passages that are merely irrelevant. The weighting stage is what
contains the damage, by multiplying every passage by its retrieval relevance.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from verifact.config import VerificationSettings, get_settings
from verifact.errors import ModelUnavailableError
from verifact.logging import get_logger
from verifact.retrieval.rankers import tokenize

_log = get_logger(__name__)

_NEGATION = frozenset(
    {
        "not",
        "no",
        "never",
        "none",
        "neither",
        "nor",
        "cannot",
        "isn't",
        "wasn't",
        "aren't",
        "weren't",
        "doesn't",
        "didn't",
        "don't",
    }
)
_NUMBER_RE = re.compile(r"\d[\d,.]*")
#: Capitalised tokens not at the start of the string: a crude named-entity proxy.
_PROPER_TOKEN_RE = re.compile(r"(?<!^)(?<![.!?]\s)\b([A-Z][a-z]{2,})")


@dataclass(frozen=True)
class NliResult:
    """One premise/hypothesis judgement."""

    entail: float
    contra: float
    neutral: float
    backend: str

    def as_tuple(self) -> tuple[float, float, float]:
        return self.entail, self.contra, self.neutral


_MODEL_CACHE: dict[str, Any] = {}


def load_nli(model_name: str) -> Any | None:
    """Load and cache a cross-encoder, or None when unavailable."""
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        _log.info("sentence-transformers not installed, NLI falling back to lexical")
        return None
    try:
        model = CrossEncoder(model_name)
    except (OSError, ValueError) as exc:
        _log.warning("NLI model unavailable", extra={"model": model_name, "error": str(exc)})
        return None
    _MODEL_CACHE[model_name] = model
    return model


def _label_indices(model: Any) -> dict[str, int]:
    """Map entailment/contradiction/neutral to this model's output positions.

    Reading the model's own config is the only safe way: checkpoints differ, and
    guessing silently inverts the system's conclusions.
    """
    id2label = getattr(model.model.config, "id2label", None) or {}
    out: dict[str, int] = {}
    for idx, label in id2label.items():
        key = str(label).strip().lower()
        if key.startswith("entail"):
            out["entail"] = int(idx)
        elif key.startswith("contradict"):
            out["contra"] = int(idx)
        elif key.startswith("neutral"):
            out["neutral"] = int(idx)
    if set(out) != {"entail", "contra", "neutral"}:
        raise ModelUnavailableError(f"NLI model does not expose a 3-way NLI label map: {id2label}")
    return out


def _softmax(row: list[float]) -> list[float]:
    top = max(row)
    exps = [math.exp(v - top) for v in row]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def _lexical_nli(premise: str, hypothesis: str) -> NliResult:
    """Deterministic, dependency-free stand-in for an NLI model.

    Three signals: how much of the hypothesis is covered by the premise, whether
    their negation polarity differs, and whether their numbers disagree. It is a
    far weaker judge than a trained model, and the run's provenance records that
    it was used so a degraded result is never mistaken for a normal one.
    """
    prem_tokens = set(tokenize(premise))
    hyp_tokens = tokenize(hypothesis)
    if not hyp_tokens:
        return NliResult(0.0, 0.0, 1.0, "lexical")

    content = [t for t in hyp_tokens if t not in _NEGATION]
    covered = sum(1 for t in content if t in prem_tokens)
    coverage = covered / max(len(content), 1)

    # Entity substitution is the failure this backend is worst at. "The Eiffel
    # Tower is located in Berlin" shares almost every token with a passage about
    # Paris, so coverage alone scored it as entailed. A named entity present in
    # the hypothesis but absent from the premise means this passage simply does
    # not speak to the claim -> neutral, not contradiction. Reporting
    # contradiction here would be inferring falsehood from absence, which is the
    # one thing the whole system refuses to do.
    missing_entities = [
        tok for tok in _PROPER_TOKEN_RE.findall(hypothesis) if tok.lower() not in prem_tokens
    ]
    if missing_entities:
        return NliResult(0.0, 0.0, 1.0, "lexical")

    polarity_differs = bool(set(hyp_tokens) & _NEGATION) != bool(prem_tokens & _NEGATION)
    prem_numbers = set(_NUMBER_RE.findall(premise))
    hyp_numbers = set(_NUMBER_RE.findall(hypothesis))
    numbers_conflict = bool(hyp_numbers) and bool(prem_numbers) and not (hyp_numbers & prem_numbers)

    if coverage < 0.4:
        # Not enough shared content to judge either way: neutral, not contradiction.
        return NliResult(0.0, 0.0, 1.0, "lexical")
    if polarity_differs or numbers_conflict:
        return NliResult(0.0, round(coverage, 4), round(1 - coverage, 4), "lexical")
    return NliResult(round(coverage, 4), 0.0, round(1 - coverage, 4), "lexical")


def infer(
    premises: list[str],
    hypothesis: str,
    settings: VerificationSettings | None = None,
    model_name: str | None = None,
) -> list[NliResult]:
    """3-way NLI of `hypothesis` against each premise.

    Args:
        premises: evidence passage texts.
        hypothesis: the claim being checked.
    """
    if not premises:
        return []
    cfg = settings or get_settings().verification
    name = model_name or cfg.nli_model

    model = None if cfg.backend == "lexical" else load_nli(name)
    if model is None:
        if cfg.backend == "transformer":
            raise ModelUnavailableError(f"transformer backend requested but {name} is unavailable")
        return [_lexical_nli(p, hypothesis) for p in premises]

    idx = _label_indices(model)
    # (premise, hypothesis) order: the passage is the premise.
    raw = model.predict([(p, hypothesis) for p in premises])
    out: list[NliResult] = []
    for row in raw:
        probs = _softmax([float(v) for v in row])
        out.append(
            NliResult(
                entail=round(probs[idx["entail"]], 6),
                contra=round(probs[idx["contra"]], 6),
                neutral=round(probs[idx["neutral"]], 6),
                backend=name,
            )
        )
    return out
