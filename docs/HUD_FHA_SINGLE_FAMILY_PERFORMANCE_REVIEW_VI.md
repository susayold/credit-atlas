# HUD FHA Single-Family Loan Performance Trends — source review

Reviewed: 16/10/2026. Source scope: FHA-insured U.S. forward single-family
mortgages. This is a complementary government-loan benchmark for Mortgage
Sources / portfolio monitoring; it is not an additional loan-level training
set for D01 or NSMO D02.

## What the source contains

HUD publishes a monthly **FHA Single-Family Loan Performance Trends** report.
The official page lists reports from 2013 through August 2026 at this review
date. The August 2026 report has ten pages and six tables plus a fiscal-year
failure-rate figure:

| Report section | Available measures | Useful module | Boundary |
|---|---|---|---|
| 1. Delinquency rates by month | End-of-month insurance-in-force count; 30-, 60-, 90-day delinquency; foreclosure; bankruptcy; serious delinquency; seasonally adjusted and unadjusted series | Mortgage performance monitoring / macro context | Aggregate FHA-only time series; no loan IDs |
| 2. New 90+ delinquency by reason | New 90+ counts and reason shares by fiscal quarter | Early-warning context / hardship mix | Reason attribution is a share of new 90+ records, not an individual-level predictor; recent quarter may be partial |
| 3. Delinquency by characteristics | Active-loan denominator, IIF share and delinquency/serious-delinquency rates by credit-score band, fiscal-year cohort, original loan amount, property type, purchase/refinance, DPA | Risk segmentation benchmark | Subpanel denominators differ; reported rates are descriptive and do not establish causal effects |
| 4. Foreclosure statistics | Insurance in force, foreclosure starts, in-foreclosure counts, HUD-paid claims, six-month moving average and annualized rate | Collections / foreclosure pipeline monitoring | Annualized claim rate has a separate denominator and is not the Table 1 foreclosure share |
| 5. REO recovery | Disposition counts and recovery rates by state/territory, with month/year changes | LGD / recovery context | Rates use UPB at default; small state counts can be unstable and recovery can exceed 100% |
| 6. REO loss components | Claim expense, holding cost, collateral loss, sales expense, program discounts, net-loss rate, average loss/UPB, disposition count, and stage-duration metrics | Loss-severity benchmark | HUD states listed cost categories are incomplete and do not necessarily sum to net-loss rate |

The companion **FHA Single Family Portfolio Snapshot** is a different source:
HUD describes it as monthly loan-level records with geographic, purpose/type,
product, down-payment-source, lender/sponsor and origination-month fields. It
does not provide the monthly performance history needed for a loan-level model;
the trends report remains aggregate. Keep the two source contracts separate.

## Verified August 2026 examples

The August 2026 report states 8,416,639 active loans in insurance in force.
Its non-seasonally adjusted values show 90-day delinquency of 5.24%, foreclosure
of 0.63%, bankruptcy of 0.55%, and serious delinquency of 6.42%. Serious
delinquency is explicitly the sum of 90+ delinquency, in-foreclosure and
in-bankruptcy; the 90-day delinquency category excludes foreclosure and
bankruptcy cases. The same report's seasonally adjusted serious delinquency is
6.63%, so adjusted and unadjusted series must stay distinct.

The August 2026 characteristic table reports serious delinquency of 11.28% for
the `<500` score band and 1.94% for `720–850`; purchase loans show 7.20% versus
4.32% for refinance loans. These are aggregate segment rates, not borrower-level
labels or model coefficients. Credit-score coverage is incomplete: HUD notes
that reporting was not mandatory until July 2008 and streamline refinance loans
do not require a score. The table also warns that segment shares within a
subpanel sum to that subpanel, not always to all insurance-in-force loans.

Table 5 reports a U.S. REO recovery rate of 50.5% on 392 July 2026 dispositions.
Table 6 reports a July 2026 net-loss rate of 49.48%, average dollar loss of
$101,498 and average unpaid balance of $205,141. It separately lists component
cost percentages and stage times; its footnote says the components are not
exhaustive and may omit recoveries. Do not reconstruct LGD from a simple sum of
those component rows.

## Fit and integration recommendation

Use this source only in a separately labeled FHA/government-backed performance
context view. Preserve `report_month`, `table_id`, `segment`, `metric`,
`adjustment_status`, denominator, unit and source note as data dimensions.
Keep values reported in percent as percent; never join them to NSMO loan rows,
Freddie loan keys, or HMDA applications. The report may support portfolio
monitoring, segmentation comparison, and source-specific KPI panels. It cannot
increase the 65 origination-aligned NSMO 90+ support count, create a Freddie
vintage, or qualify a PD model.

Metric definitions must remain source-specific:

- Table 1/3 active-loan rates use active counts in FHA insurance in force; 90+
  delinquency excludes foreclosure/bankruptcy while serious delinquency includes
  both.
- Table 2 reason shares refer to new 90+ delinquency records; the August 2026
  document includes fiscal-quarter values through Q4 July/August, which are not
  complete-quarter results.
- Table 4 annualized foreclosure rate is based on the monthly foreclosure-claim
  rate scaled against beginning insurance in force, not the Table 1 in-foreclosure
  share.
- Table 5 recovery and Table 6 loss measures are based on disposition/default
  balances and are sensitive to small counts, reporting lag and differing HUD
  reporting methodology.

HUD says its delinquency/foreclosure numbers may not fully reconcile with other
FHA reporting areas because methodologies differ. Treat the monthly report as
an aggregate source with its own published definitions; do not force exact ties
to HUD's portfolio snapshot or FHFA NMDB.

## Acquisition checkpoint

The August 2026 PDF and monthly snapshot are linked from public HUD pages, but
ordinary direct `HEAD` requests from this workspace returned HTTP 403 for both
the XLSX snapshot and PDF report. The report text was reviewed through the
available public web document view; no binary payload was acquired or access
restriction bypassed. Table 1 and all 60 Table 3 rows were transcribed into a
separate curated aggregate reference with source table/page, denominator
definitions, an Excel workbook and an NSMO-page context panel; see
`HUD_FHA_PERFORMANCE_BENCHMARK_VI.md`. There is still no local PDF hash or
binary parser receipt. The aggregate capture is **integrated from public report
text; raw PDF and portfolio snapshot download remain pending**.

## Official references

- [HUD FHA Single-Family Loan Performance Trends reports](https://www.hud.gov/hud-partners/single-family-loan-performance)
- [HUD FHA August 2026 Credit Risk Report](https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf)
- [HUD FHA Single-Family Portfolio Snapshot and data definitions](https://www.hud.gov/stat/sfh/fha-sf-portfolio-snapshot)
