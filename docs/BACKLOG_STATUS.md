# D01 — Requirement audit and remaining work

Checkpoint: 2026-10-15. Specification: PLAN_MODULE_01.md, section 47.18.
This tracks the entire module scope. An engineering check is evidence for the
behavior it exercises; it does not qualify absent vintages or model performance.
Data acquisition resumed. Additional Clarity annual ZIPs require a login session
that is not available. An alternative FHFA/CFPB NSMO public-use mortgage sample
was identified (2013–2024 originations; quarterly performance through 2025 Q3);
its official documentation/codebook were acquired and reviewed. Its source-level
monitoring/terms acknowledgement is pending user authorization, and the data
payload has not been downloaded. NSMO must remain a separate source, not a new
Freddie vintage. Three public macro series and retrospective context were
acquired separately; they do not qualify the loan-level study. The Release 47
public example/layout audit confirms field widths but finds disjoint loan IDs;
no new Freddie annual vintage was added. A Ginnie Mae loan-performance quarterly/
annual release is now documented as a separate candidate MBS case; its Terms of
Use require affirmative agreement, so the payload remains undownloaded. See
`docs/GINNIE_MAE_LOAN_PERFORMANCE_SOURCE_REVIEW_VI.md`. A terms-gated, streaming
ZIP structure auditor was added from the official 59-field layout; its synthetic
contract tests pass 6/6, but no production file has been checked yet.

## 2026-10-15 — Ginnie Mae separate-source preparation

Reviewed Ginnie Mae's official bulk catalog, Single-Family Loan-Level Terms of
Use, quarterly/annual Loan Performance layout, monthly active-loan layout,
liquidation layout, and dictionary. The quarterly and annual files are
pipe-delimited `HH`/`LP`/`TT` packages with up to 3/12 active-loan reporting
periods; `LP-59` adds up to 24 two-character monthly delinquency states, with
`XX` for unavailable periods. This is useful for a Ginnie MBS case, but active
pool selection and Ginnie-specific delinquency/removal semantics prevent it
from serving as a Freddie vintage.

Added `src/credit_atlas/ginnie_performance.py` and
`scripts/audit_ginnie_loanperf.py`. The offline auditor reads inside the ZIP,
checks row widths, frequency, dates, duplicate loan-period keys, status codes,
history encoding and trailer totals, then emits aggregate counts and a source
member SHA-256 without exposing disclosure IDs. It requires an explicit
user-accepted-terms flag. Six synthetic parser tests passed and the full suite
passed 1,587/1,587. The actual payload is still not downloaded; production
format/resource profiling and model-use qualification remain unverified.

