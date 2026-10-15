import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import pytest
from credit_atlas.portfolio_reviews import PortfolioReviews
from credit_atlas.exposure_views import ExposureViews
from credit_atlas.exposure_scenario_views import ExposureScenarioViews
from credit_atlas.exposure_ecl_views import ExposureEclViews
from credit_atlas.exposure_tail_views import ExposureTailViews
from credit_atlas.reviews import ReviewConflict
from credit_atlas.server import handler_for
from tests.test_exposure_tail import frozen


@pytest.fixture
def fixture(tmp_path):
    receipt=frozen(tmp_path)
    service=SimpleNamespace(root=tmp_path,exposure_views=ExposureViews(tmp_path),exposure_scenario_views=ExposureScenarioViews(tmp_path),
        exposure_ecl_views=ExposureEclViews(tmp_path),exposure_tail_views=ExposureTailViews(tmp_path))
    service.portfolio_reviews=PortfolioReviews(service,tmp_path/'reviews.sqlite3')
    payload={'source_import_id':receipt['source_import_id'],'title':'Research tail review','rationale':'Recovery and correlation are declared; no capital approval.',
        'owner':'Research analyst','expires_on':'2100-01-01','status':'draft','currency':'USD','assumptions_acknowledged':False,
        'evidence_refs':[{'kind':'tail','id':receipt['tail_id']}]}
    return service,payload


def test_versions_source_binding_and_no_qualification(fixture):
    service,p=fixture; reviews=service.portfolio_reviews; first=reviews.save(p)
    assert first['revision']==1 and not first['qualification']['capital_approved']
    second=reviews.save({**p,'id':first['id'],'revision':1,'status':'reviewed','assumptions_acknowledged':True})
    assert second['revision']==2 and reviews.report(p['source_import_id'],first['id'],1)['status']=='draft'
    assert reviews.report(p['source_import_id'],first['id'])['status']=='reviewed'
    assert reviews.list(p['source_import_id'])['packages'][0]['evidence_current']
    with pytest.raises(ReviewConflict): reviews.save({**p,'id':first['id'],'revision':1})
    with pytest.raises(KeyError): reviews.report('exposure-import-000000000000',first['id'])


@pytest.mark.parametrize('change',[{'status':'reviewed'},{'status':'reviewed','assumptions_acknowledged':True,'expires_on':'2000-01-01'},
    {'evidence_refs':[{'kind':'model','id':'x'}]},{'currency':'GBP'},{'owner':''},{'override_el':'0'}])
def test_rejects_unqualified_or_unsupported_review(fixture,change):
    service,p=fixture
    with pytest.raises((ValueError,KeyError)): service.portfolio_reviews.save({**p,**change})


def test_stale_evidence_prevents_export_but_preserves_record(fixture):
    service,p=fixture; record=service.portfolio_reviews.save(p)
    tail=service.root/'artifacts/private'/p['evidence_refs'][0]['id']/'report.json'
    tail.write_text(tail.read_text(encoding='utf-8')+' ',encoding='utf-8')
    assert not service.portfolio_reviews.list(p['source_import_id'])['packages'][0]['evidence_current']
    with pytest.raises(ValueError): service.portfolio_reviews.report(p['source_import_id'],record['id'])
    with service.portfolio_reviews.connect() as db: assert db.execute('SELECT COUNT(*) FROM history').fetchone()[0]==1


def test_http_create_export_conflict_and_cross_origin(fixture):
    service,p=fixture; server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); base='http://127.0.0.1:'+str(server.server_port)
    headers={'Content-Type':'application/json','Origin':base,'X-CreditAtlas-Client':'local'}
    def post(payload,custom=headers): return urlopen(Request(base+'/api/portfolio-reviews',data=json.dumps(payload).encode(),headers=custom))
    try:
        with post(p) as response: record=json.load(response); assert response.status==201
        query='?source_import_id='+p['source_import_id']+'&id='+record['id']
        with urlopen(base+'/api/portfolio-review-report'+query) as response: assert json.load(response)['revision']==1
        with pytest.raises(HTTPError) as error: post(p,{**headers,'Origin':'https://external.example'})
        assert error.value.code==403
        with pytest.raises(HTTPError) as error: post({**p,'id':record['id'],'revision':0})
        assert error.value.code==409
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
