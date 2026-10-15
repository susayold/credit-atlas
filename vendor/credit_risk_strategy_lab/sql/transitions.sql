-- Opening UPB at t, not closing UPB at t+1. No cross-gap one-month transitions.
WITH following AS (
 SELECT loan_id,period,current_upb,delinquency_state,terminal_type,
  LEAD(period) OVER w AS next_period,
  LEAD(delinquency_state) OVER w AS next_state,
  LEAD(terminal_type) OVER w AS next_terminal
 FROM fact_loan_month WINDOW w AS (PARTITION BY loan_id ORDER BY period)
)
SELECT *, CASE WHEN next_period IS NULL THEN 'NO_NEXT_OBSERVATION'
 WHEN date_diff('month',period,next_period)<>1 THEN 'GAP'
 ELSE COALESCE(next_terminal,next_state) END AS destination,
 COALESCE(date_diff('month',period,next_period)=1,FALSE) AS adjacent
FROM following WHERE terminal_type IS NULL;
