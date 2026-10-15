import json
import os
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas import hmda_references as refs
from credit_atlas.hmda_reference_views import HmdaReferenceViews
from credit_atlas.server import handler_for
from credit_atlas.workspace import sha256
from tests.test_hmda_views import view
from tests.test_hmda_sources import fake_network
from tests.test_hmda_references import filer_rows


@pytest.fixture
def labeled(view, monkeypatch):
    root, source, case, snapshot, aggregate = view
    def download(url, path):
        body = '<html>API</html>' if path.suffix == '.html' else json.dumps({'institutions': filer_rows(int(path.name[:4]))})
        path.write_text(body, encoding='utf-8')
        return {'file': path.name, 'url': url, 'http_status': 200, 'bytes': path.stat().st_size,
                'sha256': sha256(path), 'retrieved_at': 'fixture'}
    monkeypatch.setattr(refs, 'download', download)
    receipt, payload = refs.acquire_references(root, source['source_id'], 'lender_only')
    return root, source, snapshot, aggregate, receipt, HmdaReferenceViews(root, aggregate)


def test_labeled_report_preserves_all_base_numbers_and_dated_names(labeled):
    root, source, snapshot, aggregate, receipt, service = labeled
    for year in ('2023', '2024', '2025'):
        query = {'view_id': snapshot['view_id'], 'year': year, 'dimension': 'lender'}
        actual = service.report(receipt['reference_id'], query); base = aggregate.report(snapshot['view_id'], query)
        assert actual['summary'] == base['summary'] and actual['timeline'] == base['timeline']
        assert actual['breakdown'][0]['display_label']['names'] == ['Lender ' + year]
        assert actual['breakdown'][1]['display_label']['status'] == 'AMBIGUOUS'
        assert actual['reference']['county_names_acquired'] is False
        for row in actual['breakdown']: row.pop('display_label')
        actual.pop('reference'); assert actual == base


def test_missing_county_labels_keep_codes_and_counts(labeled):
    root, source, snapshot, aggregate, receipt, service = labeled
    report = service.report(receipt['reference_id'], {'view_id': snapshot['view_id'], 'dimension': 'county'})
    assert report['breakdown'][0]['bucket'] == '24031'
    assert all(row['display_label'] == {'names': [], 'status': 'UNMATCHED'} for row in report['breakdown'])


def test_cross_source_reference_rejected(labeled):
    *_, receipt, service = labeled
    with pytest.raises(ValueError, match='another HMDA source'):
        service.reference(receipt['reference_id'], 'hmda-source-' + '1' * 12)


def test_hot_reference_cache_checks_content_even_when_timestamp_restored(labeled):
    root, source, snapshot, aggregate, receipt, service = labeled
    identifier = receipt['reference_id']; service.reference(identifier, source['source_id'])
    path = root / 'data/private/hmda' / identifier / '2024-filers.json'; stat = path.stat()
    path.write_text(path.read_text().replace('Lender 2024', 'Forged 2024'), encoding='utf-8')
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError, match='Frozen HMDA reference'): service.reference(identifier, source['source_id'])
    assert service.catalog(source['source_id'])['references'][0]['status'] == 'unavailable'


def test_reference_results_do_not_mutate_cached_projection(labeled):
    root, source, snapshot, aggregate, receipt, service = labeled
    result = service.reference(receipt['reference_id'], source['source_id'])
    result['references']['2024']['lender']['A' * 20]['names'] = ['Invented']
    assert service.reference(receipt['reference_id'], source['source_id'])['references']['2024']['lender']['A' * 20]['names'] == ['Lender 2024']


def test_http_named_export_and_source_origin_parameter_guards(labeled):
    root, source, snapshot, aggregate, receipt, service = labeled
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, hmda_reference_views=service)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    endpoint = '/api/hmda-labeled-report?reference_id=' + receipt['reference_id'] + '&view_id=' + snapshot['view_id'] + '&year=2024&dimension=lender'
    try:
        with urlopen(base + endpoint) as response:
            assert 'attachment' in response.headers['Content-Disposition']
            assert response.headers['Cache-Control'] == 'no-store'
            result = json.load(response)
            assert result == service.report(receipt['reference_id'], {'view_id': snapshot['view_id'], 'year': '2024', 'dimension': 'lender'})
            assert str(root) not in json.dumps(result)
        for suffix in ('&pd=1', '&reference_id=other', '&year=2026'):
            with pytest.raises(HTTPError) as error: urlopen(base + endpoint + suffix)
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + endpoint, headers={'Origin': 'https://other.example'}))
        assert error.value.code == 403
        with pytest.raises(HTTPError) as error: urlopen(base + '/api/hmda-reference?reference_id=' + receipt['reference_id'] + '&source_id=hmda-source-' + '1' * 12)
        assert error.value.code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
