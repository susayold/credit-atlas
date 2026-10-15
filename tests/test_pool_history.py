from pathlib import Path
import copy,shutil
import pytest
from credit_atlas import pool_history as p
ROOT=Path(__file__).resolve().parents[1]


def test_population_blank_and_real_zero():
    r=p.report(ROOT,{})
    assert r['inventory']['cohorts']==21 and r['inventory']['populated_age_cells']==1998
    assert r['inventory']['blank_age_cells']==1362 and len(r['rows'])==52
    assert any(x['status']=='SOURCE_BLANK' and x['value_exact'] is None for x in r['rows'])
    assert not any(r['qualification'].values())
    s=p.report(ROOT,{'metric':'loss','deal':'WOART 2026-B'})
    zero=p.report(ROOT,{'metric':'loss','deal':'WOART 2021-B'})
    assert any(x['value_exact'] is not None and float(x['value_exact'])==0 for x in zero['rows'])
    assert next(x for x in s['cohort_summary'] if x['deal']=='WOART 2026-B')['age12_value_exact'] is None


@pytest.mark.parametrize('query',[{'metric':'PD'},{'deal':'WOART 2020-A'},{'period':'2026-08-31'}])
def test_unsupported_filters(query):
    with pytest.raises(ValueError):p.report(ROOT,query)


@pytest.mark.parametrize('filename',['StaticPool-WOART.xlsx','ManagedPool-Retail.xlsx','acquisition-complete.json'])
def test_source_mutation_rejected(tmp_path,filename):
    folder=tmp_path/'data/private/structured'/p.SOURCE_ID
    shutil.copytree(ROOT/'data/private/structured'/p.SOURCE_ID,folder)
    path=folder/filename;path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):p.report(tmp_path,{})


@pytest.mark.parametrize('value',['NaN','Infinity','2'])
def test_invalid_fraction(value):
    folder,_=p.verified_source(ROOT);sheets=p.workbook(folder/'StaticPool-WOART.xlsx')
    sheets['Cumulative Losses']['B4']['value']=value
    with pytest.raises(ValueError):p.curves(sheets)


def test_duplicate_cohort_and_age_rejected():
    folder,_=p.verified_source(ROOT);sheets=p.workbook(folder/'StaticPool-WOART.xlsx')
    sheets['Cumulative Losses']['C3']['value']=sheets['Cumulative Losses']['B3']['value']
    with pytest.raises(ValueError):p.curves(sheets)
