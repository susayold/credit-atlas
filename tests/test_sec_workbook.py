import pytest
from credit_atlas.sec_workbook import document
from tests.test_sec_financials import acquired
from tests.test_sec_views import view


def test_server_capture_and_no_fabricated_actuals(view):
    _,_,receipt,views=view
    d=document(views,{'view_id':receipt['view_id'],'cik':'0000320193','asof':'2026-02-01','years':'3','interest_concept':'InterestExpense'})
    assert d['trend']['filters']['asof']==d['coverage']['filters']['asof']=='2026-02-01'
    assert d['coverage']['filters']['interest_concept']=='InterestExpense'
    assert d['trend']['source_id']==d['coverage']['source_id']
    assert len(d['trend']['method_source_sha256'])==64 and d['visibility']=='private'
    with pytest.raises(ValueError):document(views,{'view_id':receipt['view_id'],'asof':'1900-01-01'})


@pytest.mark.parametrize('query',[{}, {'view_id':'bad','actuals':{}}, {'view_id':'bad','path':'D:/out.xlsx'}, {'view_id':1}, {'view_id':'bad','years':'100'}, {'view_id':'bad','interest_concept':'InterestPaid'}])
def test_filter_only_export_contract(view,query):
    with pytest.raises(ValueError):document(view[3],query)
