import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from credit_atlas.server import handler_for
from tests.test_business_archive import graph


def test_private_archive_http_export_scope_and_origin(graph):
    views = SimpleNamespace(root=graph, view=lambda _: {'business': {'business_id': 'business-sba-21c568f10f7d'}})
    service = SimpleNamespace(root=graph, suite_views=views)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base + '/api/business-archive?view_id=test') as response:
            r = json.load(response)
            assert r['records'] == 18 and r['view_id'] == 'test'
            assert 'no-store' in response.headers['Cache-Control']
        with urlopen(base + '/api/business-archive-report?view_id=test') as response:
            assert json.load(response) == r
            assert 'attachment' in response.headers['Content-Disposition']
        for suffix in ['', '?view_id=test&program=7A']:
            with pytest.raises(HTTPError) as error: urlopen(base + '/api/business-archive' + suffix)
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + '/api/business-archive?view_id=test', headers={'Origin': 'https://outside.example'}))
        assert error.value.code == 403
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
