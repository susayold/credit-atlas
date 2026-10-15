import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.bankruptcy import prepare_bankruptcy
from credit_atlas.bankruptcy_views import BankruptcyViews, build_bankruptcy_view
from credit_atlas.server import handler_for
from tests.test_bankruptcy import acquisition


@pytest.fixture
def view(acquisition):
    root, suite, reference, _ = acquisition
    case = prepare_bankruptcy(root, suite, reference)
    result = build_bankruptcy_view(root, case['case_id'])
    return root, result, BankruptcyViews(root)


def test_horizon_scope_definitions_and_null_extremes(view):
    root, receipt, service = view
    snapshot = service.view(receipt['view_id'])
    assert snapshot['rows'] == 10 and len(snapshot['feature_quality']) == 320
    assert str(root) not in json.dumps(snapshot)
    report = service.report(receipt['view_id'], {'horizon': '4', 'feature': 'A3'})
    assert report['horizon_summary']['source_subset_code'] == 2
    assert report['horizon_summary']['rows'] == 2
    assert len(report['feature_quality']) == 64
    assert report['selected_feature']['known'] == 0 and report['selected_feature']['min'] is None
    assert report['feature_definition']['original_attribute'] == 'Attr3'
    assert not report['model_qualified'] and not report['public_release_approved']
    assert service.catalog()['views'][0]['status'] == 'verified'


@pytest.mark.parametrize('query', [{'horizon': '2005'}, {'horizon': '0'}, {'feature': 'X1'},
                                  {'program': '7A'}, {'view_id': 'other'}])
def test_invalid_scopes_fail(view, query):
    _, receipt, service = view
    with pytest.raises(ValueError):
        service.report(receipt['view_id'], query)


def test_changed_snapshot_rejected(view):
    root, receipt, service = view
    path = root / 'artifacts/private' / receipt['view_id'] / 'snapshot.json'
    with path.open('a') as stream:
        stream.write('\n')
    with pytest.raises(ValueError, match='snapshot changed'):
        service.view(receipt['view_id'])
    assert service.catalog()['views'][0]['status'] == 'unavailable'


def test_real_http_filters_export_and_origin_guard(view):
    root, receipt, service = view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, bankruptcy_views=service)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with urlopen(base + '/api/bankruptcy-report?view_id=' + receipt['view_id'] + '&horizon=1&feature=A1') as response:
            assert 'attachment' in response.headers['Content-Disposition']
            assert response.headers['Cache-Control'] == 'no-store'
            report = json.load(response)
        assert report['horizon_summary']['source_subset_code'] == 5
        assert report['selected_feature']['min'] == -1200000
        for endpoint in ['/api/bankruptcy-views?horizon=1',
                         '/api/bankruptcy-view?view_id=' + receipt['view_id'] + '&feature=A1',
                         '/api/bankruptcy-report?view_id=' + receipt['view_id'] + '&horizon=1&horizon=2']:
            with pytest.raises(HTTPError) as error:
                urlopen(base + endpoint)
            assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
