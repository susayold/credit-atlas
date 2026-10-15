import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
import pytest
from credit_atlas import retail_explanations as module
from credit_atlas.retail_explanation_views import RetailExplanationViews
from credit_atlas.server import handler_for
from credit_atlas.workspace import sha256
from tests.test_retail_explanations import fixture, plan


def test_source_bound_case_report_private_http_and_cached_hash_corruption(tmp_path, monkeypatch):
    file = tmp_path / 'source.txt'; file.write_text('frozen development evidence')
    args = fixture(); lineage = {'freeze_id': plan()['freeze_id'], 'case_id': 'case', 'assessment_id': 'assessment', 'selected_model': 'logistic', 'selected_variant': 'raw'}
    monkeypatch.setattr(module, 'source', lambda root, p: (*args, {'source.txt': sha256(file)}, lineage))
    identifier = module.build(tmp_path, plan())['explanations_id']; views = RetailExplanationViews(tmp_path)
    import credit_atlas.retail_explanation_views as serving
    monkeypatch.setattr(serving,'verify',module.verify)
    scope = {'freeze_id': plan()['freeze_id']}; query = dict(scope, explanations_id=identifier, case='validation_case_12')
    assert views.catalog(scope)['studies'][0]['explanations_id'] == identifier
    report = views.report(query)
    assert len(report['local_explanations']) == 1 and len(report['global_permutation']) == 4
    assert 'source_client_id' not in str(report)
    with pytest.raises(ValueError, match='mismatch'): views.report(query | {'freeze_id': 'retail-freeze-bbbbbbbbbbbb'})
    with pytest.raises(ValueError, match='unavailable'): views.report(query | {'case': 'train_case_01'})
    service = SimpleNamespace(root=tmp_path, retail_explanation_views=views)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service)); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with urlopen(base + '/api/retail-explanation-report?' + urlencode(query)) as response:
            assert json.load(response) == report and 'attachment' in response.headers['Content-Disposition'] and 'no-store' in response.headers['Cache-Control']
        with pytest.raises(HTTPError) as error: urlopen(base + '/api/retail-explanation?' + urlencode(query | {'case': 'final_test_01'}))
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error: urlopen(base + '/api/retail-explanation?' + urlencode(query | {'explanations_id': '../escape'}))
        assert error.value.code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    original = file.stat(); file.write_text('broken development evidence')
    import os
    os.utime(file, ns=(original.st_atime_ns, original.st_mtime_ns))
    with pytest.raises(ValueError, match='input evidence'): views.report(query)
