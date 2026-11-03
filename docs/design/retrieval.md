# Evidence Retrieval

**Owner:** P3 (Ayush) · **Code:** `src/verifact/retrieval/` · **Requirements:** FR-13…FR-19
**Produces:** `list[EvidencePassage]`, and the `evidence_golden.json` fixture

## What it does

Builds a query from a claim, gathers candidate passages from permitted sources,
and ranks them with two complementary retrievers fused into one ordering.

## Why it exists

The brief's hard rule: **no unrestricted web result is automatically
trustworthy.** The registry is the mechanism. It is also the single structural
difference from RARR (`gao2023rarr`), which post-edits text using whatever a
search engine returns and has no notion of source reliability at all.

The registry does double duty: it decides what may be *cited* and what hosts may
be *contacted*. One list, so there is no second allowlist to forget to update.

## How it works internally

**Source registry** (`config/sources.yaml`) — five tiers, each justified in the
file rather than asserted. Tier 1 is structured and referenced (Wikidata); tier 2
is editorially reviewed and correctable (Wikipedia); tier 3 is official-record
metadata (Crossref); tier 4 is an operator corpus; tier 5 is unregistered. An
unknown source resolves to tier 5 and is **logged, never silently dropped** —
dropping it would hide a coverage gap from the evaluation.

**SSRF controls** (`safety.py`) — four of them, because the input text is
untrusted and entity names feed query construction:

1. Host allowlist from the registry. Not a denylist: a denylist of bad hosts is a
   list you are always behind on.
2. **Address check after DNS resolution.** An allowlisted *name* is not enough —
   a public name with a private `A` record is the whole attack.
   `ipaddress.is_global` is used rather than a hand-maintained CIDR list, so
   loopback, link-local (169.254.0.0/16, where cloud metadata lives), RFC1918,
   multicast and reserved space are all covered for v4 and v6 without
   maintenance.
3. Redirects are followed **by hand**, re-validating each hop. A permitted host
   must not be able to send us anywhere it likes.
4. Response size and time caps.

**Ranking** (`rankers.py`) — BM25 and dense embeddings fail in *complementary*
ways, which is the entire reason for running both:

- BM25 finds rare named entities, numbers and dates — tokens an embedding model
  may never have seen — and scores a paraphrase with no shared terms at zero.
- Dense retrieval finds the paraphrase, and rates "Einstein was born in Ulm"
  against its own negation at >0.8 similarity.

Measured on a paraphrase with no shared vocabulary: BM25 −0.28, dense +0.41.

Their scores are **not on a comparable scale and cannot be added**, so Reciprocal
Rank Fusion combines *ranks* (`cormack2009rrf`). No normalisation, no training
data, three lines. `k = 60` is the paper's value, recorded in config rather than
hardcoded silently.

**Pooling**: candidates from all sources are ranked *together*, not quota'd per
source. A per-source quota would force weak evidence into the set whenever a weak
source happened to be enabled, and the weighting stage would then have to undo it.

## What alternatives exist

| Alternative | Why not |
|---|---|
| Open web search | forbidden by the brief, and it is what makes RARR unauditable |
| Elasticsearch | a service, for a corpus where `rank_bm25`'s linear scan is fine |
| pgvector / Chroma / HNSW | FAISS flat is exact and needs no tuning at this corpus size |
| A learned reranker | would likely beat RRF — we have no training data and no budget, which is the honest answer |
| Stemming in the tokeniser | collapses "1990"/"1990s" and merges "found"/"founded"; the exact surface form of a number is the thing being checked |

## What could go wrong

- **`relevance` is min-max scaled per claim**, so the best candidate always
  scores 1.0 even when nothing retrieved is about the claim. This made evidence
  coverage structurally unable to report "nothing relevant found" (EA-07). The
  verification stage now gates on absolute similarity; retrieval still has the
  property.
- **One unreachable source degrades silently** — logged, skipped, and reflected
  in coverage. Failing the claim instead would turn a transient outage into a
  verdict, which is a correctness bug rather than a reliability one.
- **Coverage bias.** Wikipedia is excellent on encyclopaedic subjects and absent
  on private or very recent facts, so `UNVERIFIABLE` correlates with the
  registry's blind spots, not with the claim's truth.
- **Cache staleness.** The HTTP cache has no expiry; a cached Wikipedia paragraph
  can be months old while the article has changed.
- **Paragraph granularity** can bury the relevant sentence in a long paragraph,
  which hurts the NLI stage.

## How it is tested

29 unit tests plus 20 SSRF tests. The SSRF suite names the attack each case
blocks — loopback by IP and by name, IPv6 loopback, cloud metadata, three private
ranges, scheme downgrade, non-HTTP schemes, credentials in the URL, missing host,
and a DNS-rebinding case that resolves a public name to a loopback address.
Retriever tests run against a local JSONL corpus with no network, so they are
deterministic and exercise the same code path as FR-18's offline mode.
