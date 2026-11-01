"""NLI stage tests. Owner: P4 (FR-27)."""

from __future__ import annotations

import pytest

from verifact.config import VerificationSettings
from verifact.verification.nli import _lexical_nli, infer, load_nli

PREMISE = "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France."

LEXICAL = VerificationSettings(backend="lexical")


def test_lexical_entailment() -> None:
    result = _lexical_nli(PREMISE, "The Eiffel Tower is located in Paris.")
    assert result.entail > result.contra
    assert result.backend == "lexical"


def test_lexical_detects_explicit_negation() -> None:
    result = _lexical_nli(PREMISE, "The Eiffel Tower is not located in Paris.")
    assert result.contra > result.entail


def test_lexical_entity_substitution_is_neutral_not_contradiction() -> None:
    """Regression for EA-06, and the project's core principle in miniature.

    "located in Berlin" shares nearly every token with a passage about Paris.
    Scoring it as contradiction would be inferring falsehood from the absence of
    "Berlin" in the passage, so the correct answer is neutral. The consequence -
    this backend under-detects contradictions - is the safe direction.
    """
    result = _lexical_nli(PREMISE, "The Eiffel Tower is located in Berlin.")
    assert result.neutral > max(result.entail, result.contra)
    assert result.contra == 0.0


def test_lexical_irrelevant_premise_is_neutral() -> None:
    result = _lexical_nli(PREMISE, "Water boils at 100 degrees Celsius.")
    assert result.neutral == 1.0


def test_lexical_numeric_conflict_is_contradiction() -> None:
    result = _lexical_nli("The tower is 330 metres tall.", "The tower is 500 metres tall.")
    assert result.contra > 0.0


def test_probabilities_are_bounded() -> None:
    for hypothesis in [
        "The Eiffel Tower is located in Paris.",
        "Water boils at 100 degrees Celsius.",
        "",
    ]:
        result = _lexical_nli(PREMISE, hypothesis)
        for value in result.as_tuple():
            assert 0.0 <= value <= 1.0


def test_empty_premise_list_returns_empty() -> None:
    assert infer([], "any claim", LEXICAL) == []


def test_lexical_backend_is_used_when_requested() -> None:
    results = infer([PREMISE], "The Eiffel Tower is located in Paris.", LEXICAL)
    assert results[0].backend == "lexical"


@pytest.mark.ml
def test_label_map_is_read_from_the_model_not_assumed() -> None:
    """A wrong label order would invert every verdict while all plumbing passed.

    cross-encoder/nli-deberta-v3-small orders its labels
    {0: contradiction, 1: entailment, 2: neutral} - neither alphabetical nor the
    intuitive order - so the mapping must come from the model's own config.
    """
    from verifact.verification.nli import _label_indices

    model = load_nli(VerificationSettings().nli_model)
    assert model is not None, "ml marker implies the model is installed"
    idx = _label_indices(model)
    assert set(idx) == {"entail", "contra", "neutral"}
    id2label = {int(k): str(v).lower() for k, v in model.model.config.id2label.items()}
    assert id2label[idx["entail"]].startswith("entail")
    assert id2label[idx["contra"]].startswith("contradict")


@pytest.mark.ml
def test_transformer_separates_support_from_contradiction() -> None:
    cfg = VerificationSettings(backend="transformer")
    supported = infer([PREMISE], "The Eiffel Tower is located in Paris.", cfg)[0]
    contradicted = infer([PREMISE], "The Eiffel Tower is located in Berlin.", cfg)[0]
    assert supported.entail > 0.8
    assert contradicted.contra > 0.8


@pytest.mark.ml
def test_premise_hypothesis_order_matters() -> None:
    """FR-27. Reversing the pair asks a different question, so the order is asserted.

    A comment would not have caught a reversal; this does.
    """
    cfg = VerificationSettings(backend="transformer")
    claim = "The Eiffel Tower is in Paris."
    correct = infer([PREMISE], claim, cfg)[0]
    reversed_pair = infer([claim], PREMISE, cfg)[0]
    assert correct.entail != reversed_pair.entail


@pytest.mark.ml
def test_known_weakness_irrelevant_premise_scores_contradiction() -> None:
    """EA-05, asserted so the limitation is a measured fact, not a vague caveat.

    The model gives contradiction ~1.0 for a passage that says nothing about the
    claim. If a future checkpoint fixes this, the test fails and the containment
    machinery (relevance weighting, the similarity gate) can be revisited.
    """
    cfg = VerificationSettings(backend="transformer")
    result = infer([PREMISE], "Water boils at 100 degrees Celsius.", cfg)[0]
    assert result.contra > result.neutral, (
        "expected the documented pathology; if this now passes correctly, "
        "update EA-05 and reconsider tau_sim"
    )
