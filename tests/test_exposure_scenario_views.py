import importlib.util
import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request,urlopen

import pytest
from credit_atlas.exposure_scenario_views import ExposureScenarioViews
from credit_atlas.server import handler_for
from tests.test_exposure_scenarios import frozen,ratio


@pytest.fixture
def fixture(tmp_path):
    receipt=frozen(tmp_path); return tmp_path,receipt,ExposureScenarioViews(tmp_path)


def test_source_binding_filters_and_cache_copies(fixture):
    root,receipt,views=fixture; source=receipt['source_import_id']
    assert views.catalog(source)['scenario_sets'][0]['scenario_id']==receipt['scenario_id']
    assert views.catalog('exposure-import-000000000000')['scenario_sets']==[]
    q={'scenario_id':receipt['scenario_id'],'source_import_id':source,'dimension':'segment','currency':'USD'}
    report=views.report(q); assert len(report['scope'])==1
    assert all(r['currency']=='USD' and r['dimension'] in ('total','segment') for s in report['scenarios'] for r in s['aggregates'])
    report['assumptions']['name']='mutated'; assert views.report(q)['assumptions']['name']!='mutated'
    for change in ({'source_import_id':'exposure-import-000000000000'},{'currency':'GBP'},{'dimension':'representation'},{'pd':'0.1'}):
        with pytest.raises(ValueError): views.report({**q,**change})


def test_cached_assumptions_corruption_same_timestamp_rejected(fixture):
    root,receipt,views=fixture; views.catalog(receipt['source_import_id'])
    path=root/'artifacts/private'/receipt['scenario_id']/'assumptions.json'; stat=path.stat()
    path.write_text(path.read_text(encoding='utf-8').replace('Illustrative fixture','Altered assumption'),encoding='utf-8')
    os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match='source changed'): views.evidence(receipt['scenario_id'])
    assert views.catalog(receipt['source_import_id'])['scenario_sets']==[]


def test_independent_decimal_audit_detects_wrong_pd_effect(fixture,monkeypatch):
    root,receipt,views=fixture
    spec=importlib.util.spec_from_file_location('scenario_audit',Path(__file__).parents[1]/'scripts/audit_exposure_scenarios.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.audit(root,receipt['scenario_id'])['status']=='PASS'
    original=module.verify
    def bad(*args):
        folder,receipt,report=original(*args); report['scenarios'][1]['aggregates'][0]['pd_effect']['numerator']='999'; return folder,receipt,report
    monkeypatch.setattr(module,'verify',bad)
    with pytest.raises(ValueError,match='Independent scenario audit failed'): module.audit(root,receipt['scenario_id'])


def test_private_http_export_guard_and_exact_rational(fixture):
    root,receipt,views=fixture
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=root,exposure_scenario_views=views)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    q={'scenario_id':receipt['scenario_id'],'source_import_id':receipt['source_import_id']}
    query='?scenario_id='+q['scenario_id']+'&source_import_id='+q['source_import_id']
    try:
        for endpoint in ('/api/exposure-scenario','/api/exposure-scenario-report'):
            with urlopen(base+endpoint+query) as response:
                report=json.load(response); assert report==views.report(q)
                assert 'no-store' in response.headers['Cache-Control']
                assert str(root) not in json.dumps(report) and 'source_lineage' not in report
        for suffix in ('&pd=1','&scenario_id='+q['scenario_id'],'&currency=GBP','&dimension=loan'):
            with pytest.raises(HTTPError) as error: urlopen(base+'/api/exposure-scenario'+query+suffix)
            assert error.value.code==400
        with pytest.raises(HTTPError) as error: urlopen(Request(base+'/api/exposure-scenario'+query,headers={'Origin':'https://external.example'}))
        assert error.value.code==403
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
