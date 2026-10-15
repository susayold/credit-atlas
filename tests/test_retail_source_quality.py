from pathlib import Path
from types import SimpleNamespace
import copy
import json
import pytest
from credit_atlas.retail_source_quality import report
from credit_atlas.workspace import sha256
from credit_atlas.monitor_reviews import MonitorReviews

ROOT = Path(__file__).resolve().parents[1]
VIEW = 'suite-view-74e07524f6d0'


@pytest.fixture
def views(tmp_path):
    source = json.loads((ROOT / 'data/private/public-suite/suite-619b1ee9aa8c/uci-retail-receipt.json').read_text())
    relative = 'data/private/public-suite/suite-619b1ee9aa8c/uci-retail-receipt.json'
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(source))
    anchor = tmp_path / 'artifacts/private' / VIEW / 'view-complete.json'
    anchor.parent.mkdir(parents=True)
    anchor.write_text(json.dumps({'inputs_sha256': {relative: sha256(path)}}))
    snapshot = {'view_id': VIEW, 'suite_id': 'suite-619b1ee9aa8c'}
    return SimpleNamespace(root=tmp_path, view=lambda _: copy.deepcopy(snapshot))


def test_source_population_and_exclusions(views):
    r = report(views, VIEW)
    assert r['rows'] == 30000 and r['feature_cells'] == 690000
    assert r['missing_feature_share'] == 0 and len(r['features']) == 23
    assert r['features'][0]['feature'] == 'LIMIT_BAL'
    assert {f['source_field'] for f in r['excluded_fields']} == {'ID', 'Y'}
    assert 'not final-test' in r['scope']
    # Fixture contains only aggregate receipts: reading client rows is impossible.
    assert not list(views.root.rglob('*.csv'))


def test_nonzero_counts_and_denominator(views):
    path = next(views.root.rglob('uci-retail-receipt.json'))
    source = json.loads(path.read_text()); source['profile']['null_counts']['X1'] = 150
    path.write_text(json.dumps(source))
    anchor = next(views.root.rglob('view-complete.json'))
    pins = json.loads(anchor.read_text()); key = next(iter(pins['inputs_sha256']))
    pins['inputs_sha256'][key] = sha256(path); anchor.write_text(json.dumps(pins))
    r = report(views, VIEW)
    assert r['features'][0]['missing_share'] == 150 / 30000
    assert r['missing_feature_share'] == 150 / 690000


def test_mutated_profile_rejected(views):
    path = next(views.root.rglob('uci-retail-receipt.json'))
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='bound'):
        report(views, VIEW)


@pytest.mark.parametrize('query', [{'view_id': 'other'}, {'partition': 'final'}, {'field': 'X1'}])
def test_scope_rejected(views, query):
    with pytest.raises(ValueError): report(views, VIEW, query)


def test_review_source_capture_requires_same_suite(views):
    store = MonitorReviews(SimpleNamespace(root=views.root, suite_views=views))
    snapshot = {'domain': 'P1', 'scope': 'QA', 'metrics': [{'name': 'N', 'value': 1}],
                'quality_metrics': [], 'filters': {}, 'comparison_control': None,
                'evidence_refs': [{'kind': 'suite', 'id': VIEW}, {'kind': 'source_quality', 'id': VIEW}]}
    assert len(store.capture(snapshot)['source_capture']) == 2
    snapshot['evidence_refs'][1]['id'] = 'other'
    with pytest.raises(ValueError, match='same suite'): store.capture(snapshot)


@pytest.mark.parametrize('value', [-1, 30001, True, 0.5])
def test_invalid_profile_counts_rejected_even_when_pinned(views, value):
    path = next(views.root.rglob('uci-retail-receipt.json'))
    source = json.loads(path.read_text()); source['profile']['null_counts']['X1'] = value
    path.write_text(json.dumps(source))
    anchor = next(views.root.rglob('view-complete.json'))
    pins = json.loads(anchor.read_text()); key = next(iter(pins['inputs_sha256']))
    pins['inputs_sha256'][key] = sha256(path); anchor.write_text(json.dumps(pins))
    with pytest.raises(ValueError, match='Malformed'): report(views, VIEW)


def test_http_scope_and_private_report(views):
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
    from credit_atlas.server import handler_for
    server = ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=views.root,suite_views=views)))
    thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    url = f'http://127.0.0.1:{server.server_port}/api/retail-source-quality-report?view_id={VIEW}'
    try:
        with urlopen(url) as response:
            assert response.headers['Cache-Control']=='no-store'
            assert 'attachment' in response.headers['Content-Disposition']
            assert json.load(response)['feature_cells']==690000
        with pytest.raises(HTTPError) as exc: urlopen(url+'&partition=final')
        assert exc.value.code==400
        with pytest.raises(HTTPError) as exc: urlopen(Request(url,headers={'Origin':'https://other.example'}))
        assert exc.value.code==403
    finally:
        server.shutdown(); server.server_close(); thread.join(5)