| ID | Current status | Evidence / remaining requirement |
|---|---|---|
| M01-001 | Partial | Pinned 164-file engine and actual local source found; complete capability-gap audit still needed |
| M01-002 | Verified for 2012 | Fresh eight-stage rebuild; 50,000 loans / 4,510,559 months; resource receipt |
| M01-003 | Verified for supplied 2012 corpus | Release-47 trace audit covers 17 field sentinels, 20 categorical fields, 6 date fields, HARP flags, percentage-point casts, and 4,510,559 state/terminal mappings; see `docs/D01_CANONICAL_SEMANTIC_AUDIT_VI.md` and `artifacts/private/d01-canonical-semantics-e2fe2cdc8cbf/receipt.json`. Cross-vintage semantic compatibility remains open |
| M01-004 | Partial | Runtime lock 19/19, 164 pinned engine hashes, D: storage and 0/969 private Git candidates verified; current 15-asset bundle scanned against 50,000 source IDs; latest full suite passes 1,577/1,577 after NSMO CSV-streaming parser. Earlier 1,568 run also passed in 21 fresh sequential batches. License metadata/engine redistribution rights and concurrent/full-model resource sign-off remain; see `docs/D01_RELEASE_READINESS_VI.md` and `docs/TEST_SUITE_2026-10-15_VI.md` |
| M01-005 | Authentication blocked; code implemented | HTTP downloader + local import/atomic registration; official check confirms Freddie Clarity and Fannie Data Dynamics account gates; no new annual ZIP downloaded; public macro context completed separately; see `docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md` |
| M01-006 | Unmet | Multi-vintage canonical and layout comparison require additional qualified data |
| M01-007 | Partial | 2012 segment support visible; multi-vintage qualification memo absent |
| M01-008 | Implemented | Existing early-entry target version preserved; no target change to inflate support |
| M01-009 | Verified for 2012 | Saved labels reconcile to source population and label summary |
| M01-010 | Verified for 2012 | Frozen stock/profile views, independent count/UPB and cohort checks, and analyst findings memo; multi-vintage composition comparison remains open |
| M01-011 | Verified for 2012 | Lifetime/reporting-year count and opening-UPB denominators independently reconcile; adjacent-pair, missing-balance, sparse-support and lifetime-scope interpretation documented; multi-vintage comparison remains open |
| M01-012 | Verified for 2012 | Event occurrences versus unique-loan support and follow-up status denominators independently reconcile; app UI regression passes; model cure/redefault probabilities remain out of scope |
| M01-013 | Verified for 2012 | Existing independently checked competing-event ledger and 6/12/24m evidence; multi-vintage comparison absent |
| M01-014 | Implemented descriptive | Signed observed loss bridge, residual and unresolved coverage; no qualified severity model |
| M01-015 | Partial code; data gates unmet | prepare-study writes actual timing/support audit and access log; required vintages/protocol qualification absent |
| M01-016 | Partial code; qualification unmet | Strict allowlist, train-only encoder, development coverage, saved-state parity and final-test predictor exclusion implemented; actual 2012 audit performed; multi-vintage availability/ablation review not frozen |
| M01-017 | Partial code; actual study unmet | Multi-case gated constant/logistic adapter and bounded train-only C tuning implemented; actual 2012 study stops before fit |
| M01-018 | Partial code; actual study unmet | Same-cohort boosting and artifact parity tested on synthetic engineering fixtures; actual qualified challenger not fitted |
| M01-019 | Partial code; actual study unmet | Separate calibration and raw/calibrated metric reconciliation implemented; qualified real outer-cohort evidence/uncertainty absent |
| M01-020 | Unmet | No model-selection/final-study freeze |
| M01-021 | Unmet | No final out-of-time scoring/evaluation |
| M01-022 | Verified for descriptive export | Actual schema-2 and embedded schema-1 reports reconcile across 5 scopes; case/run/method/digests, empty-year behavior, determinism, and 50,000-ID privacy scan pass; unknown PD12/ECL/cash-flow overrides now fail closed. Model-score consumer remains gated until R3; see `docs/D01_EXPORT_CONTRACT_AUDIT_VI.md` |
| M01-023 | Implemented local | Run navigation and URL filter persistence tested; unknown run IDs now fail clearly instead of silently switching to the first run |
| M01-024 | Partial | Chart/support audit passes: monthly denominators, vintage risk sets, profile shares, annual/lifetime transition matrices and signed loss bridge; browser confirms rendered series/support, sparse transition warning and 390px mobile layout. Actual model page reports five before-fit blockers; multi-vintage comparison and model qualification remain open |
| M01-025 | Implemented local | Findings, case/filter refs, optimistic revisions and append-only history tested |
| M01-026 | Partial | Frozen integrity/missingness/support monitoring and investigation order; validated-model monitoring remains unavailable |
| M01-027 | Unmet | Frozen validated mortgage scoring interface awaits R3 |
| M01-028 | Partial | 57 real-data browser checks pass on a fresh valid case; five key views fit 390px; sparse/gated/unavailable, stale-evidence 503, missing-run 404, unlisted run, connection abort, malformed JSON, HTTP 500/502/503, D01 transition/episode/monitoring/loan/timeline/provenance/study/loss/findings/history/save failures, report export success/failure, standalone NMDB export/hash and privacy paths checked. Remaining other-workspace APIs/delivery routes need scoped checks |
| M01-029 | Partial | Fresh eight-stage source-manifest reproduction plus new valid private case: final report is byte-identical, snapshot JSON matches after case-ID normalization, model study/feature audit reproduce BLOCKED_BEFORE_FIT without fitting, and the latest standalone D01 browser acceptance passes 57/57 checks. Qualified multi-vintage fit/calibration/final OOT remains blocked |
| M01-030 | Partial | Descriptive case study now ties question, data/target, KPI denominators, results, limitations and evidence links; final qualified model card/demo remain blocked by missing vintages and R3 |

