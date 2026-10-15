# Forecast and stress boundary

`crsl.forecast.project_state_mass` is a deterministic scenario primitive. It
projects a closed population through a complete adjacent-state transition
matrix and asserts mass conservation. `naive_last_state` is a carry-forward
baseline for a later backtest harness.

Neither function is a qualified portfolio forecast. The current data has one
origination vintage and no rolling-origin forecast targets. The outputs are
marked `scenario_only` or `naive_baseline`, have `backtested: false`, and are
not released as expected balances, future defaults, loss dollars, or
regulatory stress results. A real forecast requires additional annual samples,
mature horizons, forecast-origin eligibility, naïve comparison, and an
explicit scenario assumption register.
