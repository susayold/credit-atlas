# HMDA 2023 — national One-Year dataset acquisition and audit

**Checkpoint:** 2026-10-16. **Status:** official 2023 nationwide One-Year CSV
downloaded, hashed, profiled, reconciled, and integrated as a private aggregate
view. Raw rows and audit workbook remain on D:; no row-level data is published.

Official references: [2023 data publication page](https://ffiec.cfpb.gov/data-publication/2023),
[HMDA Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/),
and [2023 nationwide Data Browser](https://ffiec.cfpb.gov/data-browser/data/2023?category=nationwide).
The static One-Year release was frozen on **2025-05-19**.

## Source and acquisition evidence

This is the official FFIEC/CFPB national One-Year loan-application register for
activity year 2023. It is a static release with a post-deadline resubmission
window, separate from the 2023 Snapshot and 2025 Snapshot release designs.

| Check | Verified result |
|---|---:|
| LAR records | 11,564,178 |
| Columns | 99 |
| Distinct reporting LEIs | 5,129 |
| State/territory codes | 56 |
| CSV bytes | 4,399,684,763 |
| CSV SHA-256 | `b2fcebcc952cc25cc133f75912845374f876ce56bd4542b97f44c0cc2d9c5652` |
| Release freeze date | 2025-05-19 |

Every action count reconciles to the official nationwide aggregation API. The
sum of the eight counts equals the profiled CSV rows. The acquisition profile
reports zero wrong-year, invalid action, invalid state, invalid loan-type,
invalid LEI, and invalid loan-amount rows.

| `action_taken` | Rows |
|---|---:|
| 1 — originated | 5,710,399 |
| 2 — approved, not accepted | 310,898 |
| 3 — denied | 2,037,094 |
| 4 — withdrawn | 1,468,108 |
| 5 — file closed for incompleteness | 536,137 |
| 6 — purchased loan | 1,263,097 |
| 7 — preapproval request denied | 62,622 |
| 8 — preapproval approved, not accepted | 175,823 |
| **Total** | **11,564,178** |

For the explicitly defined descriptive decision share, action 3 is the numerator
and actions 1+2+3 are the denominator:

`2,037,094 / (5,710,399 + 310,898 + 2,037,094) = 25.2792%`.

This describes the observed application disposition mix. It is not PD, delinquency,
default, repayment, or loss.

## 2023–2024 comparison

The 2023 and 2024 One-Year releases use the same action-code definitions and the
same descriptive denominator, so the app and workbook show both release-level
counts and the change. Total LAR records rise by 695,021 (+6.0101%), the action
1–3 denominator rises by 603,388 (+7.4877%), and action-3 denials rise by 66,368.
The descriptive denied share falls by 0.9948 percentage points, from 25.2792% to
24.2844%.

These are comparisons between two frozen public release populations. They do not
identify causal effects, within-borrower changes, approval quality, repayment
performance, or default risk. HMDA's public loan amounts are privacy-modified
midpoints of $10,000 intervals; summing them is not funded cash or outstanding
balance. Fields and categories can also change across years, so the workbook
retains source spellings and flags version differences rather than silently
harmonizing.

## App, Excel, and validation

The app has a separate One-Year 2023 panel, source-specific aggregate breakdowns,
action-3-only primary denial reasons, JSON export, and a 2023–2024 comparison
with release dates and denominator notes. The private audit workbook has eight
filterable sheets: Overview, Actions, Geography, Institution LEI, Credit &
product, Field dictionary, Source audit, and 2023 vs 2024. The dictionary records
all 99 observed source fields. The multi-million-row CSV is not copied into
Excel, which has a worksheet row limit; the workbook exposes audited summaries
and source metadata instead.

Browser acceptance **PASS: 11 checks, zero browser errors**, including 2023
summary and action counts, geography and denial-reason views, exact JSON export,
byte-identical private Excel download, comparative metrics, and narrow viewport.
Related automated tests: **27 passed**. The source-specific aggregate view has
its own receipt and SHA-256 lineage.

Private artifacts:

- CSV and receipt: `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2023-b2fcebcc952c`
- Workbook: `D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-one-year-2023-b2fcebcc952c\CreditAtlas-HMDA-One-Year-2023-Audit.xlsx`
- Aggregate view: `D:\data\Codex\credit-atlas\artifacts\private\hmda-one-year-2023-view-b2fcebcc952c`
- Browser QA: `D:\data\Codex\credit-atlas\artifacts\private\hmda-national-browser-qa-c02aa035f091\receipt.json`

No application row is included in the public repository. No variable was forecast,
imputed, or synthesized, and no model was fitted. This is D08 application/decision
data, not D01 mortgage performance data; it adds no Freddie vintage and does not
close D01 R2/R3.
