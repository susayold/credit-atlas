from __future__ import annotations

import csv
import hashlib
import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas.fed_bank_mortgage_context import RELEASE, SERIES as CONFIGURED_SERIES, report
from credit_atlas.server import handler_for


PERIODS = ["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]


def _fixture_root(tmp_path: Path) -> Path:
    folder = tmp_path / "data/private/public-context/fed-bank-mortgage-asset-quality-test"
    folder.mkdir(parents=True)
    metadata = {}
    for index, series_id in enumerate(CONFIGURED_SERIES):
        values = [str(index + 1 + offset / 10) for offset in range(4)]
        if series_id.startswith("COR"):
            values[1] = "-0.02"
        path = folder / f"{series_id}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["observation_date", series_id])
            writer.writerows(zip(PERIODS, values))
        raw = path.read_bytes()
        metadata[series_id] = {
            "source_url": f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
            "metadata_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "observations": len(values), "first_reference_date": PERIODS[0],
            "last_reference_date": PERIODS[-1], "sha256": hashlib.sha256(raw).hexdigest(),
        }
    manifest = {
        "status": "DOWNLOADED_AND_VALIDATED", "visibility": "private",
        "predictor_qualified": False, "model_training_performed": False,
        "source": "Board of Governors of the Federal Reserve System via FRED",
        "release": RELEASE, "release_url": "https://www.federalreserve.gov/releases/ChargeOff/",
        "retrieved_at": "2026-10-16T00:00:00+00:00",
        "completed_at": "2026-10-16T00:00:01+00:00",
        "latest_common_reference_date": PERIODS[-1], "series": metadata,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


@pytest.fixture
def app_server(tmp_path):
    web = tmp_path / "apps/web"
    web.mkdir(parents=True)
    shutil.copyfile(Path(__file__).parents[1] / "apps/web/app.js", web / "app.js")
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


def test_fed_bank_mortgage_context_validates_native_quarterly_series(tmp_path):
    result = report(_fixture_root(tmp_path))
    assert result["status"] == "AVAILABLE"
    assert result["first_period"] == "2025-01-01"
    assert result["last_period"] == "2025-10-01"
    assert result["quarter_count"] == 4
    assert result["rows"][-1]["DRSFRMACBS"] == 1.3
    assert result["rows"][1]["CORSFRMACBS"] == -0.02
    assert len(result["series"]) == 10
    assert len(result["products"]) == 5
    mortgage = next(s for s in result["series"] if s["series_id"] == "DRSFRMACBS")
    assert mortgage["historical_high_value"] == 1.3
    assert mortgage["historical_high_date"] == "2025-10-01"
    assert mortgage["historical_percentile"] == 100
    assert "not borrower-level records" in result["limitations"][0]


def test_fed_bank_mortgage_context_fails_closed_on_hash_mismatch(tmp_path):
    root = _fixture_root(tmp_path)
    path = root / "data/private/public-context/fed-bank-mortgage-asset-quality-test/CORSFRMACBS.csv"
    path.write_text(path.read_text(encoding="utf-8") + "", encoding="utf-8")
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest or URL"):
        report(root)


def test_fed_bank_mortgage_api_and_fixed_workbook_download(app_server, tmp_path):
    _fixture_root(tmp_path)
    workbook = tmp_path / "apps/excel/templates/CreditAtlas-Fed-Bank-Asset-Quality.xlsx"
    workbook.parent.mkdir(parents=True)
    payload = b"PK\x03\x04FedBank"
    workbook.write_bytes(payload)

    with urlopen(app_server + "/api/fed-bank-mortgage-context", timeout=5) as response:
        body = json.loads(response.read())
        assert response.status == 200
        assert body["quarter_count"] == 4
        assert body["rows"][1]["CORSFRMACBS"] == -0.02
    with urlopen(app_server + "/downloads/fed-bank-mortgage-context.xlsx", timeout=5) as response:
        assert response.status == 200
        assert response.read() == payload
        assert "CreditAtlas-Fed-Bank-Asset-Quality.xlsx" in response.headers["Content-Disposition"]
    with pytest.raises(HTTPError) as error:
        urlopen(app_server + "/api/fed-bank-mortgage-context?unexpected=1", timeout=5)
    assert error.value.code == 400
    with pytest.raises(HTTPError) as error:
        urlopen(app_server + "/downloads/fed-bank-mortgage-context.xlsx?path=../../secret", timeout=5)
    assert error.value.code == 400


def test_fed_bank_quality_excel_library_entry_is_present(app_server):
    with urlopen(app_server + "/app.js", timeout=5) as response:
        source = response.read().decode("utf-8")
    assert "/api/fed-bank-mortgage-context" in source
    assert "/downloads/fed-bank-mortgage-context.xlsx" in source
    assert "10 quarterly series across mortgages, cards, consumer, CRE and business loans" in source
