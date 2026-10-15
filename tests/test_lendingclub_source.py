from pathlib import Path
from decimal import Decimal
import pytest
from credit_atlas import lendingclub_source as d
ROOT=Path(__file__).resolve().parents[1]

def test_publisher_source_and_duplicate_target_are_explicit():
    r=d.report(ROOT,{})
    assert r['whole_source_records']==1055054 and len(r['columns'])==90
    assert r['window_source_status_counts']=={'Charged Off':216625,'Fully Paid':838429}
    assert r['source_status_encoded_cross_counts']==[{'source_loan_status':'Charged Off','encoded_LoanStatus_raw':'0','records':216625},{'source_loan_status':'Fully Paid','encoded_LoanStatus_raw':'1','records':838429}]
    assert {'loan_status','LoanStatus','id'}<=set(r['candidate_model_exclusions'])
    assert not any(r['field_readiness'].values()) and not r['model_training_performed']

def test_status_filter_does_not_change_share_denominator_or_whole_source_quality():
    a=d.report(ROOT,{'from':'2020-01','status':'all'})
    b=d.report(ROOT,{'from':'2020-01','status':'Charged Off','field':'dti'})
    assert b['selected_records']<a['selected_records'] and b['window_all_status_records']==a['window_all_status_records']
    assert b['window_terminal_charged_off_share_decimal50']==a['window_terminal_charged_off_share_decimal50']
    assert Decimal(b['window_terminal_charged_off_share_decimal50'])<1
    assert b['selected_field']['missing']==1204 and b['selected_field']['numeric_profile']['negative']==2
    assert b['quality_scope']=='whole_source_not_filtered_by_month_or_status'

def test_absent_source_status_stays_null_and_non_numeric_profile_unavailable():
    r=d.report(ROOT,{'field':'purpose'})
    assert any(x['source_charged_off_records'] is None for x in r['timeline'])
    assert r['selected_field']['numeric_profile'] is None

@pytest.mark.parametrize('q',[{'from':'2015-12'},{'to':'2020-07'},{'from':'2020-01','to':'2019-01'},{'status':'Current'},{'field':'PD'},{'field':2},{'from':'2020-13'},{'application_type':'Joint App'}])
def test_invalid_scope_rejected(q):
    with pytest.raises(ValueError):d.report(ROOT,q)

@pytest.mark.parametrize('name',['acquisition-complete.json','LENDINGCLUB2016Q12020Q2.csv','profile.json'])
def test_tampering_fails_closed(monkeypatch,name):
    original=d.sha256
    monkeypatch.setattr(d,'sha256',lambda p:'changed' if p.name==name else original(p))
    with pytest.raises(ValueError,match='changed'):d.report(ROOT,{})
