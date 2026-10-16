# HMDA 2022 — national One-Year dataset acquisition and audit

**Checkpoint:** 2026-10-16. Official 2022 One-Year national LAR archive has been
downloaded, integrity-checked, profiled, and integrated as a private aggregate
view. The raw CSV, ZIP and Excel workbook remain on D:; no record-level rows are
published in the repository.

Official references: [FFIEC One-Year 2022 release page](https://ffiec.cfpb.gov/data-publication/one-year-national-loan-level-dataset/2022),
[static dataset FAQ and vintage map](https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq),
[2022 CFPB mortgage-market summary](https://www.consumerfinance.gov/data-research/hmda/summary-of-2022-data-on-mortgage-lending/),
and [HMDA Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/).

## Release choice and provenance

This is the **static One-Year National Loan-Level Dataset** for activity year
2022. FFIEC describes these files as including amendments submitted during the
12 months after the filing deadline; the static vintage is frozen **2024-05-01**.
The page's hosting package reports a later file update date (2025-10-15); that
does not change the release's stated data freeze.

The distinction matters: current Data Browser/API queries for activity year 2022
route to the **Three-Year** dataset, whose freeze is 2025-12-31. I downloaded the
published static One-Year ZIP directly, and did not use the current Three-Year
API counts as if they belonged to this One-Year vintage. Therefore this source's
action counts are profiled from the official CSV itself, with archive/CSV hashes,
ZIP CRC, schema and row-level checks recorded; there is no exact-vintage public
API aggregate reconciliation for this file.

## Acquisition and audit results

| Check | Verified result |
|---|---:|
| National LAR rows | 16,099,307 |
| Columns | 99 |
| Distinct reporting LEIs | 4,480 |
| State/territory codes | 56 |
| ZIP bytes | 890,368,467 |
| ZIP SHA-256 | `7494b6cf207396fca9c8625649d27561795a1c857fa502c2cdffd412eb216f89` |
| Extracted CSV bytes | 6,076,750,324 |
| CSV SHA-256 | `364cdfa3f46ca80659a18e79df17a7993a1ccc10481def5e3516faa095f94c80` |
| One-Year freeze | 2024-05-01 |

The ZIP has one expected member, `2022_public_lar_one_year_csv.csv`; the member
length matches the extracted file, and the complete CRC test passed. The 99
source headers are unique and satisfy the required LAR field contract. The row
profile found zero wrong-year, invalid action, invalid state, invalid loan-type,
invalid LEI, or invalid loan-amount records. All eight action codes occur and
sum to the row count.

| `action_taken` | Rows |
|---|---:|
| 1 — originated | 8,406,350 |
| 2 — approved, not accepted | 417,122 |
| 3 — denied | 2,500,211 |
| 4 — withdrawn | 2,224,475 |
| 5 — file closed for incompleteness | 791,864 |
| 6 — purchased loan | 1,559,011 |
| 7 — preapproval request denied | 71,850 |
| 8 — preapproval approved, not accepted | 128,424 |
| **Total** | **16,099,307** |

The descriptive decision denominator is actions 1+2+3:

`2,500,211 / (8,406,350 + 417,122 + 2,500,211) = 22.0795%`.

That is an application disposition share, not probability of default, delinquency,
repayment, loss, or recovery. The CFPB's 2022 public summary reports rounded
figures of about 16.1 million records and 8.4 million originations. Those rounded
figures are a broad plausibility check only; the report's release date predates
this One-Year freeze, so it is not an exact-vintage reconciliation.

## Available One-Year release comparison

The app presents the audited 2020–2024 static One-Year releases with the same
action definitions and denominator. A prior review missed the 2021 line in the
FFIEC FAQ; it has now been downloaded and separately audited. The observed
aggregates are:

| Activity year | Freeze date | LAR rows | Actions 1–3 denominator | Denied action 3 | Descriptive denied share |
|---|---|---:|---:|---:|---:|
| 2020 | 2022-04-30 | 25,666,745 | 18,134,264 | 2,880,243 | 15.8829% |
| 2021 | 2023-05-01 | 26,227,364 | 18,620,312 | 2,922,414 | 15.6948% |
| 2022 | 2024-05-01 | 16,099,307 | 11,323,683 | 2,500,211 | 22.0795% |
| 2023 | 2025-05-19 | 11,564,178 | 8,058,391 | 2,037,094 | 25.2792% |
| 2024 | 2026-06-02 | 12,259,199 | 8,661,779 | 2,103,462 | 24.2844% |

The denied share falls 0.1881 percentage points from 2020 to 2021, rises 6.3847
points from 2021 to 2022, rises 3.1997 points from 2022 to 2023, then falls
0.9948 points from 2023 to 2024. These are
descriptive release-to-release changes; changes in application mix, market
conditions, reporting/resubmissions and freeze timing may contribute. They do
not establish cause, applicant-level transitions, loan performance, or default
risk.

## App and Excel

The HMDA workspace has a separate 2022 One-Year view with the action table,
breakdowns by state, county, LEI, product and applicant attributes, action-3-only
denial reasons, JSON export, source limits and private Excel download. The 2023
panel compares the release years, showing adjacent-release deltas, including
2021 after its source archive was verified.
The eight-sheet Excel workbook includes Overview, Actions, Geography, Institution
LEI, Credit & product, Field dictionary, Source audit, and 2022 vs 2024. It records
all 99 actual source fields and carries the warning that the current 2022 Data
Browser aggregate endpoint is a Three-Year release. The 16.1-million-row CSV is
not embedded in the workbook; it exceeds Excel's worksheet row limit.

Private artifacts:

- Raw ZIP, extracted CSV and acquisition receipt: `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2022-364cdfa3f46c`
- Excel workbook: `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2022-364cdfa3f46c\CreditAtlas-HMDA-One-Year-2022-Audit.xlsx`
- Aggregate view: `D:\data\Codex\credit-atlas\artifacts\private\hmda-one-year-2022-view-364cdfa3f46c`

No row-level source data is copied to GitHub. No data was forecast, imputed or
synthetically generated; no model was fitted. HMDA supports application and
underwriting analysis for D08, not D01 monthly mortgage-performance vintage
qualification, and does not close Freddie R2/R3 gates.
