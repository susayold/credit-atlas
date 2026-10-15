import copy
from types import SimpleNamespace
import pytest
from credit_atlas.monitor_reviews import MonitorReviews
from credit_atlas.reviews import ReviewConflict


@pytest.fixture
def store(tmp_path):
    class Suite:
        def view(self,identifier):
            if identifier!='suite-view-aaaaaaaaaaaa': raise ValueError('Unknown source')
            return {'view_id':identifier,'retail':{'freeze_id':'retail-freeze-aaaaaaaaaaaa'}}
    return MonitorReviews(SimpleNamespace(root=tmp_path,suite_views=Suite()))


def payload():
    return {'title':'QA review','owner':'Test analyst','judgement':'Evidence checked','hypothesis':'To validate','next_action':'Read source','status':'draft',
            'snapshot':{'domain':'P1','scope':'Saved benchmark','metrics':[{'name':'N','value':10}],'quality_metrics':[],'filters':{},'comparison_control':None,'evidence_refs':[{'kind':'suite','id':'suite-view-aaaaaaaaaaaa'}]}}


def test_capture_and_revision(store):
    p=payload();r=store.save(p);saved=copy.deepcopy(r['capture']);p['snapshot']['metrics'][0]['value']=999
    update={k:v for k,v in p.items() if k!='snapshot'};update.update(id=r['id'],revision=1,judgement='Revised',status='reviewed');r2=store.save(update)
    assert r2['revision']==2 and r2['capture']==saved and r2['capture']['snapshot']['metrics'][0]['value']==10
    history=store.report(r['id'])['history'];assert len(history)==2 and history[0]['judgement']=='Evidence checked'
    assert store.list('P1')['reviews'][0]['id']==r['id'] and saved['source_capture'][0]['verified_source_sha256']
    with pytest.raises(ReviewConflict): store.save(update)
    update['revision']=2;update['snapshot']=p['snapshot']
    with pytest.raises(ValueError,match='immutable'): store.save(update)
    assert len(store.report(r['id'])['history'])==2


@pytest.mark.parametrize('change',[{'domain':'P2'}, {'evidence_refs':[{'kind':'suite','id':'unknown'}]}, {'metrics':[{'value':float('nan')}]}, {'scope':'x'*48001}])
def test_invalid_context_rejected(store,change):
    p=payload();p['snapshot'].update(change)
    with pytest.raises(ValueError): store.save(p)
    assert store.list('P1')['reviews']==[]


def test_http_mutation_scope_conflict_and_export(store):
    import http.client
    import json
    import threading
    from http.server import ThreadingHTTPServer
    from credit_atlas.server import handler_for
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store.service))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(method,path,p=None,authorized=True):
        client=http.client.HTTPConnection('127.0.0.1',server.server_port)
        headers={'Content-Type':'application/json'}
        if authorized: headers.update(Origin=f'http://127.0.0.1:{server.server_port}',**{'X-CreditAtlas-Client':'local'})
        client.request(method,path,json.dumps(p) if p else None,headers)
        response=client.getresponse();status=response.status;data=json.loads(response.read());client.close();return status,data
    try:
        assert request('POST','/api/monitor-reviews',payload(),False)[0]==403
        code,r=request('POST','/api/monitor-reviews',payload());assert code==201
        update={k:v for k,v in payload().items() if k!='snapshot'};update.update(id=r['id'],revision=1)
        assert request('POST','/api/monitor-reviews',update)[0]==200
        assert request('POST','/api/monitor-reviews',update)[0]==409
        update.update(revision=2,snapshot=payload()['snapshot']);assert request('POST','/api/monitor-reviews',update)[0]==400
        code,report=request('GET','/api/monitor-review-report?id='+r['id']);assert code==200 and len(report['history'])==2
        assert request('GET','/api/monitor-reviews?domain=P1&unknown=1')[0]==400
    finally:
        server.shutdown();server.server_close();thread.join()
