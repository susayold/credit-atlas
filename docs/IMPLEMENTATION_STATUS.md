# P2 / D01 implementation status

Started 2026-10-08. Goal: implement the first CreditAtlas module according to
chapter 47 of the consolidated research plan.

| Release | Status | Required evidence |
|---|---|---|
| R0 — foundation | In progress | Pinned engine/source, clean rebuild, checks and resource receipt |
| R1 — descriptive app | Not complete | Verified panel/cohort/vintage/transitions/episodes/loss, saved findings and browser QA |
| R2 — multi-vintage data | Not complete | Required annual vintages, label support and frozen temporal protocol |
| R3 — model study | Not complete | Actual same-cohort fitting/calibration/validation/OOT and model card |
| R4 — final handoff | Not complete | Full reproduction, export/browser/privacy checks and case study |

## Verified checkpoint — 2026-10-08

- Pinned engine commit: 8d9994cfcb91fe871d66a4238c3f56053d71e920.
- Actual Release 47 annual sample 2012 rebuilt: 50,000 loans and 4,510,559
  loan-months. Fresh case: d01-a24484b21a21.
- Foundation rebuild: 192.264 seconds; measured peak working set 812,138,496 bytes.
- Engine suite: 375 tests passed in the new environment.
- Full eight-stage rerun: 13 tables and four stable summaries reconciled;
  zero differing rows. This proves descriptive foundation reproduction,
  not completion of the final model/app research release.
- Browser acceptance: latest 42 checks passed; stale/missing/unlisted run, connection-failure, malformed JSON, HTTP 500 JSON, HTTP 502 HTML, and run-catalog HTTP 503 states verified; five key screens at 390px
  at desktop and 390px mobile. Includes filters, real loan timeline, report download,
  isolated QA finding creation/review/history and reload. No console/JS errors.
- Latest complete suite: 468 tests passed (375 engine + 93 application),
  rerun on 2026-10-09 after public-context acquisition changes.
  Covers reviews, frozen evidence and method integrity, HTTP boundaries,
  run-scoped Parquet queries, acquisition, registration, study preparation,
  monitoring, episode follow-up, reporting-year transitions and report supplements.
- Episode follow-up audit: 4,902 confirmed events, 82 grouped support rows,
  6/12-month horizons, preserving actual confirmation dates. Implemented in the
  transitions view; gaps, unknowns, terminal exits and source end are separate.
- Reporting-year transitions: 4,460,559 adjacent pairs, 1,091 year cells and
  94 lifetime cells; 2012–2026 opening reporting years. Exact reconciliation
  to pooled years and both frozen engine matrices passes. UI/URL/export year
  filters, origin denominators and unavailable-year states are tested.
- Monitoring/investigation is implemented from frozen evidence; no unsupported
  live freshness, drift or calibration alarms are generated.
- Private report schema 2 includes lineage-bound monitoring and selected-segment
  episode follow-up and reporting-year transitions. Unchanged evidence/code/filters produce identical exports.
- Package audit checks all 50,000 actual source IDs against four explicitly served
  static assets; no match. Private paths are excluded from Git candidates.
- Local sequential HTTP benchmark p95 spans about 0.06–0.24 seconds across
  eight routes. This is a small current-machine engineering check, not a load test.
- Source registration and prepare-study are implemented. Actual 2012 study
  support is train 100 positive / 43,227 negative; the other roles have zero.
  The command preserves candidate-protocol blockers and never fits models.
- Train-only feature audit is implemented: strict pinned allowlist, rederived
  split/joins, private access log, coverage, saved JSON encoder and parity across
  all 43,327 included actual train rows. No final-test predictors or risk models
  were fitted. Feature availability/ablation review and study freeze remain unmet.
- Models UI reads bounded aggregate prepared-study/feature evidence and marks
  related legacy/changed artifacts unavailable. Source IDs/private paths are not
  part of this API contract.
- Models UI now also reads lineage-verified development assessments: blocked
  attempts show reason codes and no metrics; verified development results expose
  only same-cohort raw/calibrated aggregate metrics. Model JSON and loan-level
  scores stay private. Actual 2012 displays BLOCKED_BEFORE_FIT and five blockers.
  Assessment artifacts, reviewed settings, cohort denominators and verification
  receipts are checked before summaries; changed evidence is unavailable.
- Gated multi-case assess-study adapter is implemented. It composes shared
  constant/logistic/boosting, bounded train-only C tuning, separate calibration,
  raw/calibrated validation metrics and persisted model/calibrator parity.
  Synthetic software integration checks cover the complete development flow;
  actual 2012 stops at BLOCKED_BEFORE_FIT with no model artifacts or scores.
  No actual champion, final-test assessment or qualified scoring exists.
- Release-47 semantic trace now passes on the supplied 2012 corpus: all 17
  field sentinels, 20 categorical fields, six date conversions, HARP flags,
  percentage-point casts and 4,510,559 delinquency/termination mappings.
  See D01_CANONICAL_SEMANTIC_AUDIT_VI.md and its private receipt. This does
  not authenticate the publisher release or prove cross-vintage compatibility.
- Full repository suite rerun on 2026-10-15 in fresh sequential batches after
  the reproduction receipt and batch-runner changes: 1,568/1,568 passed, zero
  failures/errors/skips. Receipt and reproduction command are in
  TEST_SUITE_2026-10-15_VI.md.
- Latest after NSMO status parser: full application and vendor suite passed
  1,574/1,574 via `scripts/test.ps1` in 391 seconds; receipt:
  `artifacts/private/test-suite-direct-20261015/receipt.json`.
