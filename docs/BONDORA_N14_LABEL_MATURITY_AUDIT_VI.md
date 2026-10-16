# Bondora N14 — 12-MOB label maturity and country/time support

Audit date: **17 October 2026**. This is a source-qualification checkpoint using the private local XLSX snapshot. It emits aggregate counts only; no loan IDs or loan-level rows are released.

## Publisher evidence and source version

The current [Go & Grow Public Statistics page](https://goandgrow.eu/en/public-statistics/) still links a downloadable full Loan Dataset and identifies Go&Grow OÜ as not being the credit provider that issues the loans. The [2026 Bondora portfolio transparency report](https://goandgrow.eu/en/blog/bondora-loan-portfolio-statistics-2026-a-transparency-report/) defines PD12 as the share of loans defaulting within 12 months of issuance, describes default as more than 90 days overdue followed by contract termination for arrears, and says a full 12-month observation period is required before reporting a cohort. The report also distinguishes published current portfolio commentary from forecasts based on current performance and assumptions; this audit reproduces no such forecast.

On 17 October 2026, an HTTP HEAD request to the publisher’s current workbook link returned the same identity as the pinned local file: **162,618,206 bytes**, Last-Modified **10 August 2026**, ETag `0x8DEF6A56BF40FAD`; the local SHA-256 is `a75db03e24747aa8462f6f429b6cbdd2f7010be03da020a4bbd3536c4e1a07bf`. No newer file was available at that check. This server timestamp is a release identity, not evidence that every loan was observed through that date.

The dataset dictionary defines `has_default_within_12_months` as a true/false indicator for default observed within 12 months on book and NULL when not measurable yet. The local profile confirms **789,144 rows**, 31 source fields, **86,618 true**, **520,246 false** and **182,280 NULL**. The source dictionary’s wording and the publisher report’s current default definition are not proof that every historical export row was constructed with the same vintage-specific definition; that link still needs publisher documentation.

## Label support by time and country

The audit reads the whole local workbook, checks its pinned SHA-256, verifies the 31-field/two-sheet layout, requires unique loan IDs and valid issue dates, and classifies the outcome in three states. It then groups only counts by issue year, country and country × year. Country-year cells with fewer than 50 loans are suppressed in the Excel support sheet.

The 2026 cohort has **96,365 loans and all 96,365 labels are NULL**. The 2025 cohort has 182,056 loans: 7,499 true, 88,642 false and 85,915 NULL. The export contains 58 country-year support cells; the four cells below the workbook’s 50-loan display threshold are suppressed. The country date ranges vary materially: Finland 2013–2026, Estonia 2009–2026, Netherlands 2022–2026, Spain 2013–2023, Latvia 2023–2026 and Denmark 2025–2026. The remaining Slovakia/Lithuania support is too limited to generalize, and small cells are suppressed in the workbook. Country and year tables describe this export only; they do not estimate comparable country risk.

These counts preserve the source’s NULL state. They are not filled, treated as negative outcomes, or used for fitting. Known labels exist in earlier cohorts, but the local file alone does not establish that all negative labels have a full, correctly aligned 12-month observation window.

## Maturity cutoff diagnostic

To quantify the as-of uncertainty without changing any source label, the script applies a **diagnostic proxy**: a loan is proxy-mature if `loan_issued_at + 12 calendar months ≤ 10 August 2026`, using the workbook’s HTTP Last-Modified date. Leap-day anniversaries clamp to 28 February. This is a reproducible calendar rule, not a publisher-certified observation cutoff or target reconstruction.

Under that proxy, **617,724** loans are in the proxy-mature group. It contains 86,618 true labels, 520,246 false labels and **10,860 NULL labels**. Another **171,420** loans fall before the proxy anniversary and all are NULL. The 10,860 proxy-mature NULLs are all from 2025 originations. Every one also lacks recorded action evidence on or after the assumed 12-month anniversary: 7,996 have no last-recorded-action date; 2,864 have an action date before the anniversary; none has one on/after it. In this subset, current `loan_status` is Active for 7,178, Repaid for 2,864 and Defaulted for 818; `is_default` is true for 818 and false for 10,042. The independently counted `months_on_book` values are under 12 for 9,150, at least 12 for 1,657 and missing for 53.

This pattern shows why file Last-Modified cannot stand in for loan-level follow-up. It does **not** prove a source error: the NULLs remain as published because the file lacks a per-loan observation end and the meaning of `months_on_book` is active-status time, not necessarily elapsed time since issue. The NULLs must remain NULL until the publisher explains follow-up coverage and label construction. No values were projected, imputed or altered.

## Feature and use controls

No predictor set was selected. The dictionary says `customer_risk_rating` is at issue and identifies initial issue fields, but the file has no application decision timestamp, requested amount, rejected-applicant population or timestamped feature history. The definition of `combined_income` does not say when the information became available relative to approval. Those gaps keep application-underwriting use unqualified.

Current status/default, balances, past-due days, default duration, last action, payment totals, fees, next payment, early repayment and projected NPV are post-booking or servicing/outcome information. They must be excluded from any application-time feature set. A future temporal benchmark would require a fixed label cutoff, mature cohorts, feature-availability evidence, versioned data snapshots and an out-of-time protocol; this audit did not train a model or calculate PD.

The publisher’s public download page does not by itself settle row-level redistribution or commercial-use rights. Keep the 162 MB source workbook and detailed country-year report private pending rights review. The public Excel companion contains aggregate support counts only, applies small-cell suppression, and carries the same rights/use caveat.

## Plan status and reproducibility

N14 has a reproducible full-row audit for three-valued label counts, country/time support, small-cell control and a 12-month cutoff sensitivity. The underlying label observation cutoff and the 10,860 NULL cases remain unresolved, so this is **partial source qualification**, not model readiness or application underwriting.

- Source audit: `scripts/audit_bondora_n14_readiness.py`
- Unit checks for tri-state labels and calendar-anniversary boundary: `tests/test_bondora_n14_readiness.py`
- Private aggregate report: `D:\data\Codex\credit-atlas\artifacts\private\bondora-n14-readiness\report.json`
- Excel companion: `apps/excel/templates/CreditAtlas-Bondora-N14-Label-Support.xlsx`
- Existing source profile and field-level research: `docs/BONDORA_PUBLIC_DATASET_RESEARCH_VI.md`
