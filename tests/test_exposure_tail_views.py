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
from credit_atlas.exposure_tail_views import ExposureTailViews
from credit_atlas.server import handler_for
from tests.test_exposure_tail import frozen


@pytest.fixture
def fixture(tmp_path):
    receipt=frozen(tmp_path); return tmp_path,receipt,ExposureTailViews(tmp_path)


def test_binding_currency_and_cache_copies(fixture):
    root,receipt,views=fixture; source=receipt['source_import_id']
    assert views.catalog(source)['tail_studies'][0]['tail_id']==receipt['tail_id']
    assert views.catalog('exposure-import-000000000000')['tail_studies']==[]
    query={'tail_id':receipt['tail_id'],'source_import_id':source,'currency':'USD'}
    report=views.report(query)
    assert all(r['currency']=='USD' for r in report['results'])
    report['results'][0]['mean_loss']=999
    assert views.report(query)['results'][0]['mean_loss']!=999
    assert 'position_id' not in json.dumps(report) and 'total-draws' not in json.dumps(report)
    for change in ({'source_import_id':'exposure-import-000000000000'},{'currency':'GBP'},{'dimension':'segment'},{'seed':'99'}):
        with pytest.raises(ValueError): views.report({**query,**change})


def test_cache_rejects_same_timestamp_draw_corruption(fixture):
    root,receipt,views=fixture; views.catalog(receipt['source_import_id'])
    path=root/'artifacts/private'/receipt['tail_id']/'total-draws.parquet'; stat=path.stat()
    with path.open('ab') as file: file.write(b'corruption')
    os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match='source changed'): views.evidence(receipt['tail_id'])
    assert views.catalog(receipt['source_import_id'])['tail_studies']==[]


def test_independent_tail_audit_detects_es_fault(fixture,monkeypatch):
    root,receipt,views=fixture
    spec=importlib.util.spec_from_file_location('tail_audit',Path(__file__).parents[1]/'scripts/audit_exposure_tail.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.audit(root,receipt['tail_id'])['status']=='PASS'
    original=module.verify
    def bad(*args):
        folder,receipt,report=original(*args); report['results'][0]['tails'][0]['es']+=99
        return folder,receipt,report
    monkeypatch.setattr(module,'verify',bad)
    with pytest.raises(ValueError,match='Independent tail audit failed'): module.audit(root,receipt['tail_id'])


def test_http_private_report_exact_contract(fixture):
    root,receipt,views=fixture; source=receipt['source_import_id']
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=root,exposure_tail_views=views)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base='http://127.0.0.1:'+str(server.server_port); query='?tail_id='+receipt['tail_id']+'&source_import_id='+source
    try:
        for endpoint in ('/api/exposure-tail','/api/exposure-tail-report'):
            with urlopen(base+endpoint+query) as response:
                assert json.load(response)==views.report({'tail_id':receipt['tail_id'],'source_import_id':source})
                assert 'no-store' in response.headers['Cache-Control']
        for suffix in ('&seed=0','&tail_id='+receipt['tail_id'],'&dimension=position_id','&currency=GBP'):
            with pytest.raises(HTTPError) as error: urlopen(base+'/api/exposure-tail'+query+suffix)
            assert error.value.code==400
        with pytest.raises(HTTPError) as error: urlopen(Request(base+'/api/exposure-tail'+query,headers={'Origin':'https://external.example'}))
        assert error.value.code==403
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
