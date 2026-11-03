# Verification Engine

**Owner:** P4 (Bhavish) · **Code:** `src/verifact/verification/` · **Requirements:** FR-26…FR-34
**Decisions:** ADR-001, ADR-005 · **Produces:** `Verdict`

## What it does

Runs five stages over a claim and its evidence, and maps the result onto one of
six statuses with a confidence and every component score retained.

```
S1 similarity   is this passage even about the claim?
S2 NLI          does the passage entail or contradict it?
S3 KG check     does the graph hold the relation?           (P3's module)
S4 weighting    how much is each passage worth?
S5 aggregation  which of the six statuses, and why?
```

## Why it exists

This is where the project's claimed contribution lives. The gap matrix shows no
surveyed system weights evidence by **source reliability** or **age**, calibrates
its confidence, or abstains. FEVER, FEVEROUS and FActScore use Wikipedia alone;
RARR uses whatever a search returns. All treat their evidence pool as uniformly
trustworthy.

## How it works internally

**S4, the weighting formula:**

```
w_i = r(source_i) · ρ(age_i) · rel_i

  r    source base reliability from the registry, in (0, 1]
  ρ    0.5 ** (age_days / halflife_days)  — per source kind
  rel  fused retrieval relevance
```

An **undated** passage gets `ρ = 1.0` and is recorded as undated. It is never
assumed recent and never penalised: sparse metadata is a property of the
source's bookkeeping, not of the claim's support.

Near-duplicates are collapsed first, and cross-source agreement is counted **per
source, not per passage** — six paragraphs from one article are one source
agreeing, not six. That is the lesson from `kuhn2023semantic`, where counting
sequences rather than meanings overstates agreement.

**S5, aggregation:**

```
E = Σ w_i·p_entail,i / Σ w_i        C = Σ w_i·p_contra,i / Σ w_i
coverage = Σ w_i / k
```

The status rule is in `docs/architecture/system-architecture.md §6.2` and must
not diverge from the code. Three of its branches were added *after* the first
end-to-end run exposed real failures:

- `similarity_max < tau_sim → UNVERIFIABLE`. Relevance is min-max scaled per
  claim, so the best candidate always scores 1.0 and coverage could never signal
  "nothing relevant found" (EA-07). S1's docstring had always said this was its
  job; the rule simply never read it.
- **`KGCheck == SUPPORTED` is honoured.** Originally the graph was consulted only
  for contradiction, so a tier-1 structured confirmation was overridable by text
  NLI — which returned `CONTRADICTED` for Marie Curie's 1903 Physics prize while
  the graph confirmed it.
- **Graph-versus-text disagreement → `AMBIGUOUS`**, not `CONTRADICTED`. Asserting
  contradiction while our most reliable source confirms the claim is the failure
  this project exists to avoid.

`MISSING` appears nowhere in the rule, by design.

**Confidence comes from the branch that decided the verdict**, not from one
global formula. A graph-decided verdict takes the knowledge base's own
reliability, because a graph statement is categorical and the uncertainty lives
in the source; an NLI-decided verdict takes `|E − C|`; disagreement takes
`min(E, C)`; an unresolved reference takes 1.0, because that is not a statistical
judgement at all. Before this, the explanation said "decided by kg_consistency"
while the number described the text margin — and the corrector then abstained on
a verdict it should have acted on.

**Calibration** (ADR-005): `|E − C|` passed through a temperature fitted on a
held-out split by grid search *on ECE* — minimising the metric we report rather
than claiming an improvement on a different objective. `Verdict.calibrated` is
`True` **only** when a fitted calibrator actually loaded from disk. `UNVERIFIABLE`
and `INSUFFICIENT_EVIDENCE` are left uncalibrated: their confidence describes
retrieval, not the claim.

**Adaptive budget** (H2): pass 1 is `top_k=3` with the small model. A claim is
escalated only when the margin sits near a threshold, the claim carries a number
or a date, or sources disagree. `budget_spent` is recorded on every verdict,
which is what makes the cost/accuracy curve measurable rather than asserted.

## What alternatives exist

| Alternative | Why not |
|---|---|
| Learned aggregator (KGAT-style) | would likely be more accurate; needs FEVER-scale supervision and replaces a formula we can defend with a black box we cannot |
| LLM-as-judge | unauditable, uncalibrated, non-reproducible — rejected on principle in ADR-001, not on cost |
| Report raw `\|E − C\|` as a probability | the specific thing the brief forbids, and the most obvious line of attack |
| Ask the model for its confidence (`tian2023justask`) | model self-opinion with no evidence behind it |
| One global confidence formula | incoherent once different branches decide different verdicts |

## What could go wrong

- **The NLI model reports contradiction ≈1.0 for merely irrelevant passages**
  (EA-05, open). Contained by relevance weighting and the similarity gate;
  **not eliminated.** A passage that is off-topic but scores high on relevance
  still pushes `C` up.
- **Fabricated entities return `CONTRADICTED` where `UNVERIFIABLE` is honest**
  (EA-08, deliberately open). Needs entity-grounded coverage, not a threshold
  tweak.
- **Every threshold is a placeholder.** ADR-005's freeze protocol has not run.
  No reported number depends on them yet, and none may until it does.
- **Thresholds are per-backend.** Cosine and Jaccard are different measures on
  different scales; one gate for both marked everything `UNVERIFIABLE` on the
  fallback (EA-09).
- **Temperature scaling corrects average confidence, not per-group**
  miscalibration, so numeric and temporal claims need their own reported ECE.

## How it is tested

81 tests. `test_every_status_is_reachable` asserts all six can actually be
produced — a status that cannot be reached is dead documentation. Two tests
encode the project's invariants: no evidence → `UNVERIFIABLE`, and a `MISSING`
graph result changes nothing. The NLI label order is read from the model's own
`id2label` and asserted, because `nli-deberta-v3-small` orders its labels
`{0: contradiction, 1: entailment, 2: neutral}` and a wrong guess would invert
every verdict in the system while leaving all plumbing tests green.
