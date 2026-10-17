# D02 — NSMO mortgage-performance workspace

Updated: 2026-10-16. D02 is a separate FHFA/CFPB National Survey of Mortgage
Originations (NSMO) case. It does not use, extend, or relabel the Freddie Mac
D01 panel.

## What is ready

- FHFA v7.0 PUF (page updated 2026-05-27) was downloaded after the user
  authorized the Notice of Monitoring and NMDB Terms acknowledgement.
- The ZIP, CSV and detailed receipts are held in a private local store outside
  the public repository. Only aggregate, non-identifying profile evidence is
  described here.
- 62,359 sample mortgages, 587 columns, 2013–2024 origination years, 51
  quarterly `perf_status_MMYY` columns from 2013Q1 to 2025Q3, 3,180,309 status
  cells, unique nonblank `nsmoid`, no malformed rows, valid positive
  `analysis_weight`, and no unknown performance codes.
- Codebook-grounded streaming parser accepts the lowercase headers in the
  publisher file. Focused tests and a full-file parser pass are complete.
- All 587 PUF headers now reconcile one-to-one with the official v7.0 Appendix C
  and SAS label file; the sanitized dictionary records question/wave metadata,
  PDF location, timing class, and conservative predictor-use gates. The app now
  has a searchable dictionary and value labels from SAS formats.
- Twenty-two deduplicated official questionnaire packages covering waves 1–46
  are archived privately with source hashes. A PUF/SAS wave-coverage audit
  reconciles 319 survey fields × 46 waves (14,674/14,674 field-wave cells) with
  zero unmapped values; a sanitized 319-row coverage index is now shown in the
  dictionary. It distinguishes observed response, all-row not-asked, partial
  not-asked, and not-applicable waves. PDF question-number/text extraction is a
  locator only; manual item/scale equivalence review remains open.
- A six-item pilot found the exact item phrase in all 22 packages for credit
  familiarity, late-payment/default attitudes, expected mortgage-payment
  difficulty, and short-term bill-paying resilience. SAS formats also confirm
  matching broad response scales across versions for these candidates. A
  sanitized candidate crosswalk is in `docs/data/nsmo-v70-wave-item-comparability.csv`;
  this is descriptive-trend readiness only, not origination predictor approval
  or a measurement-invariance test. Follow-up wording review found a version
  break in X94A: “borrow enough money” (waves 1–10) changes to “borrow a
  significant amount” (waves 11–46), while the checked three-category response
  scale stays the same. Long-run trend views must stratify/sensitivity-test
  this wording version; see `docs/NSMO_WAVE_ITEM_REVIEW_VI.md`.
- Appendix D Table 1 weighted tabulations were independently recomputed for
  seven survey fields × 11 origination years × purchase/refinance × three
  response categories: 462/462 cells match the published rounded percentages.
  This is a selected consistency check, not a design-variance validation.
- The 51-quarter state audit found zero out-of-domain nonblank codes. In the
  actual PUF, `Close_Status_0925` has only 1=open and 2=terminated; all open
  records have no close date and all terminated records have a close date.
  Across the panel, every A (history no longer reported) belongs to a terminated
  mortgage, B does not occur, and 678 mortgages have no observed C/1–9 status.
  These findings inform eligibility design but do not yet define an at-risk set.
  A separate aggregate-only feasibility screen tested a candidate four-quarter
  endpoint from C/1/2 baselines. It found 872,888 current-state baseline
  snapshots with a full 4-quarter horizon, but 42,236 same-month termination
  ambiguities and 83,092 competing termination censors; these are repeated
  snapshots, not unique loans or rates. A unique-support extension found about
  59.7k distinct mortgages with at least one C landmark and a full horizon;
  censor/ambiguity shares vary from about 8% to 23% across broad origination
  vintage groups. See `NSMO_TARGET_FEASIBILITY_VI.md`.
- A second domain audit scans and emits aggregates only for 30 origination
  mortgage/borrower fields (including the cash-out flag), five origination
  VantageScore fields, 51 quarterly respondent-score fields, and 23 quarterly
  forbearance fields. All 109 selected fields reconcile to official SAS format
  domains. Scores are bucketed as published; exact score values and loan rows
  are never returned by the API.
