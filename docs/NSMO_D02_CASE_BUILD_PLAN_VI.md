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
  or a measurement-invariance test.
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
- Edge browser QA against the local hash-verified PUF passes for the 30-field
  selector, 46 survey waves, origination score coverage, quarterly score trend,
  23-quarter forbearance table, termination breakdown, and selectable
  unweighted/weighted observed transition matrices. No record IDs are rendered.

## Build stages

| Stage | Work | Exit evidence | State |
|---|---|---|---|
| D02-0 — access and storage | Review FHFA gate/terms, download official v7.0, preserve source hashes, keep PUF private | Official URL, release, ZIP/CSV hashes, user authorization record, no secrets | Complete |
| D02-1 — structural profile | Check schema, keys, row widths, vintages, quarterly fields, weight domains and code domain | Aggregate-only audit receipt; parser reconciles the actual PUF | Complete |
| D02-2 — codebook reconciliation | Map every physical field to the 322 survey and 265 supplemental entries; distinguish wave variants, as-of timing, termination/forbearance/MTM-LTV and score series | Versioned 587-field dictionary, 587/587 header match, 587 SAS labels, 59 formats / 377 value labels, timing gates, Appendix D 462/462 selected weighted-cell check, 319×46 SAS-coded wave coverage and a six-item questionnaire pilot | Structural wave coverage complete; six common-item candidates identified for descriptive trend review; routing, response-mode/population equivalence and predictor allowlist still require formal review |
| D02-3 — state and observation-risk audit | Produce per-quarter weighted/unweighted status distributions, transition counts, entry/exit and censoring profiles; reconcile `A/B/K/M/P/Q/S` semantics to FHFA documentation | Reconciled state matrix with denominators and a documented choice of valid observed risk set | Descriptive state/censoring audit complete, including all 50 adjacent-quarter observed transition matrices. Candidate C/1/2 snapshots screened for a four-quarter horizon; unique-loan support and censoring by origination vintage are now quantified. Close-month ambiguity, differential censoring, and risk-set protocol remain open. |
| D02-4 — descriptive workspace | Add a separate UI/API with cohort, survey wave, borrower/mortgage mix, credit-score availability, delinquency-state snapshots, forbearance and termination views | Browser/API acceptance; every metric shows grain, numerator, denominator, weights and source caveat; no IDs | Aggregate dashboard covers origination year and 46 waves; 30 mortgage/borrower fields; five origination scores and 51 respondent quarterly-score snapshots; 23 forbearance quarters; termination and 50 transition pairs; searchable 587-field dictionary with 319 survey-field wave coverage. Target-feasibility panel compares one-landmark vs repeated-C support. It now also shows the separate origination-month-aligned feasibility screen by vintage, explicitly labels unweighted support and no-PD limitations, and verifies the receipt against the PUF SHA through an aggregate-only API. Edge headless QA passes desktop/mobile; API, 20 focused NSMO view/feasibility tests, and the public-mirror suite pass. Other domain extensions remain open. |
| D02-5 — target protocol | Decide whether the evidence supports a quarterly snapshot outcome or an observed first-entry endpoint; specify horizon, event, competing termination, censoring, missing/suppressed rules and weight/variance method | Signed/frozen target and evaluation protocol before outcome-driven analysis | Feasibility screens now cover repeated/current-state C landmarks, earliest eligible C per loan, and an origination-month-aligned snapshot window. The origination-aligned diagnostic finds only 65 observed 90+ outcomes across 62,359 mortgages; the earliest fully followed C anchor yields 156 among 59,703, while repeated C landmarks yield 2,174 positive snapshots / ~750 distinct loans ever positive. These are different estimands and descriptive support counts, not rates. None is frozen; population/estimand, competing risks, censoring/selection, predictor timing, and design variance remain unresolved. No target/PD/model outputs. See `NSMO_ORIGINATION_FEASIBILITY_VI.md`. |
| D02-6 — model study | Only if target support and temporal cohorts are adequate; use time-separated train/calibration/validation/test and report weighted plus unweighted diagnostics | Reproducible model card, calibration/threshold review and source-specific limitations | Not started; current origination-aligned support (65 observed 90+ statuses) is insufficient to justify a multi-predictor model. Revisit only after target/estimand and additional validated outcome data are available. |

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
