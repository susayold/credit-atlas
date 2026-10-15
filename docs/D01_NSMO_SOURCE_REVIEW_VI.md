# FHFA/CFPB NSMO: source review and acquisition gate

Date checked: 2026-10-15. FHFA's May 27, 2026 NSMO v7.0 PUF has been downloaded after the user explicitly authorized the two-step monitoring/terms acknowledgement. The file has passed structural and code-domain checks; no credit-risk target or model has been created.

## Why this source matters

FHFA says the current NSMO public-use file (May 27, 2026) contains 62,359 sample mortgages originated from 2013 through 2024 and quarterly mortgage-performance information through 2025 Q3. The sample is drawn from newly originated mortgages in the NMDB/Experian frame, about 6,000 loans per quarter. It is a public-use, de-identified sample, not the Freddie Mac Single-Family Loan-Level Dataset and not a Freddie annual vintage. It could support a separate external-cohort or robustness study after the raw file, survey response process, weights, censoring, and target definition are audited.

Official source: [FHFA NSMO public-use-file page](https://www.fhfa.gov/data/nsmo) and its [Notice of Monitoring/Terms gate](https://www.fhfa.gov/data/nsmo/puf). After the user authorized it, the official gate was completed and the CSV ZIP was fetched from FHFA. The raw ZIP/CSV and detailed receipts stay in a private local store outside this public repository. No credentials or cookies were saved.

The agreement was reviewed before completing the gate. It prohibits processing intended to identify individuals, requires compliance with privacy laws, restricts use of FHFA/NMDB marks, requires a caveat that FHFA does not attest to post-download analyses, prohibits presenting modified data as official government material, and includes user warranty/indemnification language. No row-level PUF or IDs are included in public GitHub. If any future output cites this source, include the FHFA-required analysis disclaimer; do not imply FHFA endorsement.

## What the official codebook says is available

The May 27, 2026 codebook describes 322 survey variables and 265 supplemental variables, matching the 587 physical CSV columns. It names `nsmoid` as the sequential sample-mortgage identifier and `analysis_weight` as sampling weight × non-response adjustment. The identifier is unique in this file. Exact values for continuous survey answers are not released; for some survey fields, the PUF records only whether a response was provided. Question wording and response definitions changed across waves, and the codebook marks non-comparable legacy variants. A field-by-field reconciliation of all 587 headers to the codebook remains open. Survey answers collected after origination must not be used as origination-time predictors without a documented, timestamp-valid use case.

The v7.0 CSV structural audit found **62,359 rows**, **587 columns**, **62,359 distinct non-empty `nsmoid` values**, no duplicate IDs, no blank IDs, no malformed row widths, and no duplicate column names (case-insensitive). `open_year` covers 2013–2024; all 12 months are represented. `survey_wave` values and weighted sample composition still need their own codebook-aligned interpretation.

`analysis_weight` is present for every row, numeric and finite, and all values are positive. Its observed range is 395.24–7,114.61; median 1,116.55; total 85,472,423.11. This confirms the raw field profile only; it does not establish that a particular weighted estimator, variance formula, or respondent-level inference is appropriate.

Potentially useful mortgage and borrower fields include:

- Origination year/month; loan-size category; jumbo flag; rate spread and Freddie Mac PMMS rate at origination; term; LTV/CLTV; DTI and mortgage PTI; mortgage type; GSE; metro-LMI category; borrower count; and first-mortgage-in-credit-file flags.
- VantageScore 3.0 at origination for respondent, spouse/partner, and other borrowers, plus quarterly score snapshots. These must be assigned a strict as-of timestamp and borrower role.
- Quarterly performance status from March 2013 through September 2025. The codebook maps values to delinquency buckets (30–59 through 180+ DPD), Chapter 13, foreclosure/deed-in-lieu/voluntary surrender, several other adverse termination types, current, and non-performance states such as history ended, status pending, missing gap, pre-open, opened during quarter, or servicer-suppressed.
- Mortgage termination year/month/status; quarterly forbearance flags from March 2020 through September 2025; and quarterly mark-to-market LTV.

The performance labels are not a drop-in match for Freddie's monthly state history. A target must define how to handle quarterly observation, 30/60/90+ DPD, bankruptcy, foreclosure, other charge-off/claim outcomes, prepayment/termination, missing or suppressed observations, and horizon censoring. Do not treat “not reported” or “history ended” as current/performing. Survey non-response and the supplied weights also need a separate representativeness review.

A codebook-grounded parser helper now streams case-insensitive `perf_status_MMYY` columns into ordered quarter-end observations and preserves the original status family, including adverse, history-ended, gap, pre-open, and suppressed states. Against the actual PUF it found **51 consecutive quarter-end columns**, 2013-03-31 through 2025-09-30, for **3,180,309 status cells**. Every status code is in the reviewed domain; aggregate counts are in the private audit receipt. The 11 parser tests include lowercase publisher headers and reject case-insensitive duplicate names. Two additional auditor tests verify that aggregate reports exclude IDs and fail closed on unknown status codes. This validates parser/input integrity, not an outcome definition. No PD label is produced.

The unweighted status totals across all loan-quarter cells are: current (`C`) 978,598; 30–59 DPD (`1`) 4,859; 60–89 (`2`) 1,483; 90–119 (`3`) 717; 120–149 (`4`) 371; 150–179 (`5`) 252; 180+ (`6`) 1,189; Chapter 13 (`7`) 424; foreclosure/distressed disposition (`8`) 315; other adverse/charge-off (`9`) 307; history ended (`A`) 776,776; potentially closed (`B`) 0; opened-not-yet-reported (`K`) 4,396; archive gap (`M`) 1,246; pre-open (`P`) 1,343,384; opened during quarter (`Q`) 62,243; servicer-suppressed (`S`) 3,749; blank/unknown 0. These are cell counts, not unique-loan counts, event incidence, or PD. The large `P` and `A` categories mean a simple ever/never flag across the wide panel would be particularly misleading.

## Recommended placement in Credit Atlas

Keep NSMO as a distinct source and case, for example `D02_NSMO`, with its own manifest, mapping, target version, sample/weight treatment, and model splits. Do not concatenate it with the Freddie panel or label it as another Freddie vintage. First use it for a source-specific descriptive/target-feasibility module; only then consider an external temporal validation experiment using a frozen common-feature contract. Any cross-source comparison should report source-specific populations and calibration, not pool scores or claim a shared population.

## Compatibility with the current Freddie early-entry study

| Freddie contract concept | NSMO candidate | Compatibility decision |
|---|---|---|
| Origination date/vintage | `Open_Year`, `Open_Month` | Comparable as calendar cohort, but NSMO sample/weight frame differs |
| Original UPB | `Loan_Amount_Cat` | Not equivalent: nine broad loan-size bands, no exact UPB |
| Classic FICO | `Score_Orig_R` (VantageScore 3.0; respondent) | Not directly comparable: score model differs; respondent may not be the only borrower |
| Original DTI | `DTI` | Conceptually similar but top/bottom coded; needs range and missing audit |
| Original LTV/CLTV | `LTV`, `CLTV` | Conceptually similar but top-coded; must compare distributions and codebook units |
| Original term | `Term` | Whole-year category/floor representation rather than verified exact month count |
| Origination purpose, occupancy, property type, units, Relief/HARP | No confirmed one-to-one field in the reviewed supplemental mapping | Exclude from common feature contract unless a specific codebook field is validated |
| Monthly event-before-prepayment label: first 90+ DPD (`03`–`99`) inside 12 months | Quarterly `Perf_Status_MMYY`; codes 3–6 indicate 90+ DPD at an observed quarter-end | Not the same event-time resolution or target. Quarterly snapshots can miss intervening events and do not establish exact first entry; write a separate quarterly horizon target with explicit competing events and censoring |

Therefore NSMO may support a separate quarterly delinquency/default study, or a carefully scoped source-level robustness analysis. It cannot currently serve as final-test vintage for the existing monthly Freddie PD12 model. A shared-feature, shared-target external validation remains an open research question, not an assumed capability.

Next work sequence for the separate NSMO case:

1. Reconcile every physical column to the codebook, including the survey-wave range, non-comparable survey variants, quarterly scores, mortgage termination, forbearance and mark-to-market LTV.
2. Produce quarter-by-quarter status counts and transitions; distinguish states `A`, `B`, `K`, `M`, `P`, `Q`, and `S` from observed delinquency/current and determine codebook-consistent rules for when a loan enters/leaves the observation risk set.
3. Freeze a target protocol separately from Freddie. Define the quarterly horizon, event definition, competing termination outcomes, eligibility, censoring, missing/suppressed states and weighting/variance treatment before any PD estimation.
4. Build a point-in-time feature allowlist; quarantine retrospective survey answers, post-origination scores and other future information.
5. A first separate D02/NSMO descriptive page/API now serves aggregate-only evidence and the required FHFA caveat; expand/accept the metric views only after the codebook and observation-state rules are reconciled. Then decide whether a common-feature external comparison is scientifically defensible. Never merge IDs or rows with D01.

## Official documentation acquired locally

The official May 27, 2026 technical report and 336-page codebook were reviewed locally; source-document receipts and the private PUF audit receipt remain outside this repository.

- [NSMO technical documentation](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf)
- [NSMO codebook and unweighted tabulations](https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-c-v70.pdf)
- [FHFA public-use-file notice and agreement gate](https://www.fhfa.gov/data/nsmo/puf)
- [ICPSR/DataLumos catalog record](https://www.datalumos.org/datalumos/project/219485/version/V2/view)

## Required FHFA analysis disclaimer

> The opinions and analyses contained herein are solely of the users/authors of any data analyses or papers, and the FHFA cannot and does not attest to nor vouch for the quality, accuracy, or timeliness of the data, or analyses derived from these data after the data has been retrieved from FHFA.gov.
