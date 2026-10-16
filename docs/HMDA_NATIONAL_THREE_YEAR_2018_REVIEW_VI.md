# HMDA 2018 Three-Year national LAR — acquisition and quality review

**Checkpoint:** 16/10/2026. This is public loan/application decision data for
D08; it is not mortgage repayment performance and does not add a D01 vintage.
The 2018 vintage is the official Three-Year dataset frozen **2021-12-31**. Keep
it separate from HMDA One-Year 2019–2024 and Dynamic/Snapshot 2025.

Official references: [2018 Three-Year HMDA dataset](https://ffiec.cfpb.gov/data-publication/three-year-national-loan-level-dataset/2018),
[HMDA Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/),
[2018 Data Browser vintage FAQ](https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq),
[public LAR field values](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields).
The 2018 static page currently renders the national file links as “File not
found”; the official Data Browser API still serves 2018 queries from the
Three-Year freeze. Acquisition therefore records the API route and exact query,
not a fabricated direct static-file URL.

## Acquired file and integrity

| Item | Verified value |
|---|---:|
| Dataset vintage | 2018 Three-Year National Loan-Level Dataset |
| Freeze | 2021-12-31 |
| API query | `years=2018&actions_taken=1,2,3,4,5,6,7,8` |
| CSV fields | 99 |
| Download bytes | 5,879,026,670 |
| SHA-256 | `6b6678ce3c3dc0c640b867b77a10cce3e8ec05e91965e77c44ef0bce4c28c924` |
| File location | `D:\data\Codex\credit-atlas\data\private\hmda\hmda-browser-three-year-2018\hmda-2018-three-year-national.csv` |
| Acquisition receipt | `hmda-2018-browser-acq-ca2faffa1029` |
| Audit receipt | `hmda-2018-browser-audit-f2f5185955d7` |

## Reconciliation and quarantine

The official aggregation API returns **15,138,510** records across action codes
1–8. The streamed CSV contains **15,140,471** rows. All eight documented action
counts reconcile exactly to the official aggregation response:

| `action_taken` | Official count |
|---|---:|
| 1 — originated | 7,732,289 |
| 2 — approved, not accepted | 338,822 |
| 3 — denied | 2,552,640 |
| 4 — withdrawn | 1,771,582 |
| 5 — closed for incompleteness | 554,481 |
| 6 — purchased | 2,012,221 |
| 7 — preapproval denied | 101,772 |
| 8 — preapproval approved, not accepted | 74,703 |
| **Documented action codes total** | **15,138,510** |

The extra **1,961 rows** have `action_taken=-1`, blank LEI and blank/malformed
state code. Their loan amounts parse, but `-1` is not among the official
public-LAR action values 1–8. A separate request to the official aggregation
API with `actions_taken=-1` returns HTTP 400 and explicitly reports that valid
actions are 1–8; therefore the extra rows are outside the documented query
domain, not a ninth outcome category. All rows using documented action codes
have a nonblank LEI and a two-character state code. The audit therefore records
`PASS_WITH_QUARANTINED_SOURCE_ROWS`: raw rows are preserved; the 1,961 rows are
not silently recoded, treated as a ninth action, included in action KPIs, or
discarded from the acquisition count. Do not integrate this vintage into app
comparisons until the source anomaly is understood or the app can show the
quarantine count and exact valid-code denominator.

Reproduction:

- `scripts/acquire_hmda_browser_2018.py` streams the fixed official query to
  private D: storage, enforces a size bound, hashes bytes and writes a receipt.
- `scripts/audit_hmda_browser_2018.py` verifies the receipt/hash, strict CSV
  parsing, 99-field schema, activity year, documented action counts against the
  official aggregation API and out-of-domain rows. The loan-level CSV is
  excluded from GitHub.

## Analytical use and limitations

The data can extend HMDA application/decision coverage to 2018 after the
quarantined-row behavior is represented explicitly. The 2018 Three-Year freeze
must not be presented as a comparable One-Year release alongside 2019–2024:
freeze timing and resubmission scope differ. HMDA records describe application
and disposition, not borrower payment history, delinquency, default, loss or PD.
The public file also contains privacy-modified fields. No forecast, imputation,
synthetic values, loan-level modeling or D01 vintage addition was performed.

## Current source limitation

Treasury HAMP 2009–2017 remains unavailable at its official endpoint (TLS/host
timeout during recheck). HUD's official August 2026 FHA Portfolio Snapshot link
returned HTTP 403; an ordinary direct request to the June 2026 workbook also
returned 403. Neither was downloaded or bypassed. They remain separate open
acquisition leads, not acquired data.
