# HMDA 2020 — national One-Year dataset acquisition and audit

**Checkpoint:** 2026-10-16. Official static 2020 One-Year national LAR archive
downloaded, integrity-checked, fully profiled, and integrated into a private
aggregate view, Excel audit workbook, and app panel. Raw ZIP/CSV remain on D:;
no application-level records are published to GitHub.

Official references: [FFIEC One-Year 2020 release page](https://ffiec.cfpb.gov/data-publication/one-year-national-loan-level-dataset/2020),
[static dataset FAQ and release-vintage map](https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq),
[HMDA public LAR field definitions](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/),
and [Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/).

## Release vintage and source limits

This is the **static One-Year National Loan-Level Dataset** for activity year
2020, frozen **2022-04-30**. It incorporates changes filed in the 12 months
after the filing deadline. The current Data Browser maps activity year 2020 to
the Three-Year dataset, frozen 2023-12-31. Therefore the One-Year action counts
below were derived from the archived One-Year CSV and checked against its own
archive/CSV hashes, ZIP CRC, schema, and row-quality profile; no Three-Year API
count is presented as an exact-vintage reconciliation.

**Correction, 2026-10-16:** an earlier version of this review incorrectly said
2021 had no One-Year release. Rechecking the current FFIEC FAQ found the 2021
One-Year vintage and its 2023-05-01 freeze date. The official 2021 archive has
since been acquired and audited; see
[`HMDA_NATIONAL_ONE_YEAR_2021_REVIEW_VI.md`](HMDA_NATIONAL_ONE_YEAR_2021_REVIEW_VI.md).

## Acquisition and audit

| Check | Verified result |
|---|---:|
| National LAR rows | 25,666,745 |
| Columns | 99 |
| Distinct reporting LEIs | 4,512 |
| State/territory codes | 57 |
| ZIP bytes | 1,465,455,781 |
| ZIP SHA-256 | `25acc0cdf86e1ce1d5a44ab7b7ab8d46307daabefe77b1acc74c09c9c61903b7` |
| CSV bytes | 10,022,564,079 |
| CSV SHA-256 | `b59581b05544af2203bf3295fe8cbf68274e1c4b3e26473a54375d8f199acdcd` |
| ZIP integrity | Single expected LAR member; full CRC test passed |
| One-Year freeze | 2022-04-30 |

All 99 headers are unique and satisfy the required public-LAR contract. Checks
found zero wrong-year rows, invalid actions, invalid state codes, invalid loan
types, invalid LEIs, or invalid loan amounts. All eight action codes occur and
sum to the source record count.

| `action_taken` | Rows |
|---|---:|
| 1 — originated | 14,629,575 |
| 2 — approved, not accepted | 624,446 |
| 3 — denied | 2,880,243 |
| 4 — withdrawn | 3,403,483 |
| 5 — file closed for incompleteness | 1,243,387 |
| 6 — purchased loan | 2,758,274 |
| 7 — preapproval request denied | 57,569 |
| 8 — preapproval approved, not accepted | 69,768 |
| **Total** | **25,666,745** |

The descriptive decision denominator is actions 1+2+3:

`2,880,243 / (14,629,575 + 624,446 + 2,880,243) = 15.8829%`.

This is an application disposition share, not probability of default,
delinquency, repayment, loss, or recovery. HMDA provides no monthly loan
performance labels and this release is not used to train D01.

## One-Year release comparison

| Activity year | Freeze date | LAR rows | Actions 1–3 denominator | Denied action 3 | Descriptive denied share |
|---|---|---:|---:|---:|---:|
| 2020 | 2022-04-30 | 25,666,745 | 18,134,264 | 2,880,243 | 15.8829% |
| 2021 | 2023-05-01 | 26,227,364 | 18,620,312 | 2,922,414 | 15.6948% |
| 2022 | 2024-05-01 | 16,099,307 | 11,323,683 | 2,500,211 | 22.0795% |
| 2023 | 2025-05-19 | 11,564,178 | 8,058,391 | 2,037,094 | 25.2792% |
| 2024 | 2026-06-02 | 12,259,199 | 8,661,779 | 2,103,462 | 24.2844% |

The descriptive share falls 0.1881 percentage points from 2020 to 2021, rises
6.3847 points from 2021 to 2022, rises 3.1997 points from 2022 to 2023, then
falls 0.9948 points from 2023 to 2024. The 2020-to-2024 difference is +8.4015
points. These
are release-to-release changes in reported application mix; market conditions,
application composition, reporting/resubmissions and release timing may
contribute. They do not establish cause or a change in booked-loan performance.

## App and Excel

The HMDA workspace now includes a distinct 2020 One-Year panel with all eight
actions, the shared 1+2+3 denominator, aggregate breakdowns, action-3 denial
reason view, private JSON, official source links, and an eight-sheet Excel
audit workbook. The workbook contains aggregate tables and the 99-field source
dictionary, not the 25.7-million-row CSV, which exceeds Excel's worksheet row
limit. The comparison section includes all five audited releases, 2020–2024.

Private artifacts:

- Raw ZIP, CSV, and acquisition receipt:
  `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2020-b59581b05544`
- Excel workbook:
  `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2020-b59581b05544\CreditAtlas-HMDA-One-Year-2020-Audit.xlsx`
- Aggregate view:
  `D:\data\Codex\credit-atlas\artifacts\private\hmda-one-year-2020-view-b59581b05544`

No row-level source data is copied to GitHub. No forecast, imputation, synthetic
value, or model fit was performed. HMDA supports D08 application/underwriting
analysis; it does not add a Freddie D01 performance vintage or close D01 R2/R3.
