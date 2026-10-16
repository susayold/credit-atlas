# HMDA 2024 — national One-Year dataset acquisition and audit

**Checkpoint:** 2026-10-16. **Status:** downloaded and locally verified; raw data
and audit receipt remain private on D:. No rows are published to GitHub.

Official references: [2024 data publication page](https://ffiec.cfpb.gov/data-publication/2024),
[HMDA Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/),
and [2024 nationwide Data Browser](https://ffiec.cfpb.gov/data-browser/data/2024?category=nationwide).

## Source and release definition

The source is the official FFIEC/CFPB HMDA Data Browser nationwide CSV endpoint
for activity year 2024. The official 2024 data-publication page identifies the
One-Year National Dataset and says the release includes the post-deadline
resubmission window; the release was frozen on 2026-06-02. This is a distinct
release design from the 2025 Snapshot National Loan-Level Dataset. The official
Data Browser API documentation describes the public nationwide aggregation and
filtered CSV endpoints. URLs and HTTP response details are preserved in the
private acquisition receipt.

## Acquisition evidence

| Check | Result |
|---|---:|
| National LAR rows | 12,259,199 |
| Columns | 99 |
| Distinct reporting LEIs | 4,926 |
| State/territory codes represented | 55 |
| CSV bytes | 4,636,615,274 |
| CSV SHA-256 | `9f38ccda3b3eb88a22d7eb3c1745a0d418ae533486bd483d3bb7e5d3f6f8efe4` |
| Freeze date | 2026-06-02 |

The downloaded action counts match the official 2024 nationwide aggregation
API exactly. Their sum is 12,259,199. The CSV profile found zero wrong-year,
invalid action, invalid state-code, invalid loan-type, invalid LEI, or invalid
loan-amount rows. A separate historical failed-attempt receipt is retained next
to the successful receipt for auditability.

| `action_taken` | Rows |
|---|---:|
| 1 — originated | 6,197,085 |
| 2 — approved, not accepted | 361,232 |
| 3 — denied | 2,103,462 |
| 4 — withdrawn | 1,538,273 |
| 5 — file closed for incompleteness | 581,940 |
| 6 — purchased loan | 1,276,504 |
| 7 — preapproval request approved but not accepted | 47,312 |
| 8 — preapproval request denied | 153,391 |
| **Total** | **12,259,199** |

For a narrowly defined descriptive application-denial share, the numerator is
action 3 and the denominator is actions 1+2+3:

`2,103,462 / (6,197,085 + 361,232 + 2,103,462) = 24.2844%`.

This is an application decision statistic, not probability of default (PD),
delinquency, loss, or repayment performance. Actions 4–8 are excluded from that
decision denominator by definition.

## Appropriate use and limitations

This source supports descriptive research on mortgage applications, lender
decisions, loan purpose/type, geography, public borrower attributes, and
application-level underwriting outcomes. It can support D08 HMDA analysis and
benchmarking of application/denial mix. It does not contain monthly account
performance, defaults, charge-offs, recoveries, or a stable public key for
linking these records to Freddie, Fannie, or Ginnie performance panels. It must
not be represented as a mortgage PD/LGD/ECL training set.

No missing variable was forecast, imputed, or synthesized. The reported values
are observed release counts. No model was fitted. The source stays separate
from D01's Freddie lifecycle case and does not close its R2/R3 gates or increase
its 26/50 completion count.

## Local artifacts

Private D: folder:
`D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2024-002bab12cd71`

- `2024_one_year_national_lar.csv` — complete official CSV, private only.
- `acquisition-complete.json` — source URL, redirect evidence, byte count/hash,
  schema/profile, action reconciliation, and explicit no-forecast/no-label flags.
- `official-api-aggregation.json` — raw official API aggregation response.
- `acquisition-failed.json` — retained record of an earlier failed validation
  attempt before the recovered successful run.

The public repository contains only the acquisition code and this methodology /
result summary, never the private CSV or row-level records.

## App integration and review workbook

The private workbench now serves this release through a source-specific
aggregate view; it does not alter the verified 2025 Snapshot receipt. The
browser acceptance receipt records **PASS, 8 checks, zero browser errors**,
including the 2024 panel, all eight action codes, state profile, primary
denial-reason breakdown, private JSON export, and byte-identical Excel download.
The UI labels the release as One-Year 2024 and states the limitations and
denominator contract.

The private Excel workbook is:

`D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2024-002bab12cd71\CreditAtlas-HMDA-One-Year-2024-Audit.xlsx`

It has seven filterable sheets: Overview, Actions, Geography, Institution LEI,
Credit & product, Field dictionary, and Source audit. It contains audited
aggregates and metadata, not application-level rows. The full CSV exceeds
Excel's worksheet row limit, so the workbook links the audit context to the
private source folder instead of pretending Excel contains the raw file.

## Next data-first steps

The 2022 and 2023 One-Year National releases have now also been acquired and
audited, and the app compares 2022–2024 with a common action denominator. See
[`HMDA_NATIONAL_ONE_YEAR_2022_REVIEW_VI.md`](HMDA_NATIONAL_ONE_YEAR_2022_REVIEW_VI.md)
and [`HMDA_NATIONAL_ONE_YEAR_2023_REVIEW_VI.md`](HMDA_NATIONAL_ONE_YEAR_2023_REVIEW_VI.md).
Continue seeking authorized Freddie Clarity performance files and the
user-provided Ginnie signed-in session artifact. Those remain the gating data
for D01 R2/R3; public HMDA cannot substitute for them.

