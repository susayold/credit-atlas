import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.request import urlopen

import pytest
from credit_atlas.excel_workbench import ExcelWorkbench
from credit_atlas.exposure_convergence import build
from credit_atlas.exposure_convergence_views import ExposureConvergenceViews
from credit_atlas.exposure_views import ExposureViews
from credit_atlas.server import handler_for
from credit_atlas.workspace import write_new
from tests.test_exposure_tail import frozen
from tests.test_exposure_convergence import plan


def test_source_filters_copies_and_cached_corruption(tmp_path):
    base=frozen(tmp_path); write_new(tmp_path/'convergence.json',plan(base['tail_id']))
    receipt=build(tmp_path,'convergence.json'); views=ExposureConvergenceViews(tmp_path)
    assert len(views.catalog(base['source_import_id'])['studies'])==1
    query={'convergence_id':receipt['convergence_id'],'source_import_id':base['source_import_id'],'currency':'USD'}
    report=views.report(query); assert all(r['currency']=='USD' for r in report['diagnostics'])
    report['runs'].clear(); assert views.report(query)['runs']
    for change in ({'currency':'GBP'},{'source_import_id':'x'},{'seed':'0'}):
        with pytest.raises(ValueError): views.report({**query,**change})
    path=tmp_path/'artifacts/private'/receipt['convergence_id']/'report.json'
    path.write_text(path.read_text(encoding='utf-8')+' ',encoding='utf-8')
    with pytest.raises(ValueError,match='source changed'): views.report(query)


def test_private_report_download_carries_source_and_convergence_receipts(tmp_path):
    base=frozen(tmp_path); write_new(tmp_path/'convergence.json',plan(base['tail_id']))
    receipt=build(tmp_path,'convergence.json'); views=ExposureConvergenceViews(tmp_path)
    service=SimpleNamespace(root=tmp_path,exposure_convergence_views=views,exposure_views=ExposureViews(tmp_path))
    service.excel_workbench=ExcelWorkbench(service)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service)); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    query='?convergence_id='+receipt['convergence_id']+'&source_import_id='+base['source_import_id']
    try:
        with urlopen('http://127.0.0.1:'+str(server.server_port)+'/api/exposure-convergence-report'+query) as response:
            report=json.load(response); provenance=report.pop('export_provenance')
        assert provenance['source_imports'][0]['import_id']==base['source_import_id']
        convergence_artifact=next(item for item in provenance['derived_artifacts'] if item['artifact_type']=='convergence')
        tail_artifact=next(item for item in provenance['derived_artifacts'] if item['artifact_type']=='tail')
        assert convergence_artifact['artifact_id']==receipt['convergence_id']
        assert len(convergence_artifact['receipt_sha256'])==64
        assert tail_artifact['artifact_id']==base['tail_id']
        assert provenance['visibility']=='private' and provenance['public_release_approved'] is False
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
