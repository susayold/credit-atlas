import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.market_data import prepare_market
from credit_atlas.market_views import MarketViews, build_market_view
from credit_atlas.server import handler_for
from tests.test_market_data import market_acquisition


@pytest.fixture
def market_view(market_acquisition):
    root, identifier, _ = market_acquisition
    case = prepare_market(root, identifier)
    view = build_market_view(root, case['case_id'])
    return root, view, MarketViews(root)


def test_snapshot_native_report_and_rights_scope(market_view):
    root, view, service = market_view
    snapshot = service.view(view['view_id'])
    assert snapshot['native_records'] == 13
    assert snapshot['latest_three_tenor_date']['observation_date'] == '2026-01-02'
    assert snapshot['latest_aligned_date']['dgs10_percent'] is None
    assert str(root) not in json.dumps(snapshot)
    report = service.report(view['view_id'], dict(view_id=view['view_id'], series='DGS10', **{'from': '2026-01-05', 'to': '2026-01-06'}))
    assert report['native_rows'] == 2 and report['known_rows'] == 1
    assert [row['value_percent'] for row in report['rows']] == ['3.500000', None]
    assert report['profile']['rows'] == 3 and report['profile_scope'].startswith('whole_native_series')
    assert report['public_release_approved'] is False


def test_daily_context_preserves_present_missing_and_absent(market_view):
    _, view, service = market_view
    result = service.daily(view['view_id'], dict(view_id=view['view_id'], **{'from': '2026-01-03', 'to': '2026-01-05'}))
    assert len(result['rows']) == 2 and result['alignment'] == 'same_native_date_no_fill'
    assert result['rows'][0]['bamlc0a0cm_percent'] == '1.200000'
    assert result['rows'][0]['dgs2_percent'] is None and not result['rows'][0]['dgs2_native_present']
    assert result['rows'][1]['dgs2_percent'] is None and result['rows'][1]['dgs2_native_present']


def test_bond_scenario_separate_from_source_market_series(market_view):
    _, view, service = market_view
    result = service.bond(view['view_id'], dict(view_id=view['view_id'], face_usd='100',
        coupon_percent='5', yield_percent='5', years='10', frequency='2'))
    assert result['price_usd'] == pytest.approx(100)
    assert result['source_market_series_used_for_pricing'] is False and result['market_calibrated'] is False
    assert result['conventions']['settlement'] == 'coupon_date_zero_accrued_interest'


@pytest.mark.parametrize('changes', [{'series': 'NOT_A_SERIES'}, {'segment': 'all'},
    {'from': '2026-01-07', 'to': '2026-01-01'}, {'from': '1900-01-01', 'to': '2026-01-01'}])
def test_invalid_market_scope_rejected(market_view, changes):
    _, view, service = market_view
    query = dict(view_id=view['view_id'], series='DGS10', **{'from': '2026-01-01', 'to': '2026-01-06'})
    query.update(changes)
    with pytest.raises(ValueError):
        service.report(view['view_id'], query)


def test_changed_snapshot_rejected_without_stale_fallback(market_view):
    root, view, service = market_view
    assert service.catalog()['views'][0]['status'] == 'verified'
    path = root / 'artifacts/private' / view['view_id'] / 'snapshot.json'
    path.write_text(path.read_text() + ' ')
    with pytest.raises(ValueError, match='snapshot changed'):
        service.view(view['view_id'])
    assert service.catalog()['views'][0]['status'] == 'unavailable'


def test_local_market_http_routes_exports_and_unsupported_terms(market_view):
    root, view, service = market_view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, market_views=service)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    identifier = view['view_id']
    try:
        with urlopen(base + '/api/market-report?view_id=' + identifier + '&series=BAMLC0A0CM&from=2026-01-02&to=2026-01-05') as response:
            assert response.headers['Content-Disposition'].startswith('attachment;')
            result = json.load(response)
            assert result['native_rows'] == 3 and 'internal use only' in result['profile']['rights']
        with urlopen(base + '/api/bond-scenario?view_id=' + identifier + '&face_usd=100&coupon_percent=5&yield_percent=5&years=10&frequency=2') as response:
            assert json.load(response)['price_usd'] == pytest.approx(100)
        for route in ['/api/market-view?view_id=' + identifier + '&series=DGS2',
                      '/api/market-report?view_id=' + identifier + '&series=DGS10&from=2026-01-01&to=2026-01-02&segment=relief',
                      '/api/bond-scenario?view_id=' + identifier + '&face_usd=100&coupon_percent=5&yield_percent=5&years=10&frequency=3']:
            with pytest.raises(HTTPError) as error:
                urlopen(base + route)
            assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
