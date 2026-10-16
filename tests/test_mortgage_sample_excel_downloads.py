from __future__ import annotations

import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas.server import MORTGAGE_SAMPLE_WORKBOOKS, handler_for


ROOT = Path(__file__).parents[1]


@pytest.fixture
def app_server(tmp_path):
    web = tmp_path / "apps/web"
    web.mkdir(parents=True)
    shutil.copyfile(ROOT / "apps/web/app.js", web / "app.js")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=tmp_path)))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


@pytest.mark.parametrize("route,download", MORTGAGE_SAMPLE_WORKBOOKS.items())
def test_local_excel_downloads_are_fixed_private_files(app_server, tmp_path, route, download):
    relative, filename = download
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = b"PK\x03\x04" + filename.encode("ascii")
    target.write_bytes(payload)

    with urlopen(app_server + route, timeout=5) as response:
        assert response.status == 200
        assert response.headers.get_content_type() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert filename in response.headers["Content-Disposition"]
        assert response.read() == payload

    request = Request(app_server + route, method="HEAD")
    with urlopen(request, timeout=5) as response:
        assert response.status == 200
        assert int(response.headers["Content-Length"]) == len(payload)
        assert response.read() == b""

    with pytest.raises(HTTPError) as error:
        urlopen(app_server + route + "?path=../../secret", timeout=5)
    assert error.value.code == 400


def test_missing_workbook_returns_404_without_fallback(app_server):
    with pytest.raises(HTTPError) as error:
        urlopen(app_server + "/downloads/ginnie-public-samples.xlsx", timeout=5)
    assert error.value.code == 404


def test_mortgage_source_view_exposes_excel_library_downloads(app_server):
    with urlopen(app_server + "/app.js", timeout=5) as response:
        source = response.read().decode("utf-8")
    assert "Excel sample & codebook library" in source
    for route in MORTGAGE_SAMPLE_WORKBOOKS:
        assert route in source
    assert "/downloads/alfred-macro-context.xlsx" in source
    assert "95,395 vintage" in source
    assert "không phải annual vintage" in source
    assert "giữ source/population riêng" in source


def test_alfred_macro_context_workbook_download_is_fixed_local_file(app_server, tmp_path):
    workbook = tmp_path / "apps/excel/templates/CreditAtlas-ALFRED-Macro-Context.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    payload = b"PK\x03\x04ALFRED"
    workbook.write_bytes(payload)

    with urlopen(app_server + "/downloads/alfred-macro-context.xlsx", timeout=5) as response:
        assert response.status == 200
        assert response.headers.get_content_type() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "CreditAtlas-ALFRED-Macro-Context.xlsx" in response.headers["Content-Disposition"]
        assert response.read() == payload

    with pytest.raises(HTTPError) as error:
        urlopen(app_server + "/downloads/alfred-macro-context.xlsx?path=../../secret", timeout=5)
    assert error.value.code == 400
