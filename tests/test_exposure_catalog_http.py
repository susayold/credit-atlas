import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.server import handler_for


@pytest.mark.parametrize(
    ("route", "query_key", "view_name"),
    [
        ("/api/exposure-convergence-studies", "source_import_id", "exposure_convergence_views"),
        ("/api/exposure-tail-studies", "source_import_id", "exposure_tail_views"),
        ("/api/exposure-ecl-studies", "source_import_id", "exposure_ecl_views"),
        ("/api/exposure-scenarios", "source_import_id", "exposure_scenario_views"),
        ("/api/exposure-movements", "closing_import_id", "exposure_movement_views"),
    ],
)
def test_portfolio_study_catalog_http_routes_are_scoped_and_fail_closed(
    tmp_path, route, query_key, view_name,
):
    source_id = "exposure-import-test"
    payload = {"source_import_id": source_id, "studies": [], "status": "AVAILABLE"}
    view = SimpleNamespace(catalog=lambda selected: payload if selected == source_id else {})
    service = SimpleNamespace(root=tmp_path, exposure_views=SimpleNamespace())
    setattr(service, view_name, view)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base}{route}?{query_key}={source_id}") as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert json.load(response) == payload
        with pytest.raises(HTTPError) as error:
            urlopen(f"{base}{route}?{query_key}={source_id}&path=other")
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(f"{base}{route}")
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
