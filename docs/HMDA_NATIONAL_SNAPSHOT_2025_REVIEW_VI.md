# HMDA National Snapshot 2025 — data-first review

Checkpoint: 2026-10-16. The three official FFIEC snapshot packages are stored
privately under `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-snapshot-2025-9a5e89600e3c`.
Raw ZIP/CSV files, tax identifiers, and the private acquisition receipt are not
part of this public repository. No model, forecast, imputation, or application
integration has been performed.

## What was acquired and verified

The static snapshot is the 2025 HMDA national data frozen June 2, 2026. FFIEC's
June 23, 2026 release says the snapshot covers 4,782 reporting institutions.
The publisher notes public privacy modifications; snapshot data are a dated
release rather than the later-updated dynamic file. See the official
[announcement](https://www.ffiec.gov/news/press-releases/2026/an-06-23) and
[HMDA publication documentation](https://ffiec.cfpb.gov/data-publication/).

| Dataset | Rows | Fields | Checks and interpretation |
|---|---:|---:|---|
| Loan/Application Register (LAR) | 13,543,606 | 99 | Activity year is 2025 on every row; 4,782 distinct LEIs; action, state, loan-type, and LEI format checks pass; ZIP CRC passes. |
| Transmittal Sheet (TS) | 4,782 | 10 | 4,782 unique LEIs; all activity year 2025 and calendar quarter 4; reported LAR count sums exactly to 13,543,606. The public file contains institution/tax identifiers; it stays private and is not exported here. |
| MSA/MD reference | 418 | 3 | 418 unique MSA/MD codes, no blank code; ZIP CRC passes. Used as a geographic name lookup, not a performance table. |

Official source ZIPs are listed by the HMDA frontend as the 2025 LAR, TS, and
MSA/MD snapshot files and served on FFIEC's public file host. The official
[file-serving documentation](https://ffiec.cfpb.gov/documentation/api/file-serving/)
identifies that host as its public S3 file service. Acquisition checked HTTPS,
an exact URL allowlist, content type, advertised size, byte count, safe archive
members, ZIP CRC, and SHA-256. The LAR schema was compared with the official
[public LAR schema](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/public-lar-schema).
The field definitions and category meanings come from the official
[LAR data dictionary](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/).
One upstream documentation mismatch is preserved explicitly: the snapshot and
schema call the applicant age field `applicant_age`, while the field dictionary
heading reads `ageapplicant`. The Excel dictionary maps the official definition
to the actual snapshot header and flags the alias for review; it does not rename
or alter the source column.

The LAR's action totals are:

| HMDA action | Records | Meaning |
|---|---:|---|
| 1 | 6,827,891 | Loan originated |
| 2 | 417,961 | Approved, not accepted |
| 3 | 2,115,090 | Application denied |
| 4 | 1,710,723 | Withdrawn by applicant |
| 5 | 695,006 | File closed for incompleteness |
| 6 | 1,578,064 | Purchased loan |
| 7 | 50,499 | Preapproval request denied |
| 8 | 148,372 | Preapproval approved, not accepted |

These sum to 13,543,606. For a descriptive decision-rate calculation, the
denominator is actions 1+2+3 = 9,360,942; the numerator is action 3 =
2,115,090; the resulting denied share is 22.5948%. This is a snapshot-level
share of decided applications under this explicit denominator. It is not a
default rate, delinquency rate, probability of default, or estimate of an
individual borrower's credit risk. Purchased loans, withdrawals, incomplete
files, and preapproval records are not in that denominator.

The source audit uses DuckDB over the entire LAR, keeping every source field as
text during ingestion to preserve category and sentinel values. It validates
the 99-field header, activity year, action-code domain 1–8, state-code shape,
loan-type domain 1–4, and LEI length. It then calculates counts by action,
state, and loan type. The denial share is numerator divided by the stated
actions 1–3 denominator; it is not a fitted/statistical model and has no
missing-value imputation. SHA-256 and the private receipt are the reproducible
file-level evidence.

## Credit Atlas use and limits

This adds nationwide **origination/application and underwriting-decision**
coverage to D08. It enables descriptive comparisons by product, lender,
geography, reported DTI/income/credit-score-model type, denial reason, and
demographic categories subject to HMDA privacy and reporting rules. The 2025
snapshot may later differ from a one-year final dataset because late filings or
resubmissions can change the dynamic data.

HMDA does not provide a monthly loan-performance panel or repayment/default
outcome labels. Public records are privacy-modified and do not provide a
reliable borrower/loan key for joining to Freddie, Fannie, Ginnie, or other
servicing performance sources. Credit score fields describe the score model
type, not the numeric score. Therefore this source cannot independently train
or validate a PD model. Keep it as an application/decision case and connect it
to an outcome source only when a documented, authorized, stable join exists.

This acquisition does not increase the master completion ledger: the national
data are not yet integrated into the app or accepted against a D08 product
gate. The plan remains **26/50 complete (52%)**; 42/50 have at least some
implementation or conditional coverage (84%), which is not the completion
rate. It does not close D01's missing Freddie vintages or model-fit gates.

## Workbook and next data-first steps

The private Excel review workbook is complete at
`data/private/hmda/hmda-national-snapshot-2025-9a5e89600e3c/CreditAtlas-HMDA-National-2025-Audit.xlsx`.
It contains Overview, Actions, State counts, Loan types, Field dictionary,
MSA-MD reference, and Source audit sheets. The field dictionary has all 99
snapshot fields with official descriptions, types, lengths, and permitted
categories. The workbook has only aggregates and reference/codebook data; it
does not contain loan-level records, Transmittal Sheet institution rows, or tax
identifiers. Its formulas recalculate, the exported workbook reopens with all
seven sheets/tables, and the formula-error scan is clear. The source age-field
name mismatch is called out in the codebook.

1. Build a separate nationwide D08 view behind the existing HMDA case model;
   preserve the current Maryland case as its own scope. Add filter-aligned
   numerators/denominators, product/lender/geography breakdowns, privacy and
   missing/sentinel handling, and scoped Excel export. Validate aggregates
   against the acquisition receipt before release.
2. Keep loan-performance acquisition separate. Freddie annual samples still
   require an authorized Clarity session; Ginnie download still requires the
   signed-in session file. Do not synthesize repayment outcomes from HMDA.
3. Do not forecast any missing field. If a later decision requires a projected
   quantity, first gather source research, document the selected method and
   alternatives, assumptions, training/evaluation data and uncertainty, then
   validate out of time and report evidence before using the estimate.

## Acquisition utility

`scripts/acquire_hmda_national_snapshot.py` downloads from an exact official
URL allowlist, stores files only under the D: private data root, verifies
archives and profiles LAR aggregates without printing application rows. It
supports `--resume-from` to continue after a partial acquisition without
overwriting or redownloading the already verified LAR.
