# Observed loss definition and B18 gate

## Scope

This project uses Freddie Mac Release 47 reported loss components as an
observed accounting diagnostic. The source is a funded-loan performance panel,
not a lender cash-flow ledger. The output is therefore not actual lender P&L,
recovery IRR, NPV, LGD certification, IFRS 9 staging, or expected-loss dollars.

## Terminal record rule

Only loss-code terminal rows `02`, `03`, `09`, and `15` enter the resolved-loss
cohort. A loan contributes its earliest terminal row once. Later rows can carry
cumulative or revised values and are not summed again. The summary reports how
many duplicate terminal rows were removed.

## Formula and signs

When every required signed component is populated, the independent check is

`actual_loss - (removal_upb + net_sales_proceeds + delinquent_accrued_interest + total_expenses + mi_recoveries + non_mi_recoveries)`.

Missing components keep the row out of the formula check and component bridge.
Values are not clipped: a negative reported loss, a zero denominator, and a
severity above 100% remain visible and are not silently replaced with zero.
Expense reconciliation is separately checked against legal, maintenance,
taxes/insurance, and miscellaneous expense fields.

## Severity and resolution

The default descriptive denominator is `removal_upb`. Because source balance
components can be signed, severity uses the absolute reported-loss magnitude
over the absolute exposure magnitude and keeps the raw signed bridge separately.
Only non-zero, observed
denominators produce a severity observation. The summary keeps
resolved count, unresolved count, unavailable-component count, loss amount,
uncapped severity, and resolution support separate. A 1,000-loan support rule
is a research gate, not a universal regulatory threshold.

## Current status

The 2012 sample has reported loss observations and a formula reconciliation,
but the B18 model gate remains blocked until resolved support, compatible
horizon, component coverage, and temporal validation are reviewed. No expected
loss dollars are released when the gate is blocked.
