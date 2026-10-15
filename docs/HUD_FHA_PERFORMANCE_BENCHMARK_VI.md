# HUD FHA portfolio performance benchmark

CreditAtlas now includes a separate aggregate reference for HUD's August 2026 FHA Single-Family Loan Performance Trends report. It is shown on the NSMO page as outside context, but its FHA population stays separate from FHFA/CFPB NSMO and Freddie Mac D01.

## Data captured

- **Table 1, page 2:** monthly end-of-month Active Insurance in Force count and delinquency/exception rates for August 2025–August 2026, with both non-seasonally adjusted (NSA) and seasonally adjusted (SA) values: 26 observations.
- **Table 2, page 3:** 22 quarterly records for new 90+ counts and reported reason shares from 2021Q4 through the partial 2026Q4 July/August rows.
- **Table 3, pages 4–5:** all 60 aggregate rows across loan purpose, refinance detail, credit score, fiscal-year cohort, original loan amount, property type, purchase repeat/first-time status and down-payment assistance. The rows include IIF composition, past-due, 30/60/90+ delinquency, foreclosure, bankruptcy and serious-delinquency rates where reported.
- **Table 4, page 6:** 37 monthly records from August 2023 through August 2026 for active IIF, foreclosure starts, in-foreclosure counts, paid claims, six-month starts average and annualized foreclosure rate.
- **Table 5, page 7:** 50 U.S./state/territory REO recovery rows for July 2026 and comparison months, with disposition counts and percentage-point changes.
- **Table 6, page 8:** 13 monthly REO disposition/loss rows from July 2025 through July 2026, with reported loss/cost components, average dollars, counts and stage durations.
- **Excel:** `apps/excel/templates/CreditAtlas-HUD-FHA-Performance.xlsx`, with a guide and six filterable data sheets. Sheets use frozen headers, source table/page, numeric measures, true/false partial-period values, and units for rates, dollars and stage months.
- **App:** `/api/hud-fha-performance` serves all six aggregate tables; `/downloads/hud-fha-performance.xlsx` returns the workbook. The NSMO page renders Tables 1–6, the NSA/SA selector and filters for all eight Table 3 panels.

## Interpretation and limitations

HUD defines Table 1's 90-day rate as loans at least three months delinquent, excluding loans in foreclosure or bankruptcy processing. Serious delinquency is the sum of 90+ delinquency, in-foreclosure and in-bankruptcy rates. Table 3 rates are percentages of active-loan counts; segment comparisons are unadjusted. HUD notes that reporting-method differences may prevent full reconciliation with other FHA reporting areas.

Table 2 reason shares are a distribution across coded reported reasons, not causal explanations or individual-level predictors; the last two 2026Q4 observations are partial. Table 4 starts are monthly flow, in-foreclosure is a stock, claims paid are a separate flow, and the annualized rate uses beginning IIF. Table 5 recovery is relative to UPB at default and can exceed 100%; low counts can make state-level values volatile. Table 6's reported components are incomplete and cannot be summed into net loss.

This is a program portfolio benchmark, not loan-level data. It does not add NSMO events, qualify a Freddie vintage, produce target labels, or support model training. Credit-score bands and loan-purpose groups are descriptive; they do not establish causal effects.

IIF composition shares use panel-specific denominators and are rounded as printed. Refinance rows are hierarchical: child no-cash-out/cash-out rows overlap with the conventional or FHA parent row and must not be added to it. The credit-score panel excludes streamline refinances and reflects reporting availability; credit-score reporting became mandatory in July 2008. Fiscal-year cohorts describe the active portfolio in August 2026 rather than lifetime cohort outcomes, and the 2026 cohort has a partial/shorter observation window.

## Acquisition and reproducibility

The source is HUD's public report index at <https://www.hud.gov/hud-partners/single-family-loan-performance> and the August 2026 report PDF at <https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf>. The official PDF text was readable through the browser research source and the values were transcribed into six CSVs in `docs/data/` (Tables 1–6). Direct binary retrieval returned HTTP 403 during acquisition, so the PDF was not saved locally and no raw-PDF SHA-256 is claimed. Source table and page are retained per row; workbook and app disclose this text-transcription limitation.

The app acceptance now verifies all six tables and their source-specific boundaries: 26 monthly rows, 60 subgroup rows, 22 new-90+ reason rows, 37 foreclosure rows, 50 recovery rows and 13 loss-detail rows. The browser also checks the latest partial-period reason count, the August foreclosure pipeline KPIs, July U.S. REO recovery, July net loss, the six-table Excel download and the 390px mobile layout. Latest receipt: `artifacts/private/hud-tables-browser-qa-20261016/receipt.json` in the private D: runtime; seven grouped checks pass with no browser errors.

After checking a newer official report and updating the two curated CSVs, rebuild the workbook with the host-provided `@oai/artifact-tool` dependency available:

```powershell
node scripts/build_hud_fha_workbook.mjs . apps/excel/templates/CreditAtlas-HUD-FHA-Performance.xlsx
```

Refresh only after opening the current official report and checking month coverage, table definitions, publication date, and values. Keep the source PDF available in the workbook/report lineage when normal access permits. Never infer missing rows or join these totals to NSMO/Freddie loan records.
