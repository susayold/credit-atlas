import hashlib
import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.nsmo_views import NsmoViews
from credit_atlas.server import handler_for


def _workspace(root: Path) -> Path:
    csv = root / "data/private/mortgage/nsmo-2026-05-27/puf/nsmo_v70_1324_puf.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text(
        "nsmoid,analysis_weight,perf_status_0313,perf_status_0613\n"
        "private-a,10,P,C\nprivate-b,20,C,1\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    receipts = root / "artifacts/private/nsmo-puf-20261015"
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "download-receipt.json").write_text(json.dumps({
        "dataset_release": "NSMO Public Use File v7.0, page updated 2026-05-27",
        "csv_sha256": digest,
        "csv_bytes": csv.stat().st_size,
    }), encoding="utf-8")
    (receipts / "data-audit.json").write_text(json.dumps({
        "status": "PASS",
        "csv_sha256": digest,
        "csv_bytes": csv.stat().st_size,
        "column_count": 4,
        "row_count": 2,
        "unique_nonblank_nsmoid": 2,
        "duplicate_nsmoid_rows": 0,
        "blank_nsmoid_rows": 0,
        "bad_width_rows": 0,
        "origination_year_counts": {"2013": 2},
        "origination_month_counts": {"1": 1, "2": 1},
        "survey_wave_counts": {"1": 2},
        "analysis_weight": {
            "valid_n": 2, "missing": 0, "invalid": 0, "nonpositive": 0,
            "min": 10, "median": 15, "max": 20, "sum": 30,
        },
        "performance": {
            "column_count": 2,
            "first_quarter_end": "2013-03-31",
            "last_quarter_end": "2013-06-30",
            "cell_count": 4,
            "unknown_status_counts": {},
            "quarterly_counts": [
                {
                    "quarter_end": "2013-03-31",
                    "status_counts_unweighted": {"P": 1, "C": 1},
                    "status_weight_sums_descriptive_only": {"P": 10, "C": 20},
                },
                {
                    "quarter_end": "2013-06-30",
                    "status_counts_unweighted": {"C": 1, "1": 1},
                    "status_weight_sums_descriptive_only": {"C": 10, "1": 20},
                },
            ],
        },
    }), encoding="utf-8")
    return csv


def test_nsmo_profile_is_hash_bound_and_aggregate_only(tmp_path):
    _workspace(tmp_path)
    result = NsmoViews(tmp_path).report()

    assert result["schema_version"] == "nsmo-profile-v1"
    assert result["sample"]["mortgages"] == 2
    assert result["performance"]["cell_count"] == 4
    assert result["performance"]["quarterly_counts"][0]["status_counts"] == {"P": 1, "C": 1}
    assert "private-a" not in json.dumps(result)
    assert "private-b" not in json.dumps(result)
    assert "at-risk denominator" in " ".join(result["limitations"])


def test_nsmo_profile_rejects_changed_source_even_with_cached_view(tmp_path):
    csv = _workspace(tmp_path)
    views = NsmoViews(tmp_path)
    views.report()
    old = csv.read_text(encoding="utf-8")
    csv.write_text(old.replace("private-a", "private-z"), encoding="utf-8")

    with pytest.raises(ValueError, match="no longer matches"):
        views.report()


def test_nsmo_profile_http_and_standalone_page(tmp_path):
    _workspace(tmp_path)
    source_web = Path(__file__).parents[1] / "apps" / "web"
    target_web = tmp_path / "apps" / "web"
    target_web.mkdir(parents=True)
    for name in ("nsmo.html", "nsmo.css", "nsmo.js"):
        shutil.copyfile(source_web / name, target_web / name)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=tmp_path)))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/nsmo", timeout=5) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert "D02 · SEPARATE NSMO CASE" in html
        with urlopen(base + "/api/nsmo-profile", timeout=5) as response:
            payload = json.loads(response.read())
            assert response.status == 200
            assert payload["status"] == "AVAILABLE"
            assert "private-a" not in json.dumps(payload)
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-profile?run=unexpected", timeout=5)
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