## Evidence references

- Actual case: artifacts/private/d01-a24484b21a21.
- Foundation reproduction: the case's reproduction.json and [fresh end-to-end descriptive receipt](../artifacts/private/d01-final-reproduction-qa42-20261015/receipt.json).
- Reproduction-linked browser acceptance: artifacts/private/browser-qa-8c77d535b638/receipt.json; 42 checks PASS on the fresh valid reproduction case (2026-10-15).
- Prior standalone browser acceptance: artifacts/private/browser-qa-051be1f508a0/receipt.json; 47 checks PASS on the fresh verified case.
- Prior standalone browser acceptance: artifacts/private/browser-qa-3bc5265fb809/receipt.json; 48 checks PASS, including NMDB aggregate history rendering and explicit source-population caveats (2026-10-15).
- Prior standalone browser acceptance: artifacts/private/browser-qa-d97caa354c3f/receipt.json; 48 checks PASS after final aggregate-reader and source-receipt integrity checks (2026-10-15).
- Prior standalone browser acceptance: artifacts/private/browser-qa-ca555c18df19/receipt.json; 49 checks PASS, including the failed report-download user flow (2026-10-15).
- Prior standalone browser acceptance: artifacts/private/browser-qa-c58475aed5fc/receipt.json; 51 checks PASS against the latest acquired aggregate package, including standalone NMDB JSON export/hash verification and export failure behavior (2026-10-15).
- Prior standalone browser acceptance: artifacts/private/browser-qa-43c63fd3edd5/receipt.json; 55 checks PASS, adding failure coverage for provenance, prepared studies, loss diagnostics, and findings (2026-10-15).
- Latest standalone browser acceptance: artifacts/private/browser-qa-2d25ed161db0/receipt.json; 57 checks PASS, adding finding-history and finding-save failure flows (2026-10-15).
- Chart/support audit: docs/D01_CHART_SUPPORT_AUDIT_VI.md and artifacts/private/d01-chart-support-a5a39d8e7acc/receipt.json.
- Reproduction audit: docs/D01_REPRODUCTION_AUDIT_VI.md; foundation receipt at artifacts/private/d01-a24484b21a21/reproduction-pipeline-0415306845cd.json; final descriptive receipt at artifacts/private/d01-final-reproduction-qa42-20261015/receipt.json.
- Case study: docs/D01_CASE_STUDY_VI.md (descriptive checkpoint; model claims explicitly gated).
- Data access check: docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md (official sources; no equivalent unauthenticated mortgage-performance panel found).
- NSMO alternative source review: docs/D01_NSMO_SOURCE_REVIEW_VI.md; official source docs under data/private/mortgage/nsmo-2026-05-27/source_docs; agreement gate pending, no PUF payload downloaded.
- Analyst findings: docs/D01_ANALYST_FINDINGS_VI.md; artifacts/private/d01-analyst-findings-a9579df23a87/receipt.json.
- Episode denominator audit: docs/D01_EPISODE_DENOMINATORS_VI.md; artifacts/private/d01-episode-denominators-a3a3093f04b8/receipt.json; 24/24 follow-up status partitions reconcile.
- Transition denominators: docs/D01_TRANSITION_DENOMINATORS_VI.md; docs/P2_TRANSITION_ACCEPTANCE_VI.md; artifacts/private/transition-acceptance-be68432843fc/receipt.json.
- Canonical semantics: docs/D01_CANONICAL_SEMANTIC_AUDIT_VI.md; artifacts/private/d01-canonical-semantics-e2fe2cdc8cbf/receipt.json; 17 sentinel fields, 20 enum fields, all date/HARP/percentage checks and 4,510,559 monthly mappings passed.
- Release readiness: docs/D01_RELEASE_READINESS_VI.md; artifacts/private/d01-release-readiness-89b0c5945a8f/receipt.json; artifacts/private/package-audit-4dd8b231c83e/receipt.json. Privacy scan was updated to support binary background images and then passed on the current 15-asset bundle.
- Full repository suite: latest 1,581/1,581 run in artifacts/private/test-suite-direct-20261015-nmdb-export/receipt.json; previous 1,580, 1,577, 1,574 and 1,568 runs are preserved in their receipts.
- Export contract: docs/D01_EXPORT_CONTRACT_AUDIT_VI.md; artifacts/private/d01-export-contract-dc182aeaae7e/receipt.json; 5 actual scopes, 50,000-ID scan and unsupported PD/ECL/CF request rejection PASS.
- Private episode-support snapshot: artifacts/private/episode-followup-20261008.json.
- Application checks: tests/; engine checks: vendor/credit_risk_strategy_lab/tests/.
- Full check command: scripts/test.ps1.

