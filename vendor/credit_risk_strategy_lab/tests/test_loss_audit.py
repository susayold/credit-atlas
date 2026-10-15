from pathlib import Path
import duckdb
from crsl.audit import loss_checks

def test_signed_recoveries_and_null_losses():
    with duckdb.connect() as db:
        db.execute('''CREATE TABLE fact_loan_month(loan_id VARCHAR,period DATE,zero_balance_code VARCHAR,
          zero_balance_date DATE,defect_settlement_date DATE,actual_loss DECIMAL(18,2),
          removal_upb DECIMAL(18,2),net_sales_proceeds DECIMAL(18,2),delinquent_accrued_interest DECIMAL(18,2),
          total_expenses DECIMAL(18,2),mi_recoveries DECIMAL(18,2),non_mi_recoveries DECIMAL(18,2),
          legal_costs DECIMAL(18,2),maintenance_costs DECIMAL(18,2),taxes_insurance DECIMAL(18,2),misc_expenses DECIMAL(18,2))''')
        db.execute("""INSERT INTO fact_loan_month VALUES
          ('synthetic-a','2020-01-01','09','2020-01-01',NULL,10000,100000,-90000,1000,2000,-2000,-1000,500,500,500,500),
          ('synthetic-b','2020-01-01','09','2020-01-01','2021-01-01',NULL,100000,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),
          ('synthetic-c','2026-02-01','09','2026-02-01',NULL,NULL,100000,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)""")
        report=loss_checks(db,Path(__file__).resolve().parents[1]/'sql')
        assert report['loss_reconciliation'][0]['loss_mismatch']==0
        assert report['loss_reconciliation'][0]['expense_mismatch']==0
        assert {r['availability_reason'] for r in report['loss_availability']}=={'reported','withheld_defect','recent_disposition'}
