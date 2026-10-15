import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.server import handler_for


def _serve(tmp_path, service):
    service.root = tmp_path
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    return server, worker, f"http://127.0.0.1:{server.server_port}"


@pytest.mark.parametrize(
    ("route", "query", "service_name", "method", "args"),
    [
        ("/api/hmda-views", "", "hmda_views", "catalog", ()),
        ("/api/hmda-references", "source_id=hmda-source-x", "hmda_reference_views", "catalog", ("hmda-source-x",)),
        ("/api/hmda-cohorts", "case_id=hmda-case-x", "hmda_cohort_views", "catalog", ("hmda-case-x",)),
        ("/api/sec-views", "", "sec_views", "catalog", ()),
        ("/api/market-views", "", "market_views", "catalog", ()),
    ],
)
def test_workspace_catalog_http_routes_return_payload_and_reject_bad_filters(
    tmp_path, route, query, service_name, method, args,
):
    payload = {"status": "AVAILABLE", "items": []}
    calls = []
    view = SimpleNamespace(**{method: lambda *selected: (calls.append(selected), payload)[1]})
    service = SimpleNamespace(**{service_name: view})
    server, worker, base = _serve(tmp_path, service)
    try:
        with urlopen(f"{base}{route}?{query}" if query else f"{base}{route}") as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert json.load(response) == payload
        assert calls == [args]
        bad_query = "?extra=1" if not query else f"?{query}&extra=1"
        with pytest.raises(HTTPError) as error:
            urlopen(f"{base}{route}{bad_query}")
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize(
    ("route", "view_name"),
    [("/api/sec-view", "sec_views"), ("/api/market-view", "market_views")],
)
def test_workspace_snapshot_http_routes_require_exact_view_id(tmp_path, route, view_name):
    view_id = f"{view_name}-test"
    payload = {"view_id": view_id, "status": "AVAILABLE"}
    calls = []
    view = SimpleNamespace(view=lambda selected: (calls.append(selected), payload)[1])
    service = SimpleNamespace(**{view_name: view})
    server, worker, base = _serve(tmp_path, service)
    try:
        with urlopen(f"{base}{route}?view_id={view_id}") as response:
            assert response.status == 200
            assert json.load(response) == payload
        assert calls == [view_id]
        with pytest.raises(HTTPError) as error:
            urlopen(f"{base}{route}?view_id={view_id}&extra=1")
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(f"{base}{route}")
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize(
    ("route", "query", "service_name", "method", "identifier", "attachment"),
    [
        ("/api/hmda-report", "view_id=hmda-view-x", "hmda_views", "report", "hmda-view-x", True),
        ("/api/hmda-labeled-report", "reference_id=ref-x&source_id=source-x", "hmda_reference_views", "report", "ref-x", True),
        ("/api/sec-report", "view_id=sec-view-x", "sec_views", "report", "sec-view-x", True),
        ("/api/market-report", "view_id=market-view-x&series=DGS2", "market_views", "report", "market-view-x", True),
        ("/api/market-daily", "view_id=market-view-x&series=DGS2", "market_views", "daily", "market-view-x", False),
    ],
)
def test_report_and_daily_http_routes_preserve_query_and_response_contract(
    tmp_path, route, query, service_name, method, identifier, attachment,
):
    payload = {"case_id": identifier, "view_id": identifier, "status": "AVAILABLE"}
    calls = []
    report = lambda selected, filters: (calls.append((selected, filters)), payload)[1]
    view = SimpleNamespace(**{method: report})
    service = SimpleNamespace(**{service_name: view})
    server, worker, base = _serve(tmp_path, service)
    try:
        with urlopen(f"{base}{route}?{query}") as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert json.load(response) == payload
            disposition = response.headers.get("Content-Disposition", "")
            assert ("attachment" in disposition) is attachment
        from urllib.parse import parse_qs

        expected_query = {key: value[0] for key, value in parse_qs(query).items()}
        assert calls == [(identifier, expected_query)]
        if route == "/api/hmda-labeled-report":
            with pytest.raises(HTTPError) as error:
                urlopen(f"{base}{route}?source_id=source-x")
            assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
