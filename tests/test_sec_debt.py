from copy import deepcopy
from decimal import Decimal
import pytest
from credit_atlas.sec_debt import CONCEPTS,field,summarize,report
from tests.test_sec_trends import annual
from tests.test_sec_financials import acquired
from tests.test_sec_views import view


def fact(s,value='10'):
    return {'cik':s['cik'],'accession':s['accession'],'form':s['form'],'filed_date':s['filing_date'],'end_date':s['report_date'],'start_date':None,'taxonomy':'us-gaap','unit':'USD','concept':CONCEPTS['debt_only']['year_1'],'value_exact':value,'source_ordinal':0}


def test_duplicate_and_conflict_and_no_alias():
    s=annual();a=fact(s)
    assert field(s,[a,deepcopy(a)],a['concept'])['status']=='supported'
    assert field(s,[a,fact(s,'11')],a['concept'])['status']=='ambiguous'
    assert field(s,[a],CONCEPTS['debt_and_capital_lease']['year_1'])['status']=='missing'


@pytest.mark.parametrize('key,value',[('unit','EUR'),('start_date','2025-01-01'),('end_date','2024-12-31'),('filed_date','2026-02-02'),('accession','0001193125-25-000002'),('taxonomy','custom'),('form','10-K/A'),('cik','0000789019')])
def test_exact_filing_instant_only(key,value):
    s=annual();a=fact(s);a[key]=value
    assert field(s,[a],CONCEPTS['debt_only']['year_1'])['status']=='missing'


def buckets(values):
    return [{'bucket':key,'field':{'status':'missing' if v is None else 'supported','value_exact':str(v) if v is not None else None}} for key,v in zip(CONCEPTS['debt_only'],values)]


def test_complete_partial_zero_and_negative_profiles():
    bs=buckets([10,0,20,0,0,70]);r=summarize(bs)
    assert r['disclosed_schedule_total_exact']=='100' and Decimal(r['first_three_years_share_exact'])==Decimal('.3')
    assert sum(Decimal(b['share_of_disclosed_schedule_exact']) for b in bs)==1
    for values,status,total in [([10,None,20,0,0,70],'PARTIAL_DISCLOSED_SCHEDULE',None),([0]*6,'COMPLETE_ZERO_SCHEDULE','0'),([-10,0,20,0,0,70],'INVALID_NEGATIVE_BUCKET',None)]:
        bs=buckets(values);r=summarize(bs);assert r['status']==status and r['disclosed_schedule_total_exact']==total
        assert r['first_three_years_share_exact'] is None and all(b['share_of_disclosed_schedule_exact'] is None for b in bs)


def test_verified_scope_cutoff_and_lineage(view):
    _,_,receipt,views=view
    r=report(views,receipt['view_id'],{'asof':'2026-02-01','debt_scope':'debt_only'})
    assert r['statement']['cik']=='0000320193' and len(r['buckets'])==6
    assert r['summary']['status']=='PARTIAL_DISCLOSED_SCHEDULE' and not any(r['qualification'].values())
    assert len(r['source_capture']['facts_sha256'])==64 and len(r['method_source_sha256'])==64
    assert report(views,receipt['view_id'],{'asof':'1900-01-01'})['statement'] is None


@pytest.mark.parametrize('query',[{'debt_scope':'all'}, {'years':'5'}, {'asof':'2026-02-30'}, {'accession':'../private'}, {'cik':'unknown'}])
def test_invalid_filters(view,query):
    with pytest.raises(ValueError):report(view[3],view[2]['view_id'],query)
