-- One row per loan; no synthetic rows before acquisition or after exit.
WITH ordered AS (
 SELECT *, LAG(period) OVER (PARTITION BY loan_id ORDER BY period) AS prev_period
 FROM fact_loan_month
), coverage AS (
 SELECT loan_id, MIN(period) AS landmark, MAX(period) AS last_observed_month,
  COUNT(*) AS observed_months,
  COUNT(*) FILTER (WHERE date_diff('month',prev_period,period)>1) AS gap_pairs,
  first(loan_age ORDER BY period) AS source_entry_age,
  first(delinquency_state ORDER BY period) AS entry_state,
  first(modification ORDER BY period) AS entry_modification,
  first(terminal_type ORDER BY period) AS entry_terminal,
  MIN(period) FILTER (WHERE terminal_type IS NOT NULL) AS first_terminal_month,
  COUNT(*) FILTER (WHERE terminal_type IS NOT NULL) AS terminal_rows
 FROM ordered GROUP BY loan_id
)
SELECT c.*, o.original_upb, o.origination_year, o.is_relief_refinance,
 date_diff('month',o.first_payment_date,c.landmark)+1 AS contractual_entry_age
FROM coverage c JOIN dim_loan o USING(loan_id);
