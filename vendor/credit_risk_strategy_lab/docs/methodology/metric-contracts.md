# Shared metric contracts — monthly stocks

Executable registry: `src/crsl/metrics.py`; calculation owner: `sql/portfolio_monthly.sql`.
The registry covers the implemented monthly stock metrics only. Model, policy, forecast,
vintage-incidence and economics registries remain separate unfinished B07 work.

Each definition names grain, unit, formula, denominator, as-of/horizon, evidence class,
source SQL, minimum support, uncertainty limitation and zero-denominator behavior.

- Count D3 share uses state-usable active loan count.
- Balance D3 share uses known state-usable active UPB, not loan count.
- REO is disclosed separately from numeric D3.
- Unknown states and missing balances accompany headline values.
- Zero denominator produces null/unavailable, never a fabricated zero rate.
- Empty monthly results fail validation. A missing filtered result must not become a zero KPI.
- Monthly UPB is a stock, not an additive time-period originated volume.
- Rates are fractions (0.1=10%). Dollars remain USD and counts remain loans.

The validator independently recomputes both ratios from canonical numerator/denominator
columns, checks unique month and reconciles active/terminal and known/unknown counts.
It does not certify full population representativeness, censoring-adjusted incidence,
source correctness, disclosure permission or the entire project's research readiness.

Reproduce against an immutable completed portfolio run:

```powershell
.\.venv\Scripts\python -m crsl.metrics --portfolio-run artifacts/private/portfolio-a317e27aa17d
```

Every validation produces a private registry snapshot and receipt tied to the exact monthly
Parquet hash. Website and workbook adapters should consume these same definitions and
validated tables rather than independently inventing their own bad-rate calculations.
