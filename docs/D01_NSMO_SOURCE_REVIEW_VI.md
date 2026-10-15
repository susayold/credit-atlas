# FHFA/CFPB NSMO: source review and acquisition gate

Date checked: 2026-10-15. This is a candidate source review; it does not claim that the NSMO public-use data file has been downloaded or ingested.

## Why this source matters

FHFA says the current NSMO public-use file (May 27, 2026) contains 62,359 sample mortgages originated from 2013 through 2024 and quarterly mortgage-performance information through 2025 Q3. The sample is drawn from newly originated mortgages in the NMDB/Experian frame, about 6,000 loans per quarter. It is a public-use, de-identified sample, not the Freddie Mac Single-Family Loan-Level Dataset and not a Freddie annual vintage. It could support a separate external-cohort or robustness study after the raw file, survey response process, weights, censoring, and target definition are audited.

Official source: [FHFA NSMO public-use-file page](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). FHFA lists CSV, JSON, R, SAS, Stata, and XML formats and says that downloading and using the files acknowledges the FHFA Notice of Monitoring and Terms of Service. The data payload was not requested because accessing it requires an explicit “I agree” acknowledgement to monitoring on the user's behalf. The user must authorize that acknowledgement before the payload is fetched.

## What the official codebook says is available

The May 27, 2026 codebook describes 322 survey variables and 265 supplemental variables. It names `NSMOID` as the NSMO identification number and `Analysis_Weight` as sampling weight × non-response adjustment; uniqueness and use of the public identifier still need to be checked on the file. Exact values for continuous survey answers are not released; for some survey fields, the PUF records only whether a response was provided. Question wording and response definitions changed across waves, and the codebook marks non-comparable legacy variants. Survey answers collected after origination must not be used as origination-time predictors without a documented, timestamp-valid use case.

Potentially useful mortgage and borrower fields include:

- Origination year/month; loan-size category; jumbo flag; rate spread and Freddie Mac PMMS rate at origination; term; LTV/CLTV; DTI and mortgage PTI; mortgage type; GSE; metro-LMI category; borrower count; and first-mortgage-in-credit-file flags.
- VantageScore 3.0 at origination for respondent, spouse/partner, and other borrowers, plus quarterly score snapshots. These must be assigned a strict as-of timestamp and borrower role.
- Quarterly performance status from March 2013 through September 2025. The codebook maps values to delinquency buckets (30–59 through 180+ DPD), Chapter 13, foreclosure/deed-in-lieu/voluntary surrender, several other adverse termination types, current, and non-performance states such as history ended, status pending, missing gap, pre-open, opened during quarter, or servicer-suppressed.
- Mortgage termination year/month/status; quarterly forbearance flags from March 2020 through September 2025; and quarterly mark-to-market LTV.

The performance labels are not a drop-in match for Freddie's monthly state history. A target must define how to handle quarterly observation, 30/60/90+ DPD, bankruptcy, foreclosure, other charge-off/claim outcomes, prepayment/termination, missing or suppressed observations, and horizon censoring. Do not treat “not reported” or “history ended” as current/performing. Survey non-response and the supplied weights also need a separate representativeness review.

A codebook-grounded parser helper now streams `Perf_Status_MMYY` columns into ordered quarter-end observations and preserves the original status family, including adverse, closed/history-ended, gap, pre-open, and suppressed states. Nine unit tests cover mapping and input integrity using synthetic records only; they verify implementation semantics, not actual file-level row counts, uniqueness, state frequencies, or data quality. No PD label is produced by this helper.

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

Initial work sequence after authorized download:

1. Freeze the downloaded files and official metadata, terms version, hashes, retrieval time, and selected format.
2. Reconcile file row count, loan key uniqueness, origination vintages, survey waves, weights, and all performance observation columns against the May 2026 codebook.
3. Produce a label-state transition and censoring audit before defining any PD horizon.
4. Build a point-in-time feature allowlist from origination fields only; quarantine retrospective survey answers and post-origination credit scores.
5. Reconcile the parser against the actual PUF and publish file-level evidence; then create a distinct source-specific descriptive app case and decide whether a common-feature external validation is scientifically defensible.

## Official documentation acquired locally

The official May 27, 2026 technical report and 336-page codebook were downloaded to `private evidence omitted from public release` for schema review. Their SHA-256 values are recorded in `private evidence omitted from public release`. These are documentation files only; no PUF microdata are present in that folder.

- [NSMO technical documentation](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf)
- [NSMO codebook and unweighted tabulations](https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-c-v70.pdf)
- [FHFA public-use-file notice and agreement gate](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)
- [ICPSR/DataLumos catalog record](https://www.datalumos.org/datalumos/project/219485/version/V2/view)

