# HMDA 2019 — national One-Year dataset acquisition and audit

**Checkpoint:** 2026-10-16. The official static FFIEC/CFPB 2019 One-Year national LAR was downloaded, integrity checked, profiled and built into a private aggregate view. Raw files and aggregates remain on D:. This source is for D08 application/underwriting analysis and adds no D01 mortgage performance vintage.

Official references: [FFIEC 2019 One-Year release](https://ffiec.cfpb.gov/data-publication/one-year-national-loan-level-dataset/2019), [HMDA Data Browser vintage FAQ](https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq), [public LAR field definitions](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/).

## Vintage caveat

The release page says the 2019 One-Year product contains **more than 12 months' worth of updates**, because of its timing of creation. Treat this as a publisher-disclosed vintage exception. Its counts are not directly equivalent to a standardized 12-month freeze; mark 2019 in tables and any 2019–2020 change as caveated. The Data Browser FAQ maps current 2019 browsing to a Three-Year dataset frozen 2022-12-31; its live counts were not used to validate this One-Year archive.

## Acquisition and quality checks

| Check | Verified result |
|---|---:|
| National LAR rows | 17,563,200 |
| Columns | 99 |
| Distinct reporting LEIs | 5,565 |
| State/territory codes | 55 |
| ZIP bytes | 985,323,790 |
| ZIP SHA-256 | `4fb470ecebfcd2d78fd4c529e382a0c58d32d5865afa5e51efc80daf3e709033` |
| ZIP ETag | `"8b3accc27ee5339303f7e3e963f6d2de-118"` |
| CSV bytes | 6,837,866,739 |
| CSV SHA-256 | `f13d5b3aedba074921a7d114e0787d6220d10b2746a769eae135178b13b1673b` |
| Integrity | One expected CSV member; ZIP CRC passed; 99 unique fields |
| Update cutoff | Official page identifies data adjusted through 2022-04-05; see >12-month caveat above |

The full profile found zero wrong-year rows, invalid action codes, malformed state codes, invalid loan types, invalid LEIs or unparseable loan amounts.

| `action_taken` | Records |
|---|---:|
| 1 — originated | 9,340,568 |
| 2 — approved, not accepted | 404,421 |
| 3 — denied | 2,535,710 |
| 4 — withdrawn | 2,146,140 |
| 5 — closed for incompleteness | 718,782 |
| 6 — purchased | 2,267,336 |
| 7 — preapproval denied | 76,605 |
| 8 — preapproval approved, not accepted | 73,638 |
| **Total** | **17,563,200** |

The descriptive action-3 share is `2,535,710 / (9,340,568 + 404,421 + 2,535,710) = 20.6479%`. It measures applications with action 1, 2, or 3 in this release, not default PD, delinquency, loss or repayment performance. Public loan amount values may be modified/interval values. No forecasting, imputation, synthetic values or model fitting were performed.

## Integration and lineage

The app has a distinct 2019 panel with all eight action codes, action 1–3 denominator, configurable aggregate dimensions, JSON export, source links and an Excel workbook. Release comparison now spans 2019–2024 and marks the 2019 cutoff exception. No loan-level rows are put in the app API or public GitHub.

Private source folder: `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2019-f13d5b3aedba`.

Aggregate view: `D:\data\Codex\credit-atlas\artifacts\private\hmda-one-year-2019-view-f13d5b3aedba` (SHA-256 `b271c4db0c6dbe0e909a063bb03c07d14c6b83f5da50d0117076db8c09a99f4a`).

This improves D08 only. HMDA has no monthly loan repayment/performance target and cannot add a Freddie D01 vintage or close multi-vintage/model gates. No forecast or imputation was created.

