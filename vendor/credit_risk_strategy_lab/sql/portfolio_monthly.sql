-- Observed sample stocks. Never sum monthly UPB and label it originated volume.
SELECT period,
 COUNT(*) AS reported_loans,
 COUNT(*) FILTER (WHERE terminal_type IS NULL) AS active_loans,
 COUNT(*) FILTER (WHERE terminal_type IS NOT NULL) AS terminal_loans,
 COUNT(*) FILTER (WHERE terminal_type IS NULL AND delinquency_state<>'UNKNOWN') AS state_usable_active_loans,
 COUNT(*) FILTER (WHERE terminal_type IS NULL AND delinquency_state='UNKNOWN') AS unknown_active_loans,
 COUNT(*) FILTER (WHERE terminal_type IS NULL AND delinquency_state='D3PLUS') AS d3_active_loans,
 COUNT(*) FILTER (WHERE terminal_type IS NULL AND delinquency_state='REO') AS reo_active_loans,
 COUNT(*) FILTER (WHERE terminal_type IS NULL AND current_upb IS NULL) AS missing_active_balance_loans,
 SUM(current_upb) FILTER (WHERE terminal_type IS NULL) AS observed_active_upb,
 SUM(current_upb) FILTER (WHERE terminal_type IS NULL AND delinquency_state<>'UNKNOWN') AS state_usable_active_upb,
 SUM(current_upb) FILTER (WHERE terminal_type IS NULL AND delinquency_state='D3PLUS') AS d3_active_upb,
 d3_active_loans / NULLIF(state_usable_active_loans,0)::DOUBLE AS d3_count_share,
 COALESCE(d3_active_upb,0) / NULLIF(state_usable_active_upb,0)::DOUBLE AS d3_balance_share
FROM fact_loan_month GROUP BY period ORDER BY period;
