import json
from datetime import date
from pathlib import Path
import duckdb
import pytest
from crsl.labels import create_labels

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'configs/cohort.json').read_text())

def evaluate(changes=None,months=13,entry_age=0,entry_state='CURRENT',config=None):
    changes=changes or {}
    with duckdb.connect() as db:
        db.execute('CREATE TABLE dim_loan(loan_id VARCHAR,original_upb DECIMAL(18,2),origination_year INTEGER,is_relief_refinance BOOLEAN,first_payment_date DATE)')
        db.execute("INSERT INTO dim_loan VALUES ('fixture',100000,2012,false,DATE '2012-02-01')")
        db.execute('CREATE TABLE fact_loan_month(loan_id VARCHAR,period DATE,loan_age INTEGER,delinquency_state VARCHAR,modification VARCHAR,terminal_type VARCHAR)')
        for index in range(months):
            if changes.get(index)=='gap': continue
            year=2012+index//12; month=1+index%12
            state,terminal=changes.get(index,(entry_state if index==0 else 'CURRENT',None))
            db.execute('INSERT INTO fact_loan_month VALUES (?,?,?,?,?,?)',
                ['fixture',date(year,month,1),entry_age+index,state,None,terminal])
        create_labels(db,ROOT/'sql',config or CONFIG)
        row=db.execute('SELECT target,outcome,eligibility_reason FROM labels').fetchone()
        return row

def test_complete_horizon_negative(): assert evaluate()==(0,'complete_no_event','eligible')
def test_short_history_not_negative(): assert evaluate(months=6)==(None,'administrative_censoring','eligible')
def test_d3_at_12_included(): assert evaluate({12:('D3PLUS',None)})[0]==1
def test_d3_at_13_excluded(): assert evaluate({13:('D3PLUS',None)},months=14)[0]==0
def test_prevalent_excluded(): assert evaluate(entry_state='D3PLUS')[2]=='severe_at_entry'
def test_prepaid_negative_under_declared_estimand(): assert evaluate({5:('CURRENT','PREPAID_OR_MATURED')},months=6)==(0,'prepayment','eligible')
def test_credit_exit_not_negative(): assert evaluate({5:('CURRENT','CREDIT_TERMINATION')},months=6)[1]=='other_exit'
def test_whole_loan_sale_not_negative(): assert evaluate({5:('CURRENT','OTHER_TERMINATION')},months=6)[0] is None
def test_unknown_before_positive_unavailable(): assert evaluate({2:('UNKNOWN',None),4:('D3PLUS',None)})[1]=='unknown_followup'
def test_unknown_after_positive_does_not_erase_known_event(): assert evaluate({4:('D3PLUS',None),5:('UNKNOWN',None)})[0]==1
def test_gap_before_positive_unavailable(): assert evaluate({2:'gap',4:('D3PLUS',None)})[1]=='gap_followup'
def test_gap_after_positive_does_not_erase_event(): assert evaluate({4:('D3PLUS',None),5:'gap'})[0]==1
def test_same_month_event_priority(): assert evaluate({4:('D3PLUS','PREPAID_OR_MATURED')},months=5)[0]==1
def test_reo_not_numeric_d3(): assert evaluate({4:('REO',None)})[1]=='other_exit'
def test_age_mismatch_excluded(): assert evaluate(entry_age=2)[2]=='entry_age_mismatch'
def test_post_terminal_rows_fail():
    with pytest.raises(ValueError,match='post-terminal'): evaluate({4:('CURRENT','PREPAID_OR_MATURED')})
def test_unsupported_semantic_config_fails():
    with pytest.raises(ValueError,match='Unsupported'): evaluate(config={**CONFIG,'same_month_d3_and_exit':'prepay_first'})
def test_injected_horizon_fails():
    with pytest.raises(ValueError,match='Invalid'): evaluate(config={**CONFIG,'horizon_months':'12; DROP TABLE dim_loan'})
