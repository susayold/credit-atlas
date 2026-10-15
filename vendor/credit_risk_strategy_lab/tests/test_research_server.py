import hashlib
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from crsl.research_server import load_assets, make_handler


@pytest.fixture
def research_files(tmp_path):
    site = tmp_path / 'site/dist'
    site.mkdir(parents=True)
    (site / 'index.html').write_text('<h1>Test fixture</h1>')
    (site / 'data.json').write_text(json.dumps({'pipeline_run': 'test-run'}))
    directory = tmp_path / 'private-workbook'
    directory.mkdir()
    filename = 'Credit-Risk-Strategy-Lab-Private.xlsx'
    (directory / filename).write_bytes(b'synthetic endpoint fixture, not an Excel deliverable')
    (directory / 'preview.json').write_text(json.dumps({'pipeline_run': 'test-run'}))
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    registry = dict(filename=filename, sha256=digest(directory / filename),
                    preview_sha256=digest(directory / 'preview.json'),
                    pipeline_run='test-run', visibility='private', public_release_approved=False)
    (directory / 'registry.json').write_text(json.dumps(registry))
    (directory / 'qa.json').write_text(json.dumps({'status': 'PASS', 'sha256': registry['sha256']}))
    return tmp_path, directory


def test_changed_download_rejected(research_files):
    root, directory = research_files
    (directory / 'Credit-Risk-Strategy-Lab-Private.xlsx').write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed after QA'):
        load_assets(root, directory)


def test_mixed_website_workbook_runs_rejected(research_files):
    root, directory = research_files
    (root / 'site/dist/data.json').write_text(json.dumps({'pipeline_run': 'wrong-run'}))
    with pytest.raises(ValueError, match='different runs'):
        load_assets(root, directory)


def test_stale_workbook_qa_rejected(research_files):
    root, directory = research_files
    (directory / 'qa.json').write_text(json.dumps({'status': 'PASS', 'sha256': 'old'}))
    with pytest.raises(ValueError, match='stale'):
        load_assets(root, directory)


def test_server_only_serves_allowlisted_assets(research_files):
    root, directory = research_files
    with ThreadingHTTPServer(('127.0.0.1', 0), make_handler(root, directory)) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def request(route, method='GET', headers=None):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
                connection.request(method, route, headers=headers or {})
                response = connection.getresponse()
                result = response.status, dict(response.getheaders()), response.read()
                connection.close()
                return result
            status, headers, body = request('/workbook/download')
            assert status == 200 and body == (directory / 'Credit-Risk-Strategy-Lab-Private.xlsx').read_bytes()
            assert headers['Content-Disposition'].startswith('attachment;')
            assert headers['Cache-Control'] == 'no-store'
            assert request('/workbook/download', 'HEAD')[2] == b''
            assert request('/private-workbook/registry.json')[0] == 404
            assert request('/workbook/../registry.json')[0] == 404
            assert request('/%2e%2e/private-workbook/registry.json')[0] == 404
            assert request('/workbook/download', headers={'Host': 'attacker.invalid'})[0] == 403
            assert request('/workbook/download', headers={'Sec-Fetch-Site': 'cross-site'})[0] == 403
            (root / 'site/dist/data.json').write_text('{"pipeline_run":"changed-after-start"}')
            assert json.loads(request('/data.json')[2])['pipeline_run'] == 'test-run'
        finally:
            server.shutdown()
            thread.join(timeout=2)
