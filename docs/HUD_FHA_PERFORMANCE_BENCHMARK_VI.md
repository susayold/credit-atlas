# HUD FHA portfolio performance benchmark

CreditAtlas now includes a separate aggregate reference for HUD's August 2026 FHA Single-Family Loan Performance Trends report. It is shown on the NSMO page as outside context, but its FHA population stays separate from FHFA/CFPB NSMO and Freddie Mac D01.

## Data captured

- **Table 1, page 2:** monthly end-of-month Active Insurance in Force count and delinquency/exception rates for August 2025–August 2026, with both non-seasonally adjusted (NSA) and seasonally adjusted (SA) values: 26 observations.
- **Table 3, pages 4–5:** all 60 aggregate rows across loan purpose, refinance detail, credit score, fiscal-year cohort, original loan amount, property type, purchase repeat/first-time status and down-payment assistance. The rows include IIF composition, past-due, 30/60/90+ delinquency, foreclosure, bankruptcy and serious-delinquency rates where reported.
- **Excel:** `apps/excel/templates/CreditAtlas-HUD-FHA-Performance.xlsx`, with `Bat dau`, `Monthly trend` and `Subgroup rates` sheets. Each data sheet has a filterable Excel Table, frozen header, source table/page columns, panel-specific share denominator and original percent units.
- **App:** `/api/hud-fha-performance` serves the bounded aggregate report; `/downloads/hud-fha-performance.xlsx` returns the Excel workbook. The NSMO page provides the NSA/SA selector and filters for all eight Table 3 panels.

## Interpretation and limitations

HUD defines Table 1's 90-day rate as loans at least three months delinquent, excluding loans in foreclosure or bankruptcy processing. Serious delinquency is the sum of 90+ delinquency, in-foreclosure and in-bankruptcy rates. Table 3 rates are percentages of active-loan counts; segment comparisons are unadjusted. HUD notes that reporting-method differences may prevent full reconciliation with other FHA reporting areas.

This is a program portfolio benchmark, not loan-level data. It does not add NSMO events, qualify a Freddie vintage, produce target labels, or support model training. Credit-score bands and loan-purpose groups are descriptive; they do not establish causal effects.

IIF composition shares use panel-specific denominators and are rounded as printed. Refinance rows are hierarchical: child no-cash-out/cash-out rows overlap with the conventional or FHA parent row and must not be added to it. The credit-score panel excludes streamline refinances and reflects reporting availability; credit-score reporting became mandatory in July 2008. Fiscal-year cohorts describe the active portfolio in August 2026 rather than lifetime cohort outcomes, and the 2026 cohort has a partial/shorter observation window.

## Acquisition and reproducibility

The source is HUD's public report index at <https://www.hud.gov/hud-partners/single-family-loan-performance> and the August 2026 report PDF at <https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf>. The official PDF text was readable through the browser research source and the values were transcribed into `docs/data/hud-fha-performance-2026-08.csv` and `docs/data/hud-fha-performance-2026-08-subgroups.csv`. Direct binary retrieval returned HTTP 403 during acquisition, so the PDF was not saved locally and no raw-PDF SHA-256 is claimed. The source table and page are retained per row, and the workbook records this extraction limit.

After checking a newer official report and updating the two curated CSVs, rebuild the workbook with the host-provided `@oai/artifact-tool` dependency available:

```powershell
node scripts/build_hud_fha_workbook.mjs . apps/excel/templates/CreditAtlas-HUD-FHA-Performance.xlsx
```

Refresh only after opening the current official report and checking month coverage, table definitions, publication date, and values. Keep the source PDF available in the workbook/report lineage when normal access permits. Never infer missing rows or join these totals to NSMO/Freddie loan records.
