import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
import pytest
from credit_atlas import retail_cohort_explanations as cohort
from credit_atlas.retail_cohort_explanation_views import RetailCohortExplanationViews
from credit_atlas.server import handler_for
from credit_atlas.workspace import sha256
from tests.test_retail_cohort_explanations import inputs,plan


def test_all_clients_pagination_exact_search_export_binding_and_cached_corruption(tmp_path,monkeypatch):
    file=tmp_path/'source.txt'; file.write_text('original')
    validation,scores,ref,columns,predict,parent,private=inputs()
    monkeypatch.setattr(cohort,'source',lambda root,p:(validation,scores,ref,columns,predict,{'source.txt':sha256(file)},parent,private))
    identifier=cohort.build(tmp_path,plan())['cohort_id']; views=RetailCohortExplanationViews(tmp_path)
    import credit_atlas.retail_cohort_explanation_views as serving
    monkeypatch.setattr(serving,'verify_cohort_saved',cohort.verify)
    scope={k:plan()[k] for k in ('freeze_id','explanations_id')}; query=scope|{'cohort_id':identifier}
    assert views.catalog(scope)['studies'][0]['records']==40
    first=views.clients(query); second=views.clients(query|{'offset':'20'})
    assert first['total']==40 and len(first['clients'])==len(second['clients'])==20
    assert not {r['client_token'] for r in first['clients']}&{r['client_token'] for r in second['clients']}
    token=second['clients'][-1]['client_token']; exact=views.clients(query|{'q':token})
    assert len(exact['clients'])==exact['total']==1 and exact['clients'][0]['score_rank']==1
    assert views.clients(query|{'q':'client-'+'f'*24})['clients']==[]
    for bad in ({'limit':'51'},{'offset':'-1'},{'offset':'41'},{'q':'100'},{'limit':'２０'}):
        with pytest.raises(ValueError):views.clients(query|bad)
    report_query=query|{'client_token':token}; report=views.report(report_query)
    assert 'source_client_id' not in str(report) and 'features' not in str(first) and report['client']['score_rank']==1
    with pytest.raises(ValueError,match='source mismatch'):views.report(report_query|{'freeze_id':'retail-freeze-bbbbbbbbbbbb'})
    with pytest.raises(ValueError,match='does not belong'):views.report(report_query|{'client_token':'client-'+'f'*24})
    service=SimpleNamespace(root=tmp_path,retail_cohort_explanation_views=views)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service)); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); base='http://127.0.0.1:'+str(server.server_port)
    try:
        with urlopen(base+'/api/retail-client-explanation-report?'+urlencode(report_query)) as response:
            assert json.load(response)==report and 'no-store' in response.headers['Cache-Control'] and 'attachment' in response.headers['Content-Disposition']
        with pytest.raises(HTTPError) as error:urlopen(base+'/api/retail-explanation-clients?'+urlencode(query|{'limit':'1000'}))
        assert error.value.code==400
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    # Same length/timestamp must still fail content hashing.
    import os
    stat=file.stat();file.write_text('modified');os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match='input evidence'):views.report(report_query)
