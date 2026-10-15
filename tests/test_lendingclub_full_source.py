from pathlib import Path
import pytest
from credit_atlas import lendingclub_full_source as d
ROOT=Path(__file__).resolve().parents[1]

def test_raw_records_missing_dates_and_active_statuses_are_separate():
    r=d.report(ROOT,{})
    assert r['source_records']==2260701 and r['selected_records']==2260668
    assert r['source_records_with_unavailable_date']==33
    assert r['whole_source_category_counts']['Current']==878317
    assert r['approval_rate'] is None and r['fixed_horizon_pd'] is None
    assert not r['issuer_redistribution_rights_verified'] and len(r['missingness'])==151

def test_rejected_grain_and_missing_scores_are_not_repayment_labels():
    r=d.report(ROOT,{'kind':'rejected'})
    assert r['source_records']==27648741 and r['grain']=='application day'
    assert next(x for x in r['missingness'] if x['field']=='Risk_Score')['missing']==18497630
    assert not r['rejected_repayment_labels_available'] and r['category_column']=='Policy Code'

def test_category_scope_and_no_dated_records_keep_global_quality():
    r=d.report(ROOT,{'category':'Current','from':'2018-01'})
    assert r['selected_records']<r['window_all_category_records']
    assert all(x['source_category']=='Current' for x in r['selected_month_category_rows'])
    missing=d.report(ROOT,{'category':'__missing__'})
    assert missing['selected_records']==0 and missing['source_records_with_missing_category']==33
    assert missing['source_records_with_unavailable_date']==33

@pytest.mark.parametrize('q',[{'kind':'applications'},{'from':'2006-01'},{'to':'2019-01'},{'category':'Fully Paid','kind':'rejected'},{'from':'2018-12','to':'2018-01'},{'kind':2},{'metric':'PD'}])
def test_invalid_scope_rejected(q):
    with pytest.raises(ValueError):d.report(ROOT,q)

@pytest.mark.parametrize('name',['acquisition-complete.json','accepted_2007_to_2018Q4.csv.gz','profile.json'])
def test_integrity_tampering_fails_closed(monkeypatch,name):
    original=d.sha256
    monkeypatch.setattr(d,'sha256',lambda p:'changed' if p.name==name else original(p))
    with pytest.raises(ValueError,match='changed'):d.report(ROOT,{})
