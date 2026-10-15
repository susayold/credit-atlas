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
no new Freddie annual vintage was added.

| ID | Current status | Evidence / remaining requirement |
|---|---|---|
| M01-001 | Partial | Pinned 164-file engine and actual local source found; complete capability-gap audit still needed |
| M01-002 | Verified for 2012 | Fresh eight-stage rebuild; 50,000 loans / 4,510,559 months; resource receipt |
| M01-003 | Verified for supplied 2012 corpus | Release-47 trace audit covers 17 field sentinels, 20 categorical fields, 6 date fields, HARP flags, percentage-point casts, and 4,510,559 state/terminal mappings; see `docs/D01_CANONICAL_SEMANTIC_AUDIT_VI.md` and `private evidence omitted from public release`. Cross-vintage semantic compatibility remains open |
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
| M01-028 | Partial | 42 real-data browser checks pass on a fresh valid case; five key views fit 390px; sparse/gated/unavailable, stale-evidence 503, missing-run 404, unlisted run, connection abort, malformed JSON, HTTP 500 JSON and HTTP 502 HTML, run-catalog HTTP 503, privacy and export paths checked. Broader endpoint-specific transport coverage remains |
| M01-029 | Partial | Fresh eight-stage source-manifest reproduction plus new valid private case: final report is byte-identical, snapshot JSON matches after case-ID normalization, model study/feature audit reproduce BLOCKED_BEFORE_FIT without fitting, and 42/42 browser checks pass. Qualified multi-vintage fit/calibration/final OOT remains blocked |
| M01-030 | Partial | Descriptive case study now ties question, data/target, KPI denominators, results, limitations and evidence links; final qualified model card/demo remain blocked by missing vintages and R3 |

## Evidence references

- Actual case: private evidence omitted from public release
- Foundation reproduction: the case's reproduction.json and [fresh end-to-end descriptive receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).
- Latest browser acceptance: private evidence omitted from public release 42 checks PASS on the fresh valid reproduction case (2026-10-15).
- Chart/support audit: docs/D01_CHART_SUPPORT_AUDIT_VI.md and private evidence omitted from public release
- Reproduction audit: docs/D01_REPRODUCTION_AUDIT_VI.md; foundation receipt at private evidence omitted from public release final descriptive receipt at private evidence omitted from public release
- Case study: docs/D01_CASE_STUDY_VI.md (descriptive checkpoint; model claims explicitly gated).
- Data access check: docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md (official sources; no equivalent unauthenticated mortgage-performance panel found).
- NSMO alternative source review: docs/D01_NSMO_SOURCE_REVIEW_VI.md; official source docs under private evidence omitted from public release agreement gate pending, no PUF payload downloaded.
- Analyst findings: docs/D01_ANALYST_FINDINGS_VI.md; private evidence omitted from public release
- Episode denominator audit: docs/D01_EPISODE_DENOMINATORS_VI.md; private evidence omitted from public release 24/24 follow-up status partitions reconcile.
- Transition denominators: docs/D01_TRANSITION_DENOMINATORS_VI.md; docs/P2_TRANSITION_ACCEPTANCE_VI.md; private evidence omitted from public release
- Canonical semantics: docs/D01_CANONICAL_SEMANTIC_AUDIT_VI.md; private evidence omitted from public release 17 sentinel fields, 20 enum fields, all date/HARP/percentage checks and 4,510,559 monthly mappings passed.
- Release readiness: docs/D01_RELEASE_READINESS_VI.md; private evidence omitted from public release private evidence omitted from public release Privacy scan was updated to support binary background images and then passed on the current 15-asset bundle.
- Full repository suite: latest 1,577/1,577 run in private evidence omitted from public release earlier 1,574 and 1,568 runs are preserved in their receipts.
- Export contract: docs/D01_EXPORT_CONTRACT_AUDIT_VI.md; private evidence omitted from public release 5 actual scopes, 50,000-ID scan and unsupported PD/ECL/CF request rejection PASS.
- Private episode-support snapshot: private evidence omitted from public release
- Application checks: tests/; engine checks: vendor/credit_risk_strategy_lab/tests/.
- Full check command: scripts/test.ps1.

## Next source-independent implementation

1. Broaden M01-028 error-state checks to the remaining relevant workspace APIs and delivery flows; current D01 snapshot path now covers HTTP 500 JSON and 502 non-JSON.
2. Keep M01-029 and R2/R3 open for authorized multi-vintage data; the descriptive report, UI, and no-fit gate are now reproduced, but empirical model qualification is data-gated.
3. Continue source-independent audit and documentation cleanup without changing model claims or completion counts.

Completed at this checkpoint: monitoring/follow-up exports, private token scope
checks, static/Git package scan, local API benchmark, local source registration
and temporal-study preparation. The full latest suite has 468 passing checks.
