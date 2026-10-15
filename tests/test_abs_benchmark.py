from pathlib import Path
from decimal import Decimal
import json, shutil
import pytest
from credit_atlas import abs_benchmark as b
from credit_atlas.abs_views import AbsViews

ROOT=Path(__file__).resolve().parents[1]


def test_calendar_full_vs_early_close():
    _,calendars,_=b.reference(ROOT)
    assert len(calendars[2025]['full_closes'])==12
    assert len(calendars[2026]['full_closes'])==11
    assert b.adjustment_date('2025-04-21',calendars)==('2025-04-16',['2025-04-17','2025-04-16'])
    assert b.adjustment_date('2026-04-06',calendars)==('2026-04-02',['2026-04-03','2026-04-02'])
    assert b.adjustment_date('2025-02-18',calendars)[0]=='2025-02-13'
    with pytest.raises(ValueError): b.adjustment_date('2025-01-02',calendars)


def test_administrator_type_units_and_duplicates():
    item={'effectiveDate':'2025-01-27','type':'SOFRAI','average30day':Decimal('4.33693')}
    assert b.rates_from({'refRates':[item]})['2025-01-27']['fraction_exact']=='0.0433693'
    for key,value in [('type','SOFR'),('average30day',True),('average30day','4.3'),('average30day',Decimal('NaN')),('average30day',Decimal('100'))]:
        with pytest.raises(ValueError): b.rates_from({'refRates':[{**item,key:value}]})
    with pytest.raises(ValueError): b.rates_from({'refRates':[item,item]})


@pytest.mark.parametrize('target',['sofrai.json','sifma-archive.html','sifma-current.html','acquisition-complete.json'])
def test_source_or_receipt_mutation_rejected(tmp_path,target):
    folder=tmp_path/'data/private/reference-rates'/b.SOURCE_ID
    shutil.copytree(ROOT/'data/private/reference-rates'/b.SOURCE_ID,folder)
    p=folder/target;p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError): b.reference(tmp_path)


def test_all_period_current_snapshot_comparison():
    views=AbsViews(ROOT);identifier=next(x['view_id'] for x in views.catalog()['views'] if x['status']=='verified')
    report=b.report(views,identifier,{})
    assert report['summary']=={'periods':20,'rate_matches':19,'coupon_matches':15,'base_interest_matches':20,'rate_precision_matches':20,'coupon_precision_matches':20,'fallback_periods':0}
    assert report['rows'][0]['adjustment_date']=='2025-01-27'
    assert not report['qualification']['historical_1500_publication_vintage_verified']
    selected=b.report(views,identifier,{'period':'2025-09-30'})
    assert len(selected['rows'])==1 and selected['rows'][0]['sofr_delta_exact']=='4E-18'
    assert selected['rows'][0]['rate_value_match'] is False
    for query in [{'period':'2030-01-31'},{'start':'2025-01-01'},{'view_id':'other'}]:
        with pytest.raises(ValueError): b.report(views,identifier,query)


def test_missing_rate_fallback_and_future_exclusion():
    _,calendars,_=b.reference(ROOT)
    p={'collection_end':'2025-01-31','accrual_start':'2025-01-29','distribution_date':'2025-02-18'}
    metrics=[{'collection_end':p['collection_end'],'section':'note_slot','slot':'A-2b','metric':k,'status':'VALUE','value':v,'file':'qa','sheet':'qa','row':1,'column':1,'raw_value':v}
             for k,v in [('sofr_rate','0.043'),('coupon','0.0463'),('beginning_balance','100000')]]
    rates={'2025-01-24':{'fraction_exact':'0.043','percent_exact':'4.3','revision_indicator':''},'2025-01-28':{'fraction_exact':'0.05','percent_exact':'5','revision_indicator':''}}
    r=b.compare_period(p,metrics,rates,calendars)
    assert r['fallback_used'] and r['administrator_rate_date']=='2025-01-24' and r['coupon_match']
    metrics[0]['value']='0.04300001';r=b.compare_period(p,metrics,rates,calendars)
    assert not r['rate_precision_match']
    with pytest.raises(ValueError): b.compare_period(p,metrics,{'2025-01-28':rates['2025-01-28']},calendars)
