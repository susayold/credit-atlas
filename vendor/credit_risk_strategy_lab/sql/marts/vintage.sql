-- One endpoint per eligible loan, relative to its first observed month.
-- Never resume first-event follow-up after an unknown state or missing month.
WITH ordered AS (
 SELECT p.loan_id, p.period, p.delinquency_state, p.terminal_type,
  date_diff('month', l.landmark, p.period)::INTEGER AS age,
  LAG(date_diff('month', l.landmark, p.period), 1, 0)
   OVER (PARTITION BY p.loan_id ORDER BY p.period) AS previous_age
 FROM fact_loan_month p JOIN labels l USING (loan_id)
 WHERE l.eligibility_reason='eligible' AND p.period>l.landmark
  AND p.period<=l.horizon_end
), times AS (
 SELECT loan_id,
  MIN(age) FILTER (WHERE delinquency_state='D3PLUS') AS d3_age,
  MIN(age) FILTER (WHERE terminal_type='PREPAID_OR_MATURED') AS prepay_age,
  MIN(age) FILTER (WHERE terminal_type IN ('CREDIT_TERMINATION','OTHER_TERMINATION')
    OR delinquency_state='REO') AS other_age,
  MIN(CASE WHEN age>previous_age+1 THEN previous_age+1
    WHEN delinquency_state='UNKNOWN' THEN age END) AS unavailable_age,
  MAX(age) AS last_age
 FROM ordered GROUP BY loan_id
), stops AS (
 SELECT l.loan_id, l.origination_year, l.is_relief_refinance, l.landmark,
  l.original_upb, t.* EXCLUDE(loan_id),
  LEAST(t.d3_age,t.prepay_age,t.other_age) AS first_event_age,
  LEAST(COALESCE(t.unavailable_age-1,{max_age}),
    COALESCE(t.last_age,0),{max_age})::INTEGER AS censor_age,
  date_diff('month',l.landmark,(SELECT MAX(period) FROM fact_loan_month))::INTEGER AS calendar_age
 FROM labels l LEFT JOIN times t USING(loan_id)
 WHERE l.eligibility_reason='eligible'
)
SELECT loan_id,origination_year,is_relief_refinance,landmark,original_upb,calendar_age,
 CASE WHEN first_event_age<=censor_age THEN first_event_age ELSE censor_age END::INTEGER AS stop_age,
 CASE WHEN first_event_age<=censor_age THEN
   CASE WHEN first_event_age=d3_age THEN 'd3'
        WHEN first_event_age=other_age THEN 'other_exit' ELSE 'prepayment' END
  ELSE 'censored' END AS endpoint,
 CASE WHEN first_event_age<=censor_age THEN NULL
      WHEN unavailable_age IS NOT NULL AND unavailable_age-1=censor_age THEN 'unknown_or_gap'
      WHEN censor_age={max_age} THEN 'horizon_complete'
      ELSE 'administrative' END AS censor_reason
FROM stops ORDER BY loan_id
