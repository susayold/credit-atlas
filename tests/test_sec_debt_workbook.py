import pytest
from credit_atlas.sec_debt_workbook import document
from tests.test_sec_financials import acquired
from tests.test_sec_views import view


def test_server_capture_partial_schedule_and_no_fabrication(view):
    _,_,receipt,views=view
    r=document(views,{'view_id':receipt['view_id'],'asof':'2026-02-01','debt_scope':'debt_and_capital_lease'})
    assert r['filters']['debt_scope']=='debt_and_capital_lease' and r['statement']['cik']=='0000320193'
    assert r['summary']['disclosed_schedule_total_exact'] is None
    with pytest.raises(ValueError):document(views,{'view_id':receipt['view_id'],'asof':'1900-01-01'})


@pytest.mark.parametrize('query',[{}, {'view_id':'bad','actuals':[]},{'view_id':'bad','output':'D:/x.xlsx'},{'view_id':1},{'view_id':'bad','debt_scope':'all'},{'view_id':'bad','accession':'../private'}])
def test_bounded_source_filters_only(view,query):
    with pytest.raises(ValueError):document(view[3],query)