- Latest after NSMO CSV-streaming extension: 1,577/1,577 passed via
  `scripts/test.ps1` in 341.4 seconds; receipt:
  `artifacts/private/test-suite-direct-20261015-nsmo-stream/receipt.json`.
- M01-022 descriptive export is verified across five real-case scopes. The
  wrapper/report schemas, case/run/method digests, empty-year behavior,
  deterministic repeat, 50,000-ID scan and fail-closed unsupported metric
  filters pass. Latest 25-check real-data browser export/mobile flow also
  passes; model-score consumer remains behind the unqualified R3 gate.
- R0 still needs dependency/resource documentation and final expanded package
  review; current runtime/engine/storage and static privacy evidence is detailed
  in D01_RELEASE_READINESS_VI.md. Redistribution rights for the copied upstream
  engine and two missing dependency license metadata fields remain unresolved.
  R1 still needs complete independent acceptance/coverage audit and final
  analyst/handoff documentation. The descriptive data/method card is in
  D01_DATA_AND_METHOD_CARD.md.
- R2/R3 remain unmet: only 2012 is available. 102 early-entry positives
  include 89 Relief and 13 non-Relief. No qualified mortgage model was fitted.

## Source expansion through HTTP

The user requested additional annual sample downloads through API/HTTP.
Direct unauthenticated requests returned 401; the CLI access probe returned 403.
Both identify unavailable unauthenticated access. No additional annual ZIP
was downloaded. Official documentation directs users to authenticated Clarity.

Commands source-access and download-samples now support direct HTTP acquisition.
Download manifests and optional Netscape cookie files remain under ignored
data/private/access. The downloader allows only the official Clarity HTTPS host,
rejects other-host redirects, bounds download/decompressed size, checks member
names and CRC, records SHA-256, and omits signed URLs/cookies from receipts.
Archive checks are separate from source rights/schema/population qualification.
Additional files do not become model-ready automatically.

The user resumed acquisition on 2026-10-09 and confirmed there is no Clarity
login session. Additional loan vintages remain blocked by authentication.
Public macro acquisition completed separately: three FRED series, 4,049 native
observations and 171 case-month context rows. Unemployment is available for
170 months, mortgage-rate monthly means for 171, and HPI stays quarterly.
All saved output hashes verified. These descriptive series cannot replace loan
performance labels or qualify the multi-vintage model study. See
PUBLIC_MORTGAGE_CONTEXT.md for actual files, sources and limitations.

**Update 2026-10-15:** refreshed the public Freddie Mac references from the
current publisher page. The Release 47 example ZIP and July 2026 File Layout
were acquired over HTTPS and hash/CRC checked. Layout/example comparison found
31 origination fields and 35 performance fields, matching each example row;
the 1,000 origination IDs and 12 performance IDs have no overlap, so the files
are not joined as a loan panel. This adds parser-reference evidence only and
zero annual vintages. The current official page says SFLLD covers about 56
million loans through March 31, 2026 and directs users to register/sign in to
Clarity for full, by-year and sample data; the login requirement remains the
data gate. See FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md and
`artifacts/private/freddie-release47-reference-audit-c3ce87022b8b/audit.json`.

Mortgage real-data browser acceptance was rerun on 2026-10-15: 39 checks pass
in `artifacts/private/browser-qa-7a281849bd29`. This verifies the current
descriptive UI flow, not R2/R3 completion. R2/R3 remain unmet until authorized
annual vintages, multi-vintage support/protocol and actual model gates pass.

All release status rows above remain conservative until their complete
acceptance requirements have been audited.

Latest evidence:

- Browser (2026-10-15): artifacts/private/browser-qa-7a281849bd29/receipt.json, 39 checks PASS.
- Chart/support (2026-10-15): docs/D01_CHART_SUPPORT_AUDIT_VI.md; six numerical/data-support checks PASS.
- Reproduction (2026-10-15): docs/D01_REPRODUCTION_AUDIT_VI.md; fresh eight-stage source-manifest comparison PASS, 13 tables and four stable summaries have zero differences.
- Descriptive handoff: docs/D01_CASE_STUDY_VI.md consolidates scope, target, KPI denominators, findings, data/model gates and evidence links; final model card/demo remain pending R2/R3.
- Package: artifacts/private/package-audit-e96ce7a09397/receipt.json.
- Benchmark: artifacts/private/api-benchmark-bc3af91d5fd0/receipt.json.
- Study: artifacts/private/study-e7b5a47685c1/study-complete.json.
- Feature audit: artifacts/private/feature-audit-585be3bb2299/feature-complete.json.
- Export contract: docs/EXPORT_CONTRACT.md.
- Actual blocked assessment: artifacts/private/assessment-76010ad019fd/assessment-complete.json.
- Development adapter: docs/DEVELOPMENT_ASSESSMENT.md.
- Import/study instructions: docs/SOURCE_AND_STUDY_WORKFLOW.md.

- D01 end-to-end descriptive reproduction on 2026-10-15: fresh valid case has
  byte-identical report, normalized snapshot parity, reproduced pre-fit model
  gate (no fitting), and 42/42 real-data browser checks, including HTTP 500 JSON, 502 HTML, and run-catalog 503 failures. M01-029 remains Partial
  pending qualified multi-vintage model/calibration/final-OOT evidence; see
  D01_REPRODUCTION_AUDIT_VI.md and its private receipt.
