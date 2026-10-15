import importlib.util
import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from credit_atlas import exposure_movements as movements
from credit_atlas.exposure_movement_views import ExposureMovementViews
from credit_atlas.server import handler_for
from tests.test_exposure_movements import imported_pair


@pytest.fixture
def fixture(tmp_path):
    a,b=imported_pair(tmp_path); receipt=movements.build(tmp_path,a,b)
    return tmp_path,a,b,receipt,ExposureMovementViews(tmp_path)


def test_filters_bound_to_closing_source_and_cached_copies(fixture):
    root,a,b,receipt,views=fixture
    assert views.catalog(b)['movements'][0]['movement_id']==receipt['movement_id']
    assert views.catalog(a)['movements']==[]
    q={'movement_id':receipt['movement_id'],'closing_import_id':b,'currency':'USD','dimension':'region'}
    report=views.report(q); assert all(r['currency']=='USD' and r['dimension']=='region' for r in report['groups'])
    report['currencies'][0]['residual']='1'; assert views.report(q)['currencies'][0]['residual']!='1'
    for change in ({'closing_import_id':a},{'dimension':'position_id'},{'currency':'GBP'},{'pd':'1'}):
        with pytest.raises(ValueError): views.report({**q,**change})


def test_cache_checks_bytes_when_timestamp_preserved(fixture):
    root,a,b,receipt,views=fixture; views.catalog(b)
    path=root/'artifacts/private'/a/'source.csv'; stat=path.stat()
    path.write_text(path.read_text(encoding='utf-8').replace('segmentA','segmentB'),encoding='utf-8')
    os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match='source changed'): views.evidence(receipt['movement_id'])
    assert views.catalog(b)['movements']==[]


def test_independent_fraction_audit_and_fault_detection(fixture,monkeypatch):
    root,a,b,receipt,views=fixture
    spec=importlib.util.spec_from_file_location('movement_audit',Path(__file__).parents[1]/'scripts/audit_exposure_movement.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.audit(root,receipt['movement_id'])['status']=='PASS'
    original=module.verify
    def wrong(*args):
        folder,receipt,report=original(*args); report['currencies'][0]['continuing_amount_change']='99'; return folder,receipt,report
    monkeypatch.setattr(module,'verify',wrong)
    with pytest.raises(ValueError,match='Independent movement audit failed'): module.audit(root,receipt['movement_id'])


def test_http_exact_private_export_and_filter_guards(fixture):
    root,a,b,receipt,views=fixture
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=root,exposure_movement_views=views)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    query='?movement_id='+receipt['movement_id']+'&closing_import_id='+b
    base='http://127.0.0.1:'+str(server.server_port)
    try:
        for endpoint in ('/api/exposure-movement','/api/exposure-movement-report'):
            with urlopen(base+endpoint+query) as response:
                value=json.load(response); assert value==views.report({'movement_id':receipt['movement_id'],'closing_import_id':b})
                assert 'no-store' in response.headers['Cache-Control']
                assert str(root) not in json.dumps(value) and 'source_lineage' not in value
        for suffix in ('&dimension=loan','&movement_id='+receipt['movement_id'],'&closing_import_id='+a,'&run=1'):
            with pytest.raises(HTTPError) as error: urlopen(base+'/api/exposure-movement'+query+suffix)
            assert error.value.code==400
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
