-- Entry eligibility only: do not select on whether a future target becomes observed.
WITH measurements AS (
 SELECT l.loan_id,l.eligibility_reason,l.eligibility_reason='eligible' AS entry_eligible,
  o.is_relief_refinance,o.classic_fico::DOUBLE AS classic_fico,
  o.original_dti::DOUBLE AS original_dti,o.original_ltv::DOUBLE AS original_ltv,
  o.original_cltv::DOUBLE AS original_cltv,o.original_upb::DOUBLE AS original_upb
 FROM labels l JOIN dim_loan o USING(loan_id)
), long_form AS (
 SELECT m.loan_id,m.eligibility_reason,m.entry_eligible,m.is_relief_refinance,
   v.feature,v.value
 FROM measurements m CROSS JOIN LATERAL (VALUES
  ('classic_fico',m.classic_fico),('original_dti',m.original_dti),
  ('original_ltv',m.original_ltv),('original_cltv',m.original_cltv),
  ('original_upb',m.original_upb)) AS v(feature,value)
)
SELECT entry_eligible,eligibility_reason,is_relief_refinance,feature,
 COUNT(*) AS loans,COUNT(value) AS observed_values,COUNT(*)-COUNT(value) AS missing_values,
 -- Stable loan order prevents parallel floating-point reduction drift across runs.
 AVG(value ORDER BY loan_id) AS mean,STDDEV_POP(value ORDER BY loan_id) AS standard_deviation,
 quantile_cont(value,0.1) AS p10,quantile_cont(value,0.5) AS median,
 quantile_cont(value,0.9) AS p90,MIN(value) AS minimum,MAX(value) AS maximum
FROM long_form GROUP BY ALL ORDER BY feature,entry_eligible,eligibility_reason,is_relief_refinance;
