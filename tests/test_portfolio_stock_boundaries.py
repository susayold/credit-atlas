"""Zero/missing/terminal balances must retain distinct stock denominators."""
from pathlib import Path
from decimal import Decimal
import duckdb
import pytest

def test_zero_active_balance_is_not_missing_or_terminal():
    with duckdb.connect() as db:
        db.execute('CREATE TABLE fact_loan_month(loan_id VARCHAR,period DATE,current_upb DECIMAL(18,2),delinquency_state VARCHAR,terminal_type VARCHAR)')
        db.execute("""INSERT INTO fact_loan_month VALUES
         ('known','2020-01-01',100,'CURRENT',NULL),
         ('zero','2020-01-01',0,'D3PLUS',NULL),
         ('missing','2020-01-01',NULL,'D3PLUS',NULL),
         ('exit','2020-01-01',0,'CURRENT','PREPAID_OR_MATURED')""")
        result=db.execute((Path(__file__).resolve().parents[1]/'vendor/credit_risk_strategy_lab/sql/portfolio_monthly.sql').read_text())
        names=[c[0] for c in result.description];row=dict(zip(names,result.fetchone()))
        assert row['reported_loans']==4 and row['active_loans']==3 and row['terminal_loans']==1
        assert row['state_usable_active_loans']==3 and row['missing_active_balance_loans']==1
        assert row['d3_active_loans']==2 and row['d3_active_upb']==Decimal('0')
        assert row['observed_active_upb']==Decimal('100') and row['state_usable_active_upb']==Decimal('100')
        assert row['d3_count_share']==pytest.approx(2/3) and row['d3_balance_share']==0

def test_zero_or_missing_balance_denominator_is_unavailable():
    with duckdb.connect() as db:
        db.execute('CREATE TABLE fact_loan_month(period DATE,current_upb DECIMAL(18,2),delinquency_state VARCHAR,terminal_type VARCHAR)')
        db.execute("INSERT INTO fact_loan_month VALUES ('2020-01-01',0,'D3PLUS',NULL),('2020-02-01',NULL,'CURRENT',NULL)")
        result=db.execute((Path(__file__).resolve().parents[1]/'vendor/credit_risk_strategy_lab/sql/portfolio_monthly.sql').read_text()).fetchall()
        assert all(row[-1] is None for row in result)
