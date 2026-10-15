-- Development primary target: first-observed landmark, numeric D3 within t+1..t+12.
-- Horizon and entry age parameters are substituted only from checked integers.
WITH eligibility AS (
 SELECT *, CASE
  WHEN entry_terminal IS NOT NULL THEN 'terminal_at_entry'
  WHEN entry_state IN ('D3PLUS','REO') THEN 'severe_at_entry'
  WHEN entry_state='UNKNOWN' THEN 'unknown_at_entry'
  WHEN entry_modification IS NOT NULL THEN 'modified_at_entry'
  WHEN source_entry_age IS NULL OR contractual_entry_age IS NULL THEN 'missing_entry_age'
  WHEN source_entry_age<>contractual_entry_age THEN 'entry_age_mismatch'
  WHEN source_entry_age NOT BETWEEN {min_age} AND {max_age} THEN 'not_early_entry'
  ELSE 'eligible' END AS eligibility_reason,
  (landmark + INTERVAL '{horizon} months')::DATE AS horizon_end
 FROM observation
), candidates AS (
 SELECT e.loan_id,
  MIN(p.period) FILTER (WHERE p.delinquency_state='D3PLUS') AS d3_month,
  MIN(p.period) FILTER (WHERE p.terminal_type='PREPAID_OR_MATURED') AS prepay_month,
  MIN(p.period) FILTER (WHERE p.terminal_type IN ('CREDIT_TERMINATION','OTHER_TERMINATION')
    OR p.delinquency_state='REO') AS other_exit_month
 FROM eligibility e LEFT JOIN fact_loan_month p
  ON e.loan_id=p.loan_id AND p.period>e.landmark AND p.period<=e.horizon_end
 GROUP BY e.loan_id
), stop AS (
 SELECT e.*, c.* EXCLUDE(loan_id),
  LEAST(c.d3_month,c.prepay_month,c.other_exit_month,e.horizon_end) AS stop_month
 FROM eligibility e JOIN candidates c USING(loan_id)
), evidence AS (
 SELECT s.*,
  COUNT(p.period) AS observed_to_stop,
  COUNT(*) FILTER (WHERE p.delinquency_state='UNKNOWN') AS unknown_to_stop,
  date_diff('month',s.landmark,s.stop_month) AS required_to_stop
 FROM stop s LEFT JOIN fact_loan_month p ON s.loan_id=p.loan_id
  AND p.period>s.landmark AND p.period<=s.stop_month
 GROUP BY ALL
), outcomes AS (
 SELECT *, CASE
  WHEN eligibility_reason<>'eligible' THEN 'ineligible'
  WHEN unknown_to_stop>0 THEN 'unknown_followup'
  WHEN observed_to_stop<required_to_stop THEN
    CASE WHEN last_observed_month<stop_month THEN 'administrative_censoring' ELSE 'gap_followup' END
  WHEN d3_month=stop_month THEN 'd3_event'
  WHEN other_exit_month=stop_month THEN 'other_exit'
  WHEN prepay_month=stop_month THEN 'prepayment'
  ELSE 'complete_no_event' END AS outcome
 FROM evidence
)
SELECT *, CASE WHEN outcome='d3_event' THEN 1
 WHEN outcome IN ('prepayment','complete_no_event') THEN 0 ELSE NULL END::INTEGER AS target,
 outcome='prepayment' AS competing_prepayment,
 CASE WHEN outcome IN ('d3_event','prepayment','complete_no_event') THEN stop_month ELSE NULL END AS label_known_month,
 '{horizon}'::INTEGER AS horizon_months,
 'first_observed_early_entry_d3_before_prepayment' AS estimand
FROM outcomes;
