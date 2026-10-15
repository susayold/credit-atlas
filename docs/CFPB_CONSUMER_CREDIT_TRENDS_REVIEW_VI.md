# CFPB Consumer Credit Trends — source review and acquisition status

Checked: 2026-10-16. This is an official public-source review; the CSV payload was not acquired because the file host returned HTTP 403 from this environment.

## What the source contains

CFPB says its dashboards track mortgage, credit-card, auto-loan, and student-loan credit trends. The dashboard includes origination and inquiry metrics for selected products and risk-profile, income, or age profiles for originations. The official page now says it was last updated October 15, 2026 (the prior review showed September 17); it describes a nationally representative sample of credit records from one nationwide consumer reporting agency (NCRA), with direct identifiers removed before transfer. The data are market aggregates, not a borrower-level lending file or repayment panel.

Official entry points: [Consumer Credit Trends](https://www.consumerfinance.gov/data-research/consumer-credit-trends/), [CFPB Public Data Inventory](https://www.consumerfinance.gov/data-research/public-data-inventory/), [all-data CSV](https://files.consumerfinance.gov/data/consumer-credit-trends/all_data.csv), and [codebook/data dictionary](https://files.consumerfinance.gov/f/documents/CCT_dd_cb_all_files.xlsx).

## Access check

The public dashboard page lists a CSV containing all Consumer Credit Trends data points and an Excel codebook. On 2026-10-16, direct HEAD requests to both official file URLs still returned HTTP 403 from this environment. The official page-linked fetcher recognizes the CSV and workbook content types but cannot expose those binary downloads as page text. No CSV or workbook was saved. This review does not retry through alternate identities or automate around the denial.

## Fit to CreditAtlas

This source could extend P1/P4 with multi-product market context and time-series indicators after the dictionary, download scope, units, vintages, subgroup definitions, missing/suppressed cells, and revision behavior are inspected. It cannot supply borrower-level features, application outcomes, delinquency transitions, default labels, loss, or model training records. Treat it as aggregated market monitoring only; do not join it to individual loans or use it as an additional independent credit-bureau panel.

Acquisition status: **not downloaded; no new dataset added**. The dashboard refresh is newer than the previously checked version, but download access remains unresolved. The next permissible step is to use the official CFPB download path when it is accessible, or request the publisher's approved access route. A 403 response is not evidence of unrestricted access.