- FHFA NMDB national performance aggregates were downloaded as a separate public
  benchmark: 1,568 market-series-quarter rows across four markets and four rates,
  2002Q1–2026Q2. The latest two quarters are preliminary. This benchmark adds
  cycle context, not NSMO loan outcomes or model-training rows; see
  `NMDB_PERFORMANCE_CONTEXT_VI.md`.
- Edge browser QA against the local hash-verified PUF passes for the 30-field
  selector, 46 survey waves, origination score coverage, quarterly score trend,
  23-quarter forbearance table, termination breakdown, and selectable
  unweighted/weighted observed transition matrices. No record IDs are rendered.
- The dynamic first-entry screen now reconciles PUF population, entry and exits
  by origination vintage. Entry share ranges from 83.64% (2013 vintage) to
  96.84% (2020); 2024 is 96.39%. Most pre-entry exclusions are non-observation, not observed
  90+ or adverse states. The app labels this as vintage selection into the
  screen, not an event rate.

## Build stages

| Stage | Work | Exit evidence | State |
|---|---|---|---|
| D02-0 — access and storage | Review FHFA gate/terms, download official v7.0, preserve source hashes, keep PUF private | Official URL, release, ZIP/CSV hashes, user authorization record, no secrets | Complete |
| D02-1 — structural profile | Check schema, keys, row widths, vintages, quarterly fields, weight domains and code domain | Aggregate-only audit receipt; parser reconciles the actual PUF | Complete |
| D02-2 — codebook reconciliation | Map every physical field to the 322 survey and 265 supplemental entries; distinguish wave variants, as-of timing, termination/forbearance/MTM-LTV and score series | Versioned 587-field dictionary, 587-row Excel feature-gate inventory and 319-row field/question/routing crosswalk; 587/587 header match, SAS labels/formats, Appendix D weighted-cell check, 319×46 wave coverage, questionnaire scale review and FHFA Tables 3–6 reconciliation | Structural coverage complete; routing inventory resolves 58 conditional rows to 12 gate fields, leaves 12 retired gateways unnamed, and identifies 249 rows without codebook conditions. Seven omitted question refs reconcile to applicable questionnaire items; x17g_1 remains flagged for a wording variant. Exact wave/mode path graph remains open; response-mode equivalence is not identifiable. Predictor allowlist remains closed; target/risk-set, as-of and governance reviews remain open. See `NSMO_RESPONSE_MODE_REVIEW_VI.md`, `NSMO_PREDICTOR_TIMING_REVIEW_VI.md` and `NSMO_ROUTING_REVIEW_VI.md`. |
| D02-3 — state and observation-risk audit | Produce per-quarter weighted/unweighted status distributions, transition counts, entry/exit and censoring profiles; reconcile `A/B/K/M/P/Q/S` semantics to FHFA documentation | Reconciled state matrix with denominators and a documented choice of valid observed risk set | Descriptive state/censoring audit complete, including all 50 adjacent-quarter observed transition matrices. Candidate C/1/2 snapshots screened for a four-quarter horizon; unique-loan support and censoring by origination vintage are quantified. The first-entry audit partitions all 62,359 PUF loans by pre-entry reason and 2013–2024 vintage, then reconciles entry and exits; observed vintage entry share varies 83.64%–96.39%, mostly with pre-entry non-observation. This demonstrates nonuniform screen inclusion, not risk differences. Tied-month audit finds only code A (C: 42,236; 1: 126; 2: 21), but exact within-month ordering, differential censoring, and risk-set protocol remain open. |
| D02-4 — descriptive workspace | Add a separate UI/API with cohort, survey wave, borrower/mortgage mix, credit-score availability, delinquency-state snapshots, forbearance and termination views | Browser/API acceptance; every metric shows grain, numerator, denominator, weights and source caveat; no IDs | Aggregate dashboard covers origination year and 46 waves; 30 mortgage/borrower fields; five origination scores and 51 respondent quarterly-score snapshots; 23 forbearance quarters; termination and 50 transition pairs; searchable 587-field dictionary with 319 survey-field wave coverage and nine item comparability notes. X94A detail surfaces its wording-version split. Target-feasibility panel compares one-landmark vs repeated-C support, an origination-month-aligned feasibility screen, distinct/repeated adjacent-to-90+ support by vintage, tied-month status counts, and first-entry population-selection reconciliation by vintage; all label unweighted counts and no-PD limitations and verify receipts against the PUF SHA. A separate FHFA NMDB aggregate benchmark adds 2002Q1–2026Q2 market-performance context through its own hash-checked API, selectable trend panel and 1,568-row Excel workbook; it does not change NSMO outcomes. A new Table 3 panel shows response mode counts; a Table 4–6 panel reconciles returns, usable responses and release scope, labels waves 47–48 outside the PUF, and makes the no-record-linkage limitation explicit. HUD FHA Tables 1–6 now render separately as aggregate-only context: monthly performance, 90+ reason mix, subgroup rates, foreclosure flow/stock/claims, geographic REO recovery and loss components, with source-specific denominators and caveats. HUD raw PDF and Portfolio Snapshot binary downloads remain blocked (HTTP 403); no loan-level HUD payload is claimed. Other eligible domain extensions remain open. |
| D02-5 — target protocol | Decide whether the evidence supports a quarterly snapshot outcome or an observed first-entry endpoint; specify horizon, event, competing termination, censoring, missing/suppressed rules and weight/variance method | Signed/frozen target and evaluation protocol before outcome-driven analysis | Feasibility screens cover repeated/current-state C landmarks, earliest eligible C per loan, origination-aligned snapshots, adjacent-to-90+ transitions, and one-time dynamic entry after origination. The dynamic screen contains 57,311 entries, 695 first observed 90+ exits, and 887,861 unweighted loan-quarter intervals; entry share differs across vintages and is dominated by pre-entry missingness. New 6/12/24-month support by `Open_Year` reconciles to the PUF totals; 2024 has no eligible 24-month baseline. One earliest eligible C landmark per mortgage yields 41/156/302 observed 90+ mortgages at 6/12/24 months (61,645/59,703/55,701 eligible loans); repeated landmarks yield 623/753/735 unique mortgages ever positive with overlap/dependence. These are distinct descriptive supports, not rates or incidence. Recommended direction: do not claim origination-time PD from the 65-event origination-aligned screen; review a separate delayed-entry servicing-monitoring estimand only if needed. No target/PD/model outputs. Population/estimand, competing risks, censoring/selection correction, predictor timing, and design variance remain unresolved. See `NSMO_TARGET_FEASIBILITY_VI.md`, `NSMO_ORIGINATION_FEASIBILITY_VI.md`, and `NSMO_HORIZON_BY_VINTAGE_VI.md`. |
| D02-6 — model study | Only if target support and temporal cohorts are adequate; use time-separated train/calibration/validation/test and report weighted plus unweighted diagnostics | Reproducible model card, calibration/threshold review and source-specific limitations | Not started; current origination-aligned support (65 observed 90+ statuses) is insufficient to justify a multi-predictor model. Revisit only after target/estimand and additional validated outcome data are available. |

