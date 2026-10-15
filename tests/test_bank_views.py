import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas import bank_views
from credit_atlas.bank_panel import prepare_bank_panel
from credit_atlas.server import handler_for
from tests.test_bank_panel import acquired


@pytest.fixture
def view(acquired):
    root, acquisition = acquired
    panel = prepare_bank_panel(root, acquisition['acquisition_id'])
    receipt = bank_views.build_bank_view(root, panel['case_id'])
    return root, receipt, bank_views.BankViews(root)


def test_snapshot_and_selected_export_scope(view):
    root, receipt, service = view
    snapshot = service.view(receipt['view_id'])
    assert len(snapshot['quarters']) == 42 and snapshot['records'] == 42
    assert str(root) not in json.dumps(snapshot) and 'bank-quarter.parquet' not in json.dumps(snapshot)
    assert snapshot['peers'][0]['reported_assets_usd_thousands'] == '100000'
    report = bank_views.bank_report(snapshot, dict(view_id=receipt['view_id'], quarter='2026-06-30', peer='100m_to_1bn'))
    assert report['selected_record_count'] == 1 and len(report['rows']) == 1
    assert report['quarter_quality']['report_date'] == '2026-06-30'
    assert report['quarter_quality_scope'] == 'whole_selected_quarter_not_filtered_by_peer'
    assert report['matched_change']['matched_reports'] == 1
    report['rows'][0]['records'] = 100
    assert snapshot['peers'][-1]['records'] == 1


@pytest.mark.parametrize('query', [{'quarter': '2026-09-30'}, {'peer': 'relief'},
    {'segment': 'all'}, {'cert': '123'}, {'view_id': 'other'}])
def test_unsupported_filters_rejected(view, query):
    _, receipt, service = view
    with pytest.raises(ValueError):
        bank_views.bank_report(service.view(receipt['view_id']), query)


def test_timeline_scope_and_invalid_certificate(view):
    _, receipt, service = view
    result = service.timeline(receipt['view_id'], '123')
    assert len(result['rows']) == 42 and result['rows'][0]['assets_usd_thousands'] == '100000'
    assert result['rows'][-1]['report_date'] == '2026-06-30'
    assert result['scope'].startswith('one_certificate_all_observed_quarters')
    with pytest.raises(ValueError):
        service.timeline(receipt['view_id'], '123 OR 1=1')
    with pytest.raises(KeyError):
        service.timeline(receipt['view_id'], '999')


def test_changed_snapshot_and_catalog_unavailable(view):
    root, receipt, service = view
    assert service.catalog()['views'][0]['status'] == 'verified'
    path = root / 'artifacts/private' / receipt['view_id'] / 'snapshot.json'
    path.write_text(path.read_text() + ' ')
    with pytest.raises(ValueError, match='snapshot changed'):
        service.view(receipt['view_id'])
    assert service.catalog()['views'][0]['status'] == 'unavailable'


def test_changed_methods_rejected(view, monkeypatch):
    _, receipt, service = view
    original = bank_views.method_hashes()
    monkeypatch.setattr(bank_views, 'method_hashes', lambda: {**original, 'bank_views': 'changed'})
    with pytest.raises(ValueError, match='implementation'):
        service.view(receipt['view_id'])


def test_http_bank_routes_scoped_export_and_rejections(view):
    root, receipt, banks = view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, bank_views=banks)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    identifier = receipt['view_id']
    try:
        with urlopen(base + '/api/bank-views') as response:
            assert json.load(response)['views'][0]['status'] == 'verified'
        with urlopen(base + '/api/bank-report?view_id=' + identifier + '&quarter=2026-06-30&peer=all') as response:
            assert response.headers['Content-Disposition'].startswith('attachment;')
            assert response.headers['Cache-Control'] == 'no-store'
            result = json.load(response)
            assert result['selected_record_count'] == 1 and result['public_release_approved'] is False
        with urlopen(base + '/api/bank-timeline?view_id=' + identifier + '&cert=123') as response:
            assert len(json.load(response)['rows']) == 42
        for path in ['/api/bank-view?view_id=' + identifier + '&segment=all',
                     '/api/bank-timeline?view_id=' + identifier + '&cert=123&peer=all',
                     '/api/bank-report?view_id=' + identifier + '&quarter=unknown',
                     '/api/bank-views?run=other']:
            with pytest.raises(HTTPError) as error:
                urlopen(base + path)
            assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
