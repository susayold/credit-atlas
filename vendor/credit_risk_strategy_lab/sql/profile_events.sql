-- Diagnostic counts only. Not horizon labels, incidence rates or loss targets.
WITH rows AS (
 SELECT *, TRY_CAST(delinquency AS INTEGER) BETWEEN 3 AND 99 AS d3,
  ROW_NUMBER() OVER (PARTITION BY loan_id ORDER BY period, _source_line) AS seq
 FROM performance
)
SELECT loan_id, COUNT(*) AS observed_rows,
 MIN(period) AS first_period, MAX(period) AS last_period,
 MAX(CASE WHEN seq=1 THEN TRY_CAST(loan_age AS INTEGER) END) AS first_observed_age,
 MAX(CASE WHEN seq=1 THEN delinquency END) AS first_status,
 MIN(period) FILTER (WHERE d3) AS first_observed_d3_period,
 COUNT(*) FILTER (WHERE d3) AS d3_state_rows,
 BOOL_OR(delinquency='RA') AS ever_reo,
 COUNT(*) FILTER (WHERE TRIM(zero_balance_code)<>'') AS terminal_rows,
 MAX(zero_balance_code) FILTER (WHERE TRIM(zero_balance_code)<>'') AS terminal_code_if_unique,
 COUNT(*) FILTER (WHERE TRIM(actual_loss)<>'') AS populated_loss_rows,
 COUNT(*) FILTER (WHERE TRIM(actual_loss)<>'' AND zero_balance_code NOT IN ('02','03','09','15')) AS loss_rows_unexpected_terminal,
 COUNT(*) FILTER (WHERE TRIM(actual_loss)<>'' AND TRIM(defect_settlement_date)<>'') AS loss_rows_with_defect,
 COUNT(*) FILTER (WHERE zero_balance_code IN ('02','03','09','15') AND TRIM(actual_loss)='') AS eligible_code_without_loss_rows
FROM rows GROUP BY loan_id;
