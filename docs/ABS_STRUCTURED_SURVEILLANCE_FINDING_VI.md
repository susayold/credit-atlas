# ABS structured surveillance finding — 17/10/2026

## Finding ABS-SURV-F001

**Classification:** Source-definition and reconciliation exception
**Status:** Open; root cause not established
**Scope:** Public SEC ABS-EE and deal certificate aggregates for Toyota Auto Receivables 2022-B, Toyota Auto Receivables 2024-B and Nissan Auto Receivables 2024-B.
**Release:** `abs-surveillance-2026-10-17`; one row per deal contract × public report date.

### Analyst finding

Across the three deal contracts, ABS-EE recovery values produce 83 non-zero period residuals against deal-specific certificate comparators. The comparators have different definitions: Toyota uses aggregate net liquidation proceeds built from two signed certificate components; Nissan uses current-period Recoveries of Defaulted Receivables. Residuals and tie counts therefore remain within each deal contract and are not pooled. The available aggregate evidence does not establish whether differences arise from population, cutoff, classification, correction or servicing-record mapping. These observations are not an LGD, loss estimate, fraud signal, accounting ECL or evidence of misreporting.

### Coverage and source contracts

| Deal | Periods | Report dates | Certificate recovery comparator | Source definition |
|---|---:|---|---|---|
| Toyota 2022-B | 51 | 2022-04-30–2026-06-30 | Aggregate net liquidation proceeds | Negative sum of “Net Liquidation Proceeds Received During the Collection Period” and “Recoveries on Previously Liquidated Contracts” signed certificate rows |
| Toyota 2024-B | 29 | 2024-04-30–2026-08-31 | Aggregate net liquidation proceeds | Same two-component identity, applied only within this trust |
| Nissan 2024-B | 23 | 2024-10-31–2026-08-31 | Current-period recoveries of defaulted receivables | Certificate “Recoveries of Defaulted Receivables”; principal-only recoveries remain a separate field |

Each period retains its actual certificate collection-window start and end, report date, filing date where available, accession, source URL, source signs, comparator field and exception categories. Report month is a display label, not a substitute for a collection window. Missing source fields remain blank; they are not converted to zero. The public derivative contains aggregate period rows only; asset/contract-level IDs and loan-level rows are not released.

### Reconciliation results

| Deal | Recovery ties | Recovery exceptions | Deal-only residual sum | Periods with any exception |
|---|---:|---:|---:|---:|
| Toyota 2022-B | 2/51 | 49 | +USD 2,058,647.06 | 49/51 |
| Toyota 2024-B | 1/29 | 28 | +USD 1,764,558.08 | 28/29 |
| Nissan 2024-B | 17/23 | 6 | +USD 8,859.23 | 9/23 |

There are 86 deal-period rows with at least one exception and 83 rows with a non-zero recovery comparator residual. No across-deal recovery residual, tie percentage, charge-off count or delinquency rate is calculated. The workbook intentionally labels totals “within contract only.”

Nissan’s additional exceptions cover charge-off count/amount, first `zeroBalanceCode=4` event count/amount and one literal DPD bucket mismatch. Across Nissan’s panel, literal DPD checks tie 178/184 fields; the one-day-earlier candidate ties only 86/184 across the full panel. Its 8/8 match in June 2025 is a one-month diagnostic and does not establish a replacement definition. The July 2025 ABS-EE charge-off aggregate and certificate defaulted-receivable count/principal remain non-comparable without a dated population/event mapping.

### Method and controls

For each deal and report date, recovery delta is `ABS-EE asset recovered amount − that deal's certificate recovery comparator`, retaining the source's signed value and decimal precision. `TIED` means the delta is exactly zero at source precision; every non-zero delta remains `UNRESOLVED`. Deal-specific totals in the result and Excel workbook are arithmetic sums over that deal’s selected periods only. The cross-deal total is explicitly null because comparator semantics are not homogeneous.

The release builder checks the source CSVs and receipts against SHA-256 values before producing the 103-row release. The runtime API independently checks the contracts, output ledger, source CSVs and receipts, row uniqueness, period counts and deal-specific summary values before serving the result. The Excel workbook recalculates summary formulas against the filterable period ledger and checks 103 periods, 3 contracts, 86 exception periods, 83 recovery exceptions, plus each deal's tie counts and residual sum. No forecasts, imputation or modeled values are used.

### Required follow-up evidence

Before changing a reconciliation rule or using a recovery value for loss/cashflow analysis, obtain deal/servicer evidence that maps field definitions, included populations, collection cutoffs, reversals/corrections and transaction-level amounts to the published certificate rows. Keep the finding open until that mapping is dated, sourced and independently reproducible. Public filings currently linked on every workbook ledger row allow analysts to inspect the relevant period pair directly; representative examples include [Toyota 2022-B first-period certificate](https://www.sec.gov/Archives/edgar/data/1914281/000095013122002459/d346874dex991.htm), [Toyota 2024-B first-period certificate](https://www.sec.gov/Archives/edgar/data/2012786/000095013124002190/d824511dex991.htm), [Nissan 2024-B first-period certificate](https://www.sec.gov/Archives/edgar/data/2035264/000119312524264295/d900783dex991.htm), and [Nissan July 2025 certificate](https://www.sec.gov/Archives/edgar/data/2035264/000119312525187356/d930039dex991.htm). The row-level ledger contains the corresponding ABS-EE filing links and all certificate links.

### Reproducible files

- Contract and definitions: `docs/data/abs-surveillance-contracts-2026-10-17.json`
- Aggregate exception ledger: `docs/data/abs-surveillance-exceptions-103-periods.csv`
- Hash and control receipt: `docs/data/abs-surveillance-exceptions-103-periods-receipt.json`
- Excel analyst workbook: `apps/excel/templates/CreditAtlas-ABS-Surveillance-Exceptions.xlsx`
- Existing underlying audits: `docs/TOYOTA_RECOVERY_COMPONENT_EXCEPTION_LEDGER_VI.md` and `docs/NISSAN_2024B_EXCEPTION_LEDGER_VI.md`
