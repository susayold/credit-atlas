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
| M01-028 | Partial | 94 real-data D01 browser checks pass on a fresh verified case; five key views fit 390px. Failure coverage includes D01, Market, HMDA, FDIC, independent mortgage sources, public profiles and POST/GET exports. Retail task acceptance now covers dossier, data contract, subgroup, local explanation and cohort-client attachments: success/parity plus HTTP 503 with visible error and no fake download; dedicated receipts: `artifacts/private/remaining-domains-qa-63f3f8db24cb/`, `retail-explanations-browser-qa-04f376717b60/`, `retail-cohort-browser-qa-317b104b2738/`, `retail-data-contract-browser-0b38fb3b5ab2/`, `retail-dossier-browser-134ef4cff73f/`, `retail-subgroups-browser-qa-8c00e3f64756/`. ABS main and five specialized source/benchmark attachments also have success/failure acceptance. P4 inventory, movement, scenario, ECL, tail, convergence, and Excel delivery failures now have scoped browser acceptance. Bankruptcy ratio export also passes successful-source and HTTP 503/no-fake-download acceptance (`artifacts/private/bankruptcy-browser-qa-6949e456b58c`). M01-028 remains Partial pending a complete route inventory and remaining workspace-specific delivery checks; D01 multi-vintage qualification is unchanged.
| M01-029 | Partial | Fresh eight-stage source-manifest reproduction plus new valid private case: final report is byte-identical, snapshot JSON matches after case-ID normalization, model study/feature audit reproduce BLOCKED_BEFORE_FIT without fitting, and the latest standalone browser acceptance on the verified case passes 94/94 checks. Qualified multi-vintage fit/calibration/final OOT remains data-gated |
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
- Latest standalone browser acceptance: artifacts/private/browser-qa-12b9ce006825/receipt.json; 61 checks PASS. Adds actual Market series and assumption-only bond JSON exports, verifies their private scope/filter content, and confirms 503/502 export failures surface without fake downloads (2026-10-15).
- Latest standalone browser acceptance: artifacts/private/browser-qa-ce65ee3cf106/receipt.json; 64 checks PASS. Adds FHFA 2025 PUDB acquisition profile visibility, aggregate-only private JSON integrity, source-population caveats and export-failure handling (2026-10-15).
- Latest standalone browser acceptance: artifacts/private/browser-qa-6477b486711c/receipt.json; 66 checks PASS. Adds the shared attachment path: a real Excel template preserves its server filename, while a simulated HTTP 503 report failure shows an error without creating a fake file (2026-10-15).
- Latest standalone browser acceptance: artifacts/private/browser-qa-7a73963387de/receipt.json; 69 checks PASS. Adds HUD FHA tract exposure visibility, key-free private aggregate export with source-code/vintage caveats, and simulated export failure handling (2026-10-15).
- Latest standalone browser acceptance: artifacts/private/browser-qa-f32396b0c1ff/receipt.json; 71 checks PASS. Adds direct Fannie sample-audit JSON export via the shared attachment handler and HTTP 503 failure behavior without a fake download (2026-10-15).
- Latest standalone browser acceptance: artifacts/private/browser-qa-9b34beeb05fd/receipt.json; 74 checks PASS. Adds a real monitor KPI XLSX POST download plus HTTP 503 JSON and HTTP 200 HTML masquerade failures, which are rejected without fake files (2026-10-15).
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

1. Continue M01-028 with a route-to-test inventory for remaining workspace deliveries, starting with P4 Portfolio import/Excel/review attachments and other source-specific report routes; keep each route checked for valid payload, scoped contents, HTTP failure and no fake downloads.
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

## 2026-10-15 HMDA and FDIC report-delivery continuation

Extended the D01 M01-028 browser suite with the actual HMDA and FDIC Bank
workspace export routes. Both workspaces already had separate successful
actual-data export acceptance; this run injects HTTP 503 through the selected
HMDA report route (including the labeled-reference route) and FDIC bank report
route, then verifies that the shared attachment handler displays the server
error and creates no download. The full browser suite passes 94/94 checks on
fresh verified case `d01-202610150931`, with no browser errors. Receipt:
`artifacts/private/browser-qa-f0dba3916637/receipt.json`. The HMDA and FDIC
files are application/financial-condition sources and do not add mortgage
repayment histories or satisfy the missing Freddie multi-vintage gate. M01-028
remains partial; D01's 26/50 completion count and the model/data gates are
unchanged.

