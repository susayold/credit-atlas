-- One-row integrity and coverage summary. Technical qualification, not portfolio KPIs.
SELECT
 (SELECT COUNT(*) FROM origination) AS origination_rows,
 (SELECT COUNT(DISTINCT loan_id) FROM origination) AS origination_loans,
 (SELECT COUNT(*) FROM performance) AS performance_rows,
 (SELECT COUNT(DISTINCT loan_id) FROM performance) AS performance_loans,
 (SELECT COUNT(*) FROM (SELECT loan_id FROM origination GROUP BY loan_id HAVING COUNT(*) > 1)) AS duplicate_origination_keys,
 (SELECT COUNT(*) FROM (SELECT loan_id, period FROM performance GROUP BY loan_id, period HAVING COUNT(*) > 1)) AS duplicate_monthly_keys,
 (SELECT COUNT(*) FROM performance p WHERE NOT EXISTS (SELECT 1 FROM origination o WHERE o.loan_id=p.loan_id)) AS orphan_performance_rows,
 (SELECT COUNT(*) FROM origination o WHERE NOT EXISTS (SELECT 1 FROM performance p WHERE p.loan_id=o.loan_id)) AS loans_without_performance,
 (SELECT MIN(period) FROM performance) AS first_period,
 (SELECT MAX(period) FROM performance) AS last_period,
 (SELECT COUNT(*) FROM performance WHERE delinquency='XX') AS unknown_status_rows,
 (SELECT COUNT(*) FROM performance WHERE delinquency='RA') AS reo_status_rows,
 (SELECT COUNT(*) FROM performance WHERE TRY_CAST(delinquency AS INTEGER)>=3) AS d3plus_rows_not_incident_events,
 (SELECT COUNT(*) FROM performance WHERE NULLIF(TRIM(actual_loss),'') IS NOT NULL) AS populated_loss_rows_not_resolved_loans;