## Next source-independent implementation

1. Broaden M01-028 transport/error coverage to remaining relevant workspace APIs and delivery flows; D01 now checks transition, episode-follow-up, monitoring, loan-search, timeline, provenance, prepared studies, loss diagnostics, findings/history/save, report export, and standalone NMDB source export success/failure.
2. Keep M01-029 and R2/R3 open for authorized multi-vintage data; the descriptive report, UI, and no-fit gate are now reproduced, but empirical model qualification is data-gated.
3. Continue source-independent audit and documentation cleanup without changing model claims or completion counts.

Completed at this checkpoint: monitoring/follow-up exports, private token scope
checks, static/Git package scan, local API benchmark, local source registration
and temporal-study preparation. The full latest suite has 468 passing checks.

## 2026-10-15 continuation checkpoint

Expanded the D01 browser acceptance from 42 to 57 checks. The shared browser API
reader now reports controlled messages for malformed JSON and non-JSON HTTP
failures rather than leaking a JSON parser exception. Controlled 500/502/503
cases verify that transition matrices, episode supplements, source monitoring,
private loan lists, and timelines surface unavailable evidence without inventing
zero values or retaining stale loan rows. A further check verifies that the new
FHFA aggregate history renders with distinct population/denominator caveats. The
failed report-download path now shows server errors in the app and suppresses a
fake file. The aggregate context also exports as a standalone JSON package with
verified hash; an export outage is surfaced without triggering a fake file. Two
checks now cover finding-history outages and failed finding saves without a false
revision. The 57-check run passed on the fresh verified case; latest receipt:
`artifacts/private/browser-qa-2d25ed161db0/receipt.json`. The latest full app and
vendor suite has 1,581 passing tests; see
`artifacts/private/test-suite-direct-20261015-nmdb-export/receipt.json`.

Data audit: the next eligible D01 source is still not an unauthenticated Freddie
annual sample. FHFA/CFPB NSMO is a distinct quarterly public-use sample, but the
publisher requires an affirmative monitoring/terms acknowledgement before the
microdata download; this run did not submit that acknowledgement or fetch the
payload. Existing official codebook and parser remain ready for a separately
authorized NSMO case. Freddie/Fannie account-gated loan-level files are still
unavailable without an authenticated session. No extra dataset is being relabeled
as a Freddie vintage. Multi-vintage model qualification remains data-gated.

The public FHFA NMDB aggregate mortgage-performance package was acquired and
profiled separately: 261,856 unique rows, 13 columns, four performance series,
four markets, six geography levels, and 98 quarters through 2026Q2. A national
all-mortgages trend and separate forbearance chart are now visible in D01's
Sources page with independent-denominator caveats. This adds source context, not
loan-level observations or model-training data. See
`docs/FHFA_NMDB_AGGREGATE_PERFORMANCE_VI.md` and the private acquisition receipt.
