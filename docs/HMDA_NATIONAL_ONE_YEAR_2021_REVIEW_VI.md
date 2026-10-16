# HMDA 2021 — national One-Year dataset acquisition and audit

**Checkpoint:** 2026-10-16. The official static 2021 One-Year national LAR was
downloaded, integrity-checked, fully profiled, and integrated into a private
aggregate view, Excel audit workbook, and app panel. Raw ZIP/CSV and derived
aggregates remain on D:; no application-level records are published to GitHub.

Official references: [FFIEC One-Year 2021 release page](https://ffiec.cfpb.gov/data-publication/one-year-national-loan-level-dataset/2021),
[static dataset FAQ and release-vintage map](https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq),
[HMDA public LAR field definitions](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/),
and [Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/).

## Correction to prior research

An earlier HMDA review said the FFIEC FAQ did not list a 2021 One-Year release.
That conclusion was incorrect. Re-reading the current official FAQ's release
map shows the 2021 One-Year dataset, frozen **2023-05-01**. The FAQ separately
lists the 2021 Data Browser source as a Three-Year release frozen **2024-12-31**.
The static One-Year ZIP was therefore acquired directly; current Data Browser
counts are not treated as exact-vintage checks for this archive.

## Acquisition and audit

| Check | Verified result |
|---|---:|
| National LAR rows | 26,227,364 |
| Columns | 99 |
| Distinct reporting LEIs | 4,368 |
| State/territory codes | 56 |
| ZIP bytes | 1,518,888,317 |
| ZIP SHA-256 | `9ad543cc190f756fc42fbb202bdc06bcb1b33b28d996a7a2a4a54535ebd6d397` |
| ZIP ETag | `"ac05d9671207bee3a15565c0c9c0a889-182"` |
| CSV bytes | 10,212,571,276 |
| CSV SHA-256 | `0463a785690a47ec3406a96b4f6900fcc4e7b0d6b34877bd0397a3853a71dae6` |
| ZIP integrity | Single expected LAR member; full CRC test passed |
| One-Year freeze | 2023-05-01 |

All 99 headers are unique and satisfy the required public-LAR contract. Checks
found zero wrong-year rows, invalid action codes, invalid state-code lengths,
invalid loan types, invalid LEIs, or invalid loan amounts. All eight action
codes occur and reconcile to the total source rows:

| `action_taken` | Rows |
|---|---:|
| 1 — originated | 15,062,966 |
| 2 — approved, not accepted | 634,932 |
| 3 — denied | 2,922,414 |
| 4 — withdrawn | 3,313,356 |
| 5 — file closed for incompleteness | 1,452,022 |
| 6 — purchased loan | 2,691,964 |
| 7 — preapproval request denied | 53,506 |
| 8 — preapproval approved, not accepted | 96,204 |
| **Total** | **26,227,364** |

The descriptive decision denominator is actions 1+2+3:

`2,922,414 / (15,062,966 + 634,932 + 2,922,414) = 15.6948%`.

This is an application disposition share, not probability of default,
delinquency, repayment, loss, or recovery. HMDA provides no monthly loan
performance labels and this release is not used to train D01.

## Comparison with adjacent One-Year releases

| Activity year | Freeze date | LAR rows | Actions 1–3 denominator | Denied action 3 | Descriptive denied share |
|---|---|---:|---:|---:|---:|
| 2020 | 2022-04-30 | 25,666,745 | 18,134,264 | 2,880,243 | 15.8829% |
| 2021 | 2023-05-01 | 26,227,364 | 18,620,312 | 2,922,414 | 15.6948% |
| 2022 | 2024-05-01 | 16,099,307 | 11,323,683 | 2,500,211 | 22.0795% |
| 2023 | 2025-05-19 | 11,564,178 | 8,058,391 | 2,037,094 | 25.2792% |
| 2024 | 2026-06-02 | 12,259,199 | 8,661,779 | 2,103,462 | 24.2844% |

The 2020-to-2021 descriptive change is -0.1881 percentage points; the 2021-to-
2022 change is +6.3847 points. These are changes in application disposition
shares across frozen releases. Application composition, market conditions,
reporting/resubmissions, and release timing may contribute. They do not
establish cause or booked-loan performance.

## App and Excel

The HMDA workspace includes a separate 2021 One-Year panel with all eight
actions, the shared 1+2+3 denominator, aggregate breakdowns, action-3 denial
reasons, private JSON, official source links, and an eight-sheet Excel workbook.
The workbook contains filterable aggregate tables and the 99-field source
dictionary, not the 26.2-million-row CSV, which exceeds Excel's worksheet row
limit. The HMDA One-Year comparison now includes every year 2020–2024.

Private artifacts:

- Raw ZIP, CSV, and acquisition receipt:
  `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2021-0463a785690a`
- Excel workbook:
  `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2021-0463a785690a\CreditAtlas-HMDA-One-Year-2021-Audit.xlsx`
- Aggregate view:
  `D:\data\Codex\credit-atlas\artifacts\private\hmda-one-year-2021-view-0463a785690a`

No row-level source data is copied to GitHub. No forecast, imputation, synthetic
value, or model fit was performed. HMDA supports D08 application/underwriting
analysis; it does not add a Freddie D01 performance vintage or close D01 R2/R3.