## 2026-10-15 shared report-download continuation

M01-028 audit found that several workspace report links downloaded directly,
so an HTTP error could be saved as a fake Excel/JSON file. Added one delegated
attachment handler for API-backed download links: it checks HTTP status, rejects
HTML/empty responses, uses the server filename, and surfaces errors in the app.
Browser acceptance passed 66/66 on the verified D01 case. It downloaded the real
portfolio Excel template with its expected filename and verified that a synthetic
503 export error creates no file. Focused Market API tests passed 9/9. Receipt:
`artifacts/private/browser-qa-6477b486711c/receipt.json`. M01-028 remains Partial
because remaining workspace-specific API routes still need scoped checks; D01
data/model qualification and its 26/50 requirement count are unchanged.

## 2026-10-15 Market delivery continuation

M01-028 was extended beyond D01 to the Market workspace. Native-series and
assumption-only bond reports now pass through the shared JSON response validator
before download. A fresh browser acceptance downloaded both real reports,
checked their private-release flags and date-filter integrity, then injected
HTTP 503 and 502 responses and confirmed the UI showed errors without creating
files. The 61-check acceptance passed on the verified D01 case; receipt:
`artifacts/private/browser-qa-12b9ce006825/receipt.json`. The focused Market API
suite passed 9/9 tests. M01-028 remains Partial because other workspaces still
need scoped route and export checks; this does not change the 26/50 completion
count or the model/data gates.

## 2026-10-15 HUD FHA geographic exposure source

Acquired the official HUD ArcGIS CSV to private storage after confirming the
HUD-hosted portfolio XLSX itself was blocked with HTTP 403. The tract table
contains 85,154 unique 2010 Census GEOIDs and 20 columns. Profiled nonblank
active-loan and exposure aggregates with no tract-level export. An undocumented
`-4` appears 9,598 times each in unpaid-balance and original-amount measures;
the reader quarantines this code rather than summing it or treating it as zero.
HUD catalog metadata says coverage 2025-03, while the FeatureServer layer text
still says 09/2021, so effective timing remains unresolved. Added a receipt-
verified API and aggregate-only Sources panel. Four parser contract tests pass;
the latest real-data browser acceptance is 69/69 PASS with a key-free profile
export and injected HTTP 503 failure check. Source note: `docs/HUD_FHA_IIF_TRACT_REVIEW_VI.md`.
This is separate FHA exposure context and does not change D01's 26/50 status or
qualify model data.

## 2026-10-15 cross-workspace attachment audit

Extended the shared report-download acceptance to a second real attachment
route on Mortgage Sources: the Fannie sample-format audit returns its server
filename and private-release flags through the same handler. A simulated HTTP
503 on that report displays the source error and creates no download. Focused
Fannie/HUD parser tests pass 10/10; the complete real-data D01 browser acceptance
now passes 71/71 (`artifacts/private/browser-qa-f32396b0c1ff/receipt.json`). This
improves M01-028 delivery coverage only; other workspace routes remain to audit,
and no Fannie performance payload or D01 model gate changed.

## 2026-10-15 POST workbook error handling

The direct-attachment handler did not cover three POST-based exports. Consolidated
response validation for KPI Monitor, SEC and affordability downloads: API errors
are parsed safely, HTML or unexpected MIME responses are rejected, and empty
payloads do not create files. Real KPI, SEC maturity and SEC interest-coverage XLSX
downloads pass ZIP integrity and contain `xl/workbook.xml`; affordability JSON keeps private scope and has
no credit decision. Injected HTTP 503 JSON and HTTP 200 HTML responses surface in
the UI without creating fake files for all three flows. The fresh verified-case
browser acceptance passes 83/83 at
`artifacts/private/browser-qa-2d436bad58fc/receipt.json`; focused workbook and
affordability backend tests pass 56/56. M01-028 remains Partial because other
workspace APIs and delivery routes still require scoped acceptance. D01 data and
model gates are unchanged.

## 2026-10-15 FHFA PUDB source continuation

