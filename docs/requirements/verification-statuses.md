# The Six Verification Statuses

Owner: P4. Frozen in Phase 2 — the enum in `contracts/` is generated from this file's table,
and changing a status here is a contract change (ADR process).

The system reports **attribution to trusted sources**, not truth (vocabulary from
`rashkin2021attribution`). Every status below is a statement about *evidence*, never about
reality.

| Status | Means | Evidence condition | Worked example |
|---|---|---|---|
| `SUPPORTED` | Trusted evidence entails the claim | weighted entailment clearly exceeds contradiction, coverage adequate, KG not contradicting | *"Water boils at 100 °C at standard atmospheric pressure."* — multiple tier-1 sources entail it |
| `CONTRADICTED` | Trusted evidence refutes the claim | weighted contradiction clearly exceeds entailment, **or** the KG holds an incompatible relation for a checkable predicate | *"The Eiffel Tower is in Berlin."* — Wikidata gives `located in: Paris`; passages contradict |
| `UNVERIFIABLE` | Nothing usable was retrieved — the claim may be perfectly true | evidence coverage below τ_cov; i.e. retrieval returned nothing relevant | *"My neighbour's cat is called Mitzi."* — true, but no trusted source covers it |
| `INSUFFICIENT_EVIDENCE` | Evidence exists but is too weak to decide either way | coverage adequate, but max(E, C) below τ_weak, or E and C both low | *"The 2019 pilot study involved roughly forty participants."* — the paper is retrieved, the number is not stated in the retrieved passages |
| `OUTDATED` | Supported only by evidence that is older than the claim's temporal scope, and newer evidence disagrees | supporting passages predate a newer, at-least-equally-reliable contradicting passage | *"Twitter's CEO is Jack Dorsey."* — true in 2020, contradicted by later sources |
| `AMBIGUOUS` | The claim cannot be given one verdict as written | trusted sources of comparable reliability disagree, **or** the claim is not interpretable standalone (unresolved reference, vague quantifier) | *"He won the award twice."* — no resolvable referent; or *"Coffee is good for you."* — sources of equal standing disagree |

## Rules that follow, and are tested

1. **`UNVERIFIABLE` ≠ `CONTRADICTED`.** Absence of evidence never produces a contradiction
   verdict. Tested by `tests/unit/verification/test_aggregate.py::test_no_evidence_is_unverifiable`.
2. **`UNVERIFIABLE` vs `INSUFFICIENT_EVIDENCE`** is a statement about *retrieval*, not about
   the claim: nothing relevant came back at all, versus something came back but settled nothing.
3. **A `MISSING` KG result can never flip a claim to `CONTRADICTED`.** Wikidata not holding a
   relation is silence, not denial (the limitation identified in `shiralkar2017streams`).
4. **`OUTDATED` requires a dated newer source.** An undated contradicting passage cannot
   produce `OUTDATED`; it produces `AMBIGUOUS` or `CONTRADICTED` on the ordinary rule.
5. **`AMBIGUOUS` covers two distinct causes** — source disagreement and
   non-interpretability — and the `explanation` field must say which.

## Mapping to external datasets

| Dataset label | Our status | Note |
|---|---|---|
| FEVER `SUPPORTS` | `SUPPORTED` | direct |
| FEVER `REFUTES` | `CONTRADICTED` | direct |
| FEVER `NOT ENOUGH INFO` | `UNVERIFIABLE` **or** `INSUFFICIENT_EVIDENCE` | **many-to-one in the reverse direction.** For scoring against FEVER we collapse our two statuses into one NEI class; the collapse is applied in the metric, not in the system, and is reported |
| HaluEval `hallucinated` | `CONTRADICTED` ∪ `INSUFFICIENT_EVIDENCE` | lossy; documented in the test report |
| HaluEval `not hallucinated` | `SUPPORTED` | |

`OUTDATED` and `AMBIGUOUS` have **no equivalent in any public dataset we surveyed.** They are
evaluated only on `verifact-stress`. The test report must state this rather than implying the
public benchmarks exercised them.
