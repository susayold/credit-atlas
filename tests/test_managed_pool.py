from pathlib import Path
from decimal import Decimal
import pytest
from credit_atlas import managed_pool as m
from credit_atlas.pool_history import verified_source,workbook

ROOT=Path(__file__).resolve().parents[1]
def sheets():
    folder,_=verified_source(ROOT)
    return workbook(folder/'ManagedPool-Retail.xlsx')

def test_real_source_units_dates_sign_and_checks():
    r=m.report(ROOT,{})
    assert r['field_count']==30 and len(r['periods'])==7
    assert len([c for p in r['periods'] for c in p['checks']])==105
    assert all(c['status']=='PASS' for p in r['periods'] for c in p['checks'])
    c,d,e=r['periods'][:3]
    assert [p['end_date'] for p in (c,d,e)]==['2026-06-30','2025-06-30','2025-12-31']
    assert c['values']['receivables']['unit']=='USD_thousands'
    assert Decimal(c['values']['recoveries_signed']['value_exact'])<0
    assert c['derived_ratios']['period_net_loss_fraction']['annualized'] is False
    assert c['derived_ratios']['period_net_loss_fraction']['flow_duration_qualified'] is False
    assert e['derived_ratios']['period_net_loss_fraction']['flow_duration_qualified'] is True
    assert Decimal(c['values']['reported_net_loss_rate']['value_exact'])>Decimal(c['derived_ratios']['period_net_loss_fraction']['value_exact'])
    assert r['periods'][-2]['values']['reported_count_rate_121_plus']['value_exact']=='0'

def test_missing_input_not_zero_filled():
    s=sheets();cells=next(iter(s.values()));cells['C17']['value']=None
    p=m.project(s)[0]
    assert p['values']['gross_chargeoffs']['status']=='SOURCE_BLANK'
    assert next(c for c in p['checks'] if c['name']=='net_loss_bridge')['status']=='UNAVAILABLE'

def test_inconsistent_total_exposed():
    s=sheets();next(iter(s.values()))['C35']['value']='1'
    p=m.project(s)[0]
    assert next(c for c in p['checks'] if c['name']=='delinq_count_sum')['status']=='DIFFERENCE'

@pytest.mark.parametrize('cell,value',[('C18','5'),('C5','-1'),('C42','NaN'),('C42','2'),('C26','1'),('C4','2024')])
def test_bad_sign_rate_date_rejected(cell,value):
    s=sheets();next(iter(s.values()))[cell]['value']=value
    with pytest.raises(ValueError):m.project(s)

def test_filter_scope_not_silently_ignored():
    with pytest.raises(ValueError):m.report(ROOT,{'period':'2026-06-30'})