Added a separate FHFA Enterprise PUDB 2025 acquisition/access source track after
confirming official unauthenticated downloads and the current file definitions.
The Census Tract file has 2,093,767 rows and 66 fields; unique source record keys
and Enterprise totals reconcile to FHFA's official record-count workbook. The
source reader returns only one-dimensional aggregates, applies a <30 small-cell
display suppression, and explicitly excludes performance, denial and D01-model
claims. Five parser/receipt tests pass; the latest 64-check browser acceptance
verifies the private profile/export and an injected export outage. See
`docs/FHFA_PUDB_CREDIT_ACCESS_REVIEW_VI.md` and
`artifacts/private/browser-qa-ce65ee3cf106/receipt.json`. This is a separate
credit-access case and does not change D01's 26/50 completion count or its
unmet multi-vintage gate.

## 2026-10-15 CFPB mortgage geography context

Identified and acquired the current CFPB Mortgage Performance Trends release as
a supplemental monthly geography series: four official CSVs, 2008-01–2025-12,
30–89-day and 90+-day delinquency for 507 county equivalents and 51
state/district records, plus the national record. The 216-month tables have no
blank or nonnumeric observation cells and are preserved in private storage with
SHA-256 receipts. CFPB attributes the data to the same NMDB sample family as
the existing FHFA aggregate package; it is therefore a monthly geography view,
not an independent validation sample, new Freddie vintage, loan-level panel,
or model feature. Minimum geography sample thresholds, imputation, revisions
and emergency-reporting limitations are documented in
`docs/CFPB_MORTGAGE_PERFORMANCE_TRENDS_REVIEW_VI.md`. The Mortgage Sources
workspace now includes a National/State/County panel. The reader verifies each
raw CSV against the private acquisition receipt before serving a selected
216-month series; export contains only selected aggregate observations and
source hashes. Three parser/receipt tests pass; the real-data browser acceptance
passes 86/86 (`artifacts/private/browser-qa-64d976250c71/receipt.json`), including
county FIPS normalization, export, and outage handling. The panel remains a
separate NMDB context view, not a Freddie join or model feature. D01 stays at
26/50.

## 2026-10-15 SEC attachment flow acceptance

Extended the real-data browser acceptance across five SEC GET attachments:
payment rules, note schedule, maturity schedule, interest coverage and annual
trend. The test checks server filenames and validates returned JSON row/period
counts, then injects an HTTP 503 into the coverage attachment and confirms the
UI reports the error without a fake download. Combined verified-case browser
acceptance passes 92/92 at
`artifacts/private/browser-qa-ed3b90bff36c/receipt.json`. M01-028 remains Partial
because other workspace routes still require scoped checks.

## 2026-10-15 cross-domain task acceptance refresh

Re-ran `scripts/browser_remaining_domains_qa.py` against the live local app and
actual registered sources. Its prior exact-count checks were stale: SEC now has
13 tasks and ABS has 10. Updated the acceptance to visit every current SEC pane
(issuer ratios, payment rules, note schedule, utility DSCR, facilities, filing
timeline, maturities, coverage, corporate memo, annual trends, statement fields,
concept evidence and source quality) and all ABS panes (overview, waterfall,
tranches, source checks, static/managed pools, ABS-EE coverage/dictionary, SOFR
and terms). The refreshed acceptance passed all 10 grouped checks: SBA's
2,190,504-record explorer and dictionary, all SEC and ABS tasks, Mortgage
transition/lifecycle details, reload state, and 390px layouts. No browser errors
occurred and the Retail holdout access ledger digest was unchanged. Receipt and
private screenshots: `artifacts/private/remaining-domains-qa-904024f23f91/`.
This refreshes UX/task coverage; it does not change the D01 26/50 count, add
loan-performance vintages, or qualify any model.

## 2026-10-15 cross-workspace export failure continuation

Extended the live-app acceptance to inject HTTP 503 only after each verified
workspace had loaded. Retail model-dossier JSON, SBA aggregate report, ABS period
report, World Bank country report, and sovereign-default report each showed the
server error and produced no download. The receipt records the existing task
checks plus these five delivery checks: 16/16 grouped checks passed with no
JavaScript errors and the Retail holdout access ledger unchanged. Receipt and
private screenshots: `artifacts/private/remaining-domains-qa-7f475e378476/`.
The source-level NSMO review remains current: FHFA's 2026 PUF contains quarterly
performance through 2025Q3 but requires acknowledgement of its monitoring notice
and terms before download; Freddie/Fannie loan-level sources remain account or
registration gated. No unrelated application/aggregate table is promoted to a
mortgage-performance vintage. D01 stays at 26/50 and M01-028 remains Partial.

