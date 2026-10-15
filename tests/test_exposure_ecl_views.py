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
from credit_atlas.exposure_ecl_views import ExposureEclViews
from credit_atlas.server import handler_for
from tests.test_exposure_ecl import frozen


@pytest.fixture
def fixture(tmp_path):
    receipt=frozen(tmp_path); return tmp_path,receipt,ExposureEclViews(tmp_path)


def test_source_binding_exact_filters_and_cache_copies(fixture):
    root,receipt,views=fixture; source=receipt['source_import_id']
    assert views.catalog(source)['ecl_studies'][0]['ecl_id']==receipt['ecl_id']
    assert views.catalog('exposure-import-000000000000')['ecl_studies']==[]
    query={'ecl_id':receipt['ecl_id'],'source_import_id':source,'currency':'USD','dimension':'stage'}
    report=views.report(query)
    assert all(r['currency']=='USD' and r['dimension'] in ('total','stage') for r in report['probability_weighted_aggregates'])
    report['stage_assessments']['segmentA']['stage']=3
    assert views.report(query)['stage_assessments']['segmentA']['stage']==1
    for change in ({'source_import_id':'exposure-import-000000000000'},{'currency':'GBP'},{'dimension':'source_state'},{'hazard':'1'}):
        with pytest.raises(ValueError): views.report({**query,**change})


def test_cache_rejects_same_timestamp_assumption_corruption(fixture):
    root,receipt,views=fixture; views.catalog(receipt['source_import_id'])
    path=root/'artifacts/private'/receipt['ecl_id']/'assumptions.json'; stat=path.stat()
    path.write_text(path.read_text(encoding='utf-8').replace('Declared fixture','Altered research'),encoding='utf-8')
    os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match='source changed'): views.evidence(receipt['ecl_id'])
    assert views.catalog(receipt['source_import_id'])['ecl_studies']==[]


def test_independent_cash_identity_audit_detects_marginal_probability_fault(fixture,monkeypatch):
    root,receipt,views=fixture
    spec=importlib.util.spec_from_file_location('ecl_audit',Path(__file__).parents[1]/'scripts/audit_exposure_ecl.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.audit(root,receipt['ecl_id'])['status']=='PASS'
    original=module.verify
    def bad(*args):
        folder,receipt,report=original(*args)
        report['scenarios'][0]['segments']['segmentA']['default_events'][0]['marginal_default_probability']['numerator']='99'
        return folder,receipt,report
    monkeypatch.setattr(module,'verify',bad)
    with pytest.raises(ValueError,match='Independent ECL audit failed'): module.audit(root,receipt['ecl_id'])


def test_http_exact_private_report_binding_and_parameter_guards(fixture):
    root,receipt,views=fixture; source=receipt['source_import_id']
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=root,exposure_ecl_views=views)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base='http://127.0.0.1:'+str(server.server_port); query='?ecl_id='+receipt['ecl_id']+'&source_import_id='+source
    try:
        for endpoint in ('/api/exposure-ecl','/api/exposure-ecl-report'):
            with urlopen(base+endpoint+query) as response:
                report=json.load(response); assert report==views.report({'ecl_id':receipt['ecl_id'],'source_import_id':source})
                assert 'no-store' in response.headers['Cache-Control'] and str(root) not in json.dumps(report)
        for suffix in ('&eir=0','&ecl_id='+receipt['ecl_id'],'&dimension=position_id','&currency=GBP'):
            with pytest.raises(HTTPError) as error: urlopen(base+'/api/exposure-ecl'+query+suffix)
            assert error.value.code==400
        with pytest.raises(HTTPError) as error: urlopen(Request(base+'/api/exposure-ecl'+query,headers={'Origin':'https://external.example'}))
        assert error.value.code==403
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
