from types import SimpleNamespace
import pytest
from credit_atlas.finding_reports import report
from credit_atlas.reviews import Reviews

def fixture(tmp_path):
    reviews=Reviews(tmp_path/'reviews.sqlite3');payload={'title':'QA','body':'Research only','view':'portfolio','filters':{'segment':'relief','basis':'count','from':'2020-01','to':'2020-03'},'evidence_refs':['portfolio_monthly']}
    first=reviews.save('case-A',payload)
    second=reviews.save('case-A',{**payload,'body':'Updated','status':'reviewed','revision':1},first['id'])
    calls=[]
    def aggregates(run,filters):calls.append(filters);return {'case_id':run,'filter_context':dict(filters),'scope_notes':{'loss':'Whole-sample'}}
    service=SimpleNamespace(case=lambda _: {'manifest':{}},reviews=reviews,report=aggregates,evidence=lambda run:{'case_id':run})
    return service,first,second,calls

def test_historical_export_preserves_text_filters_and_history(tmp_path):
    service,first,second,calls=fixture(tmp_path)
    old=report(service,{'run':'case-A','id':first['id'],'revision':'1'})
    assert old['finding']==first and len(old['history'])==1 and calls[-1]==first['filters']
    new=report(service,{'run':'case-A','id':first['id']})
    assert new['finding']==second and len(new['history'])==2
    assert new['bank_credit_approval'] is False and new['authenticated_reviewer_identity'] is False
    assert new['aggregate_evidence']['filter_context']==first['filters']
    assert service.reviews.history('case-A',first['id'])==new['history']

@pytest.mark.parametrize('revision',['0','01','-1','1.0','true','9999999999'])
def test_invalid_revision(tmp_path,revision):
    service,first,_,_=fixture(tmp_path)
    with pytest.raises(ValueError):report(service,{'run':'case-A','id':first['id'],'revision':revision})

def test_foreign_case_and_missing_revision(tmp_path):
    service,first,_,_=fixture(tmp_path)
    with pytest.raises(KeyError):report(service,{'run':'case-B','id':first['id']})
    with pytest.raises(KeyError):report(service,{'run':'case-A','id':first['id'],'revision':'3'})

def test_scope_mismatch_rejected(tmp_path):
    service,first,_,_=fixture(tmp_path)
    service.report=lambda *args:{'case_id':'case-B'}
    with pytest.raises(ValueError,match='scope mismatch'):report(service,{'run':'case-A','id':first['id']})
