-- Release 47 guide pp12-14. Add signed recoveries; do not subtract them again.
-- Excludes cumulative/current modification and bankruptcy costs from actual_loss formula.
SELECT loan_id, period, zero_balance_code, zero_balance_date, defect_settlement_date,
 actual_loss, removal_upb, net_sales_proceeds, delinquent_accrued_interest,
 total_expenses, mi_recoveries, non_mi_recoveries,
 actual_loss - (removal_upb + net_sales_proceeds + delinquent_accrued_interest
   + total_expenses + mi_recoveries + non_mi_recoveries) AS loss_residual,
 total_expenses-(legal_costs+maintenance_costs+taxes_insurance+misc_expenses) AS expense_residual,
 CASE
  WHEN actual_loss IS NOT NULL THEN 'reported'
  WHEN defect_settlement_date IS NOT NULL THEN 'withheld_defect'
  WHEN zero_balance_date >= DATE '{recent_start}' THEN 'recent_disposition'
  ELSE 'unexplained_missing' END AS availability_reason
FROM fact_loan_month WHERE zero_balance_code IN ('02','03','09','15');
