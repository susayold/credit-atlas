from decimal import Decimal
import copy
import pytest
from credit_atlas.sec_coverage import field,ratio,report
from tests.test_sec_financials import acquired
from tests.test_sec_views import view


S={'cik':'0000320193','accession':'0001193125-26-000001','form':'10-K','report_date':'2025-12-31','filing_date':'2026-02-01'}
def fact(tag='InterestExpenseNonoperating',value='10'):
    return {'cik':S['cik'],'accession':S['accession'],'taxonomy':'us-gaap','concept':tag,'unit':'USD','start_date':'2025-01-01','end_date':S['report_date'],'filed_date':S['filing_date'],'form':'10-K','value_exact':value,'source_ordinal':0}


def test_explicit_concept_duplicates_and_ambiguity():
    row=fact();duplicate={**row,'source_ordinal':1}
    f=field(S,[row,duplicate],'InterestExpenseNonoperating')
    assert f['status']=='supported' and len(f['evidence'])==2
    assert field(S,[row,{**duplicate,'value_exact':'11'}],'InterestExpenseNonoperating')['status']=='ambiguous'
    assert field(S,[fact('InterestExpense')],'InterestExpenseNonoperating')['status']=='missing'
    assert field(S,[fact('InterestPaid')],'InterestExpenseNonoperating')['value_exact'] is None


@pytest.mark.parametrize('key,value',[('unit','EUR'),('accession','other'),('end_date','2024-12-31'),('filed_date','2026-02-02'),('start_date','2025-10-01'),('taxonomy','custom')])
def test_wrong_identity_period_or_unit_not_used(key,value):
    row=fact();row[key]=value
    assert field(S,[row],'InterestExpenseNonoperating')['status']=='missing'


def test_negative_numerator_zero_denominator_and_alignment():
    n=field(S,[fact('OperatingIncomeLoss','-20')],'OperatingIncomeLoss')
    d=field(S,[fact()],'InterestExpenseNonoperating')
    assert Decimal(ratio(n,d)['value_exact'])==Decimal('-2')
    for value in ['0','-10']:
        d['value_exact']=value;assert ratio(n,d)['status']=='nonpositive_interest_expense' and ratio(n,d)['value_exact'] is None
    d['value_exact']='10';d['start_date']='2025-01-02';assert ratio(n,d)['status']=='period_mismatch'
    n['status']='ambiguous';assert ratio(n,d)['status']=='missing_or_ambiguous_input'


def test_verified_report_preserves_unavailable_and_lineage(view):
    _,_,r,views=view
    output=report(views,r['view_id'],{'asof':'2026-02-01','years':'3'})
    assert output['support']['report_periods']==1 and output['support']['supported_operating_income_coverage']==0
    assert not any(output['qualification'].values())
    assert len(output['source_capture']['facts_sha256'])==64
    assert report(views,r['view_id'],{'asof':'2026-01-31'})['periods']==[]


@pytest.mark.parametrize('query',[{'interest_concept':'InterestPaid'},{'years':'100'},{'asof':'2026-02-30'},{'pd':'1'}])
def test_bad_coverage_filters(view,query):
    with pytest.raises(ValueError):report(view[3],view[2]['view_id'],query)
