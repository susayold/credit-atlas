-- Each loan is one record. No filling gaps or reconstructing pre-acquisition history.
WITH ordered AS (
 SELECT loan_id, strptime(period, '%Y%m') AS reporting_month,
  LAG(strptime(period, '%Y%m')) OVER (PARTITION BY loan_id ORDER BY period, _source_line) AS previous_month
 FROM performance
)
SELECT loan_id, COUNT(*) AS rows_observed,
 COUNT(DISTINCT reporting_month) AS months_observed,
 MIN(reporting_month)::DATE AS first_month, MAX(reporting_month)::DATE AS last_month,
 COUNT(*) FILTER (WHERE date_diff('month', previous_month, reporting_month)>1) AS gap_pairs,
 COALESCE(SUM(GREATEST(date_diff('month', previous_month, reporting_month)-1,0)),0)::BIGINT AS missing_months,
 COUNT(*) FILTER (WHERE date_diff('month', previous_month, reporting_month)=0) AS duplicate_months
FROM ordered GROUP BY loan_id;

