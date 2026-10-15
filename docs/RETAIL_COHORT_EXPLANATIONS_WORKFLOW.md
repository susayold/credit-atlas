# P1 — complete validation-client explanations, 10/10/2026

Study `retail-cohort-explanations-02487bb9d1a2` extends parent
`retail-explanations-84b3ac3bab6e` from12 ranked examples to **every one of
4,499 validation clients/995 source events**. Frozen boosting/raw model
`retail-freeze-3dc86f5afe01`, the32 training-reference clients, four predictor
groups and16-coalition probability game are unchanged.

## Computation and interpretation

All client explanations are saved privately, including a study-scoped token,
source ID, probability rank, prediction/reference, four contributions and
reconstruction residual. Source IDs never appear in client-list/report APIs.
These tokens are pseudonyms, not guaranteed anonymization or original IDs.

Computation uses32-client batches to bound memory; batching does not sample
the cohort or approximate the coalition game. Each client evaluates all16
coalitions against all32 reference rows. Reference +four contributions equals
the original frozen prediction within absolute1e-12. Actual maximum residual
is1.1102230246e-16. Every one of the12 parent examples reconciles to its
corresponding whole-cohort row, including rank, reference and contributions.

The whole-cohort distribution summarizes local Shapley values:

| Group | Mean absolute contribution, pp | Mean signed contribution, pp | Positive /negative /zero records |
|---|---:|---:|---:|
| Credit limit | 2.5447839490 | -0.5955722909 | 1797 /2702 /0 |
| Repayment status | 11.7533109379 | -0.3202096049 | 1030 /3469 /0 |
| Bill history | 2.7299299372 | -0.9792246059 | 1375 /3124 /0 |
| Payment history | 4.8097508946 | +1.0854841556 | 2258 /2241 /0 |

Each group's counts sum to4,499. These are finite-reference contribution
magnitudes and directions. They differ from performance changes under grouped
permutation; neither statistic establishes causal importance, fairness,
approved adverse-action reasons or realistic intervention effects. Group size,
cross-group correlation and reference choice affect interpretation. Within-group
histories/categories are preserved, while cross-group hybrid records may be
unrealistic. Validation already informed model selection.

## Analyst workflow and API

Retail → Model explanations → Giải thích toàn bộ validation cohort.
Browse20 rows per page, ordered by decreasing saved probability rank. Select
Giải thích on any row, or enter an exact study-scoped token. The lowest and
highest ranks and every intermediate client are supported. URL carries the
parent explanation, cohort study and selected token; reload restores that exact
client. A nonexistent token produces no client/prediction/export. Clear the
search to return to the complete paginated cohort.

The cohort summary contains all4,499 clients; each export contains one selected
client plus the whole-cohort aggregate context. It excludes original IDs,
training-reference rows, encoded predictor values and individual outcome labels.
No final-holdout client can be queried through this interface.

GET `/api/retail-cohort-explanations`: freeze_id +explanations_id.
GET `/api/retail-explanation-clients`: those IDs +cohort_id; optional ASCII
offset/limit and exact-token q. Limit is1–50; default20, maximum offset50,000
and offset must be within the selected result. Unknown/extraneous query keys,
non-ASCII numerals, original-ID searches and oversized pages are rejected.
GET `/api/retail-client-explanation` or `...-report`: exact source IDs and
client_token. Mismatched models/parents/cohorts and unknown tokens fail.
All responses and downloads are private/no-store.

## Evidence and verification

The parent study, complete frozen acquisition/canonical/feature/model graph,
reference evidence, numerical methods and outputs are pinned. Verification
replays all2,303,488 coalition-row predictions (4,499×16×32), probabilities,
ranks, tokens, original-example parity and whole-cohort summaries. Serving
performs full replay on first use, then checks every source/output/receipt hash
before serving cached rows. Cold startup includes complete numerical replay;
cached serving still reads the pinned source graph for integrity.

Independent audit `retail-cohort-explanations-audit-a441ed7a5c48.json`:
**45,021 checks PASS**, all4,499 clients. It uses separate depth-first saved-tree
traversal and all24 group orderings for marginal contribution allocation,
independent reference/rank/token derivation, count/sign/magnitude distributions
and unchanged holdout ledger. A first audit attempt ran out of memory during
NumPy allocation; the final audit uses8-client chunks over the same complete
cohort. No records, source/model methods or comparisons were omitted.

Eight focused tests PASS: complete coverage, rank/token uniqueness, partial
batch parity, reconstruction/distributions, unchanged12-example parity,
invalid probabilities/partitions/tensors, exact schema, immutable replay,
pagination/exact search, cross-source rejection, private HTTP downloads and
same-size/mtime cached-source corruption.

Browser receipt `retail-cohort-browser-qa-5d64a03b5226/receipt.json`:
**8 checks PASS** against the actual cohort. Complete population/summary,
second-page rank4470, private export, exact URL reload, lowest-rank token,
unknown-token empty state, desktop/390px mobile and unchanged consumed holdout
were verified without unexpected console errors. The client action is the
first table column and remains visible and clickable before horizontal
scrolling on mobile; selecting rank4498 reconstructs its saved prediction.

Complete regression `test-batches-b9f9556ff400/receipt.json`:
**1,098 tests PASS**, all115 files across15 sequential fresh-process batches.
Every collected test executed, with zero failures/errors/skips and no
automatic failure retries. This includes the frozen vendor suite and all
eight new cohort tests with identity/example-contribution corruption cases.

Live HTTP receipt `retail-cohort-live-e5b178d0c426/receipt.json`: **PASS**.
All4,499 clients reconciled across90 pages against the private saved evidence:
unique tokens, exact ranks/probabilities, no original client IDs and private
no-store responses. Rank4470 report/download matched the saved cohort and
its contribution vector exactly. Consumed holdout ledger unchanged.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_cohort_explanations.py --assumptions private evidence omitted from public release
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_cohort_explanations.py --verify retail-cohort-explanations-02487bb9d1a2
.\.venv\Scripts\python.exe -X utf8 scripts/audit_retail_cohort_explanations.py --cohort-id retail-cohort-explanations-02487bb9d1a2
.\.venv\Scripts\python.exe -X utf8 scripts/browser_retail_cohort_explanations_qa.py
.\.venv\Scripts\python.exe -X utf8 scripts/test_batches.py --batch-files 8
# Requires the local server on port8770.
.\.venv\Scripts\python.exe -X utf8 scripts/check_retail_cohort_explanations_live.py
```

Build creates an immutable new study. Use verify for existing evidence. This
closes complete-client coverage within this historical validation benchmark;
new application-client scoring/intended-use validation, reference sensitivity,
regulated decision reasons and temporal monitoring remain open. The full
five-workspace/50-capability goal is not complete.
