# Research (Phase 1)

| File | What it is |
|---|---|
| `papers/` | 30 per-paper records, one file each |
| `gap-matrix.md` | 16 systems × 10 capabilities, and the four empty columns |
| `novelty-statement.md` | the narrow claim, with falsification criteria fixed in advance |
| `decisions/ADR-001-contribution.md` | the accepted contribution and the alternatives rejected |
| `references.bib` | 30 BibTeX entries, metadata API-verified |

## Reading the records honestly

Every record states its summary source. **All 30 summaries are written from the published
abstract, not from a full read.** Metadata (title, authors, identifier) was verified by
querying the arXiv and Crossref APIs on 2026-11-02 — no citation here is reconstructed from
memory. Claims in the *Limitations* sections tagged *(verify on full read)* are reasoned
inferences and must be confirmed against the full paper before they appear in the report.

`full_text_read_by: <<TBD>>` in each record is a real task, assigned in
`docs/phase-0/01-research-plan.md` (≥4 papers per team member). The report's Literature
Survey must not be written from these records alone.

## Clusters

| | Cluster | Records |
|---|---|---|
| C1 | taxonomy, definitions, causes | ji2022survey, zhang2023siren, guo2022factchecking, raunak2021hallucinations |
| C2 | self-consistency and uncertainty | manakul2023selfcheckgpt, kuhn2023semantic, dhuliawala2023cove |
| C3 | decomposition, atomic facts, attribution | min2023factscore, tang2024minicheck, wang2023factcheckbench, rashkin2021attribution |
| C4 | retrieval-based verification | thorne2018fever, aly2021feverous, lewis2020rag, gao2023rarr, gao2023alce, pan2023programfc, cormack2009rrf, robertson2009bm25 |
| C5 | model backbones | he2021deberta, reimers2019sbert, wang2020minilm |
| C6 | graph and knowledge-graph verification | liu2020kgat, zhou2019gear, shiralkar2017streams, dziri2021neuralpathhunter |
| C7 | calibration | guo2017calibration, tian2023justask |
| — | benchmarks | lin2022truthfulqa, li2023halueval |

## The three papers that matter most to defend

1. **guo2022factchecking** — establishes our pipeline is standard. Read this before claiming novelty.
2. **gao2023rarr** — the closest system to our mitigation module. Know the differences cold.
3. **shiralkar2017streams** — cannot distinguish a missing relation from a false one. Our `MISSING` status exists because of this paper.