### Additional aggregate market context — 16/10/2026

FHFA NMDB's quarterly national performance extract has been downloaded and
curated separately from the NSMO PUF. The workbook and page show 30–89 DPD
(the FHFA P3089DL combination of 30–59 and 60–89 day categories),
90+ DPD, foreclosure/bankruptcy/deed-in-lieu, and forbearance across four
publisher-defined mortgage markets. It strengthens the descriptive and
cross-source context only. It does not resolve the D02 target gate, competing
termination, censoring, outcome support or survey-design variance; D02-5 and
D02-6 remain open. Detailed definitions, source hashes and refresh steps are in
`NMDB_PERFORMANCE_CONTEXT_VI.md`.

### Source refresh check — 16/10/2026

Reviewed the current FHFA NSMO and NMDB pages and HUD FHA portfolio snapshot
index. FHFA still lists NSMO v7.0 as updated 27 May 2026, with 62,359 mortgages
and performance through 2025Q3; the NMDB aggregate statistics release is dated
30 September 2026, and the app already includes its available 2026Q2 extract.
HUD's monthly FHA snapshot page currently links through August 2026, matching
the project's latest captured month. No newer eligible release was identified
to download in this review. Sources: [FHFA NSMO](https://www.fhfa.gov/data/nsmo),
[FHFA NMDB program/data index](https://www.fhfa.gov/programs/nmdb), and
[HUD Single-Family Portfolio Snapshot](https://www.hud.gov/stat/sfh/fha-sf-portfolio-snapshot).

### Excel reference handoff — 16/10/2026

D02-4 now offers a five-sheet Excel reference workbook for the four public
metadata tables: the 587-field dictionary, 377 SAS value labels, 319 survey
field-wave coverage rows, and nine item-comparability notes. The data sheets are
filterable Excel Tables with frozen headers/first column. The local download is
`/downloads/nsmo-reference.xlsx`; details and refresh steps are in
`NSMO_EXCEL_REFERENCE_VI.md`. Focused workbook/API tests pass 16/16 and the
dictionary browser acceptance passes 7/7 with no page errors. At this checkpoint
the original listener on port 8770 served the prior server version. The local
service has since been restarted with the public code version and now returns
the Excel download routes from the private D: runtime root. Workbook and route
changes are recorded in later continuation checkpoints.

### First-observed transition support — 16/10/2026

D02-5 now has a reproducible, identity-free aggregate screen for adjacent
quarter transitions into observed 90+ delinquency, distinct-mortgage support,
and the first observed 90+ status by prior C/1/2 state. The source PUF audit
reconciles 62,359 unique mortgage IDs, 587 columns and 51 quarters; totals and
vintage groups are served only after receipt-to-PUF hash verification. The
dashboard displays repeated transitions separately from unique loans and does
not call these counts event incidence. The tied-month status breakdown is also
hash-bound to the same PUF and reconciled by vintage/state. Focused API/view/audit
tests pass 28/28; Edge acceptance passes 11/11 with no JS errors, including the
tied-month status table, shared-vintage filter and mobile scroller. This advances
feasibility evidence only: D02-5 is not frozen and D02-6 remains unstarted.

### Same-month termination status audit — 16/10/2026

A supplemental audit reads the performance code in the quarter whose month ties
`Close_Year/Close_Month`. Every tied snapshot is code `A`: 42,236 after baseline
`C`, 126 after baseline `1`, and 21 after baseline `2`. Appendix C defines `A`
as performance history no longer reported, in most cases after closure; it does
not supply the exact day within the month. The dashboard now reports these counts
by baseline state and filtered origination vintage while keeping them in the
ambiguous/censor category. This adds a code-level description but does not resolve
event-versus-termination order or freeze a target. See
`NSMO_TARGET_FEASIBILITY_VI.md`.

## Intended metrics and guardrails

The initial app is descriptive, not decisioning. Current views show origination
year/wave; categorical mortgage/borrower attributes; VantageScore bins and
availability by role/quarter; unweighted counts alongside explicitly named
descriptive weight sums; quarterly status composition; forbearance with the
answered-code denominator; termination status/date consistency; and adjacent-
quarter transitions conditioned on both snapshots being observed codes C/1–9.
Every view separates delinquency codes from non-observation/administrative
states. Weight sums are not loan counts or PD; weighted shares have no
design-based variance estimate and are not incidence estimates.

Do not use retrospective survey answers, future-quarter VantageScore, future
forbearance, or mark-to-market LTV as origination predictors. Do not infer that a
loan is performing from blank, history-ended, not-yet-reported, archive-gap,
pre-open or suppressed statuses. A quarterly snapshot does not reveal exact
event dates and may miss delinquency between reporting dates. No target is
defined in the current build.

## Public-release and citation rules

Only source code, synthetic tests and sanitized technical documentation may be
committed. Never commit the PUF, identifiers, row-level exports, screenshots,
or private receipts. The FHFA Terms prohibit attempts to identify individuals
and require a caveat that post-download analysis is the users'/authors' own and
is not attested to by FHFA. Do not use FHFA/NMDB marks to imply endorsement. If
the data are cited, include the exact FHFA-required disclaimer in the report:

> The opinions and analyses contained herein are solely of the users/authors of any data analyses or papers, and the FHFA cannot and does not attest to nor vouch for the quality, accuracy, or timeliness of the data, or analyses derived from these data after the data has been retrieved from FHFA.gov.

## Reproduce the local audits

The commands below require the current FHFA v7.0 PUF and matching SAS label/
format downloads in a private local folder. They scan local files and write only
aggregate receipts; never commit those receipts or the source payload.

```powershell
$puf = 'data\private\mortgage\nsmo-2026-05-27\puf\nsmo_v70_1324_puf.csv'
$docs = 'data\private\mortgage\nsmo-2026-05-27\source_docs'
python scripts\audit_nsmo_performance_states.py `
  --puf-csv $puf --sas-labels "$docs\nsmo_v70_labels.sas" `
  --sas-formats "$docs\nsmo_v70_formats.sas" `
  --output artifacts\private\nsmo-performance-state-audit\receipt.json
python scripts\audit_nsmo_target_feasibility.py `
  --puf-csv $puf `
  --output artifacts\private\nsmo-target-feasibility\receipt.json
python scripts\audit_nsmo_domain_aggregates.py `
  --puf-csv $puf --sas-labels "$docs\nsmo_v70_labels.sas" `
  --sas-formats "$docs\nsmo_v70_formats.sas" `
  --field-dictionary docs\data\nsmo-v70-field-dictionary.csv `
  --output artifacts\private\nsmo-domain-aggregate-audit\receipt.json
python scripts\audit_nsmo_weighted_tabulations.py `
  --puf-csv $puf --weighted-pdf "$docs\nsmo-appendix-d-v70.pdf" `
  --output artifacts\private\nsmo-weighted-tabulations\receipt.json
python scripts\audit_nsmo_wave_response_coverage.py `
  --puf-csv $puf --field-dictionary docs\data\nsmo-v70-field-dictionary.csv `
  --value-labels docs\data\nsmo-v70-value-labels.csv `
  --output artifacts\private\nsmo-wave-response-coverage\receipt.json `
  --public-coverage-csv docs\data\nsmo-v70-wave-coverage.csv
```

The live app verifies that the private aggregate receipts match the local PUF
SHA-256, the public dictionary SHA-256, and the downloaded SAS source hashes
before returning `/api/nsmo-domains`.

## Source

- [FHFA NSMO PUF and release information](https://www.fhfa.gov/data/nsmo)
- [Official Notice of Monitoring and Terms gate](https://www.fhfa.gov/data/nsmo/puf)
- [May 2026 codebook and unweighted tabulations](https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-c-v70.pdf)
- [May 2026 technical report](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf)
- [May 2026 weighted tabulations, Appendix D](https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-d-v70.pdf)
- [Official SAS labels](https://www.fhfa.gov/document/d/nsmo/nsmo_v70_labels.sas) and [SAS formats](https://www.fhfa.gov/document/d/nsmo/nsmo_v70_formats.sas)
- Detailed review: `D01_NSMO_SOURCE_REVIEW_VI.md`

### HUD FHA Table 1–6 context extension — 16/10/2026

The HUD benchmark now renders its remaining report tables in the app: Table 2
new-90+ reason distributions (22 rows), Table 4 foreclosure flow/stock/claims
(37), Table 5 geographic REO recovery (50), and Table 6 REO loss/disposition
detail (13), in addition to the existing Table 1 monthly trend and 60 Table 3
subgroups. The API validates the source schema/coverage and returns aggregate
rows only. KPI cards identify partial reason periods, separate foreclosure
flows from stock and annualized rate, show REO percentage-point changes, and
state that Table 6 components do not sum to net loss. These HUD rows remain a
separate program benchmark: they do not increase NSMO/Freddie loan support or
change D02-5 target feasibility. HUD's direct PDF and XLSX downloads still
return HTTP 403; no binary source acquisition is claimed.

The HUD browser acceptance passes 7/7 grouped checks with no page errors,
including all six table row counts, latest report KPI examples, Excel download
and 390px mobile layout. Receipt is stored privately at
`artifacts/private/hud-tables-browser-qa-20261016/receipt.json`. The D02 Excel
bundle includes all 16 public source CSV tables across NSMO, NMDB and HUD, with
19 total workbook sheets including guides/definitions. Four HUD detail-table
CSV fixtures and workbook contracts are covered by the focused public tests.