## 2026-10-15 ABS specialized attachment acceptance

Fixed five specialized ABS source/benchmark exports to use the shared validated
JSON download handler. Real browser acceptance now downloads ABS-EE coverage,
ABS-EE dictionary, managed-pool, static-pool history and SOFR benchmark reports,
validates their private scope and absence of local filesystem paths, then injects
HTTP 503 for each route and confirms a visible error with no fake file. The
focused acceptance passes 22/22 at
`artifacts/private/abs-browser-qa-52d096bc29bd/receipt.json`; JavaScript syntax
and browser execution are clean. This closes these five attachment routes only:
Retail sub-workspace exports and remaining API deliveries still need scoped
acceptance. D01 remains 26/50, M01-028 remains Partial, and no data/model gate
changed.

## 2026-10-15 Retail attachment failure continuation

Replaced direct anchor downloads in five Retail report flows (model dossier,
data contract, subgroup study, local explanation and cohort-client explanation)
with the shared JSON response handler. A failed response now surfaces in the UI
and cannot become a downloaded error file; state-bound export buttons are enabled
only after their evidence is loaded. Browser acceptance confirms successful
private export parity and HTTP 503/no-fake-download behavior. The combined
workspace acceptance passes 18 grouped checks at
`artifacts/private/remaining-domains-qa-63f3f8db24cb/`; Retail data contract
(133 source-category rows), governance dossier (six-stage lineage), and subgroup
exports pass their dedicated browser suites. Local explanation acceptance passes
6 checks and cohort explanation passes 9 checks, including all 4,499 validation
clients, token/page behavior, export scope, 390px layout, no holdout-ledger change,
and 503 handling. Receipts are listed in the M01-028 row above.

This closes the Retail and ABS attachment routes called out in the previous
checkpoint, but not the full M01-028 route inventory. D01 remains 26/50; no
additional Freddie/Fannie/NSMO/Ginnie loan-performance vintage was acquired, and
no model fit or qualification gate changed. The next engineering pass starts
with Portfolio workbook/import/review deliveries and continues across other
workspace-specific routes.

## 2026-10-15 Portfolio export failure acceptance

P4 acceptance now covers inventory JSON and movement bridge exports end to end. It verifies downloaded JSON against the API response using explicit UTF-8 decoding, checks that missing risk inputs remain null and that cross-currency totals are not manufactured, and injects HTTP 503 into both export routes to confirm a visible error with no fake attachment. The expanded focused acceptance passes 11/11 grouped checks at `artifacts/private/p4-acceptance-qa-58361d0d2a27`; scenario, ECL, tail-risk, and convergence exports also match their API payloads and reject HTTP 503 without fake attachments.

The combined Portfolio/Retail workbench acceptance also passes 15 grouped checks at `artifacts/private/product-workbench-qa-5cc302c5a26d`: source-bound Portfolio summary and concentration, review drafts, native-currency Excel export and HTTP 503 behavior, on-demand movement/scenario tasks, keyboard/mobile behavior, and Retail saved evidence, validation, subgroups, and client explanation export. An expected browser console error from the synthetic 503 is accounted for explicitly. This closes the tested P4 attachment paths; it does not close the full M01-028 route inventory. D01 remains 26/50, and no additional gated loan-performance data or model qualification gate changed.


## 2026-10-15 Bankruptcy profile export failure coverage

Added a real-source browser acceptance for the bankruptcy ratio profile export: the scoped JSON matches the verified source evidence, retains the 64-feature and horizon/precision audit, and an injected HTTP 503 is shown in the UI without creating a fake download. The suite passes 9/9 checks at `artifacts/private/bankruptcy-browser-qa-6949e456b58c/receipt.json`.

The bankruptcy model catalog currently has no verified snapshot, so its report route cannot be exercised with real evidence; the saved-model export remains pending an available verified view. This adds one delivery route to M01-028 and does not change D01 data/model readiness.
