import csv
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

from credit_atlas.cfpb_mortgage_trends import FILES, MONTHS, read
from credit_atlas.server import handler_for


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FOLDER = ROOT / "data" / "private" / "public-context" / "cfpb-mortgage-performance-trends-2026-08"


def _fixture(root):
    folder = root / "data" / "private" / "public-context" / "cfpb-mortgage-performance-trends-test"
    folder.mkdir(parents=True)
    profiles = []
    for kind, metric_files in FILES.items():
        for metric, filename in metric_files.items():
            fields = (["RegionType", "State", "Name", "FIPSCode"] if kind == "county"
                      else ["RegionType", "Name", "FIPSCode"]) + MONTHS
            if kind == "county":
                meta = [("National", "", "United States", "-----"),
                        ("County", "AL", "Baldwin County", "'01003'")]
            else:
                meta = [("National", "United States", "-----"), ("State", "Alabama", "'01'")]
            rows = []
            for index, values in enumerate(meta):
                row = dict(zip(fields[:len(values)], values))
                row.update({month: str((3.5 if metric == "30_89" else 1.5) + index) for month in MONTHS})
                rows.append(row)
            path = folder / filename
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            raw = path.read_bytes()
            profiles.append({"file": filename, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                             "rows_including_national": len(rows)})
    (folder / "receipt.json").write_text(json.dumps({
        "source": "CFPB Mortgage Performance Trends", "official_published_date": "2026-08",
        "profiles": profiles,
    }), encoding="utf-8")
    return folder


def test_acquired_cfpb_series_profiles_and_returns_monthly_national_context():
    if not SOURCE_FOLDER.is_dir():
        pytest.skip("Raw CFPB data are intentionally excluded from the public repository")
    result = read(ROOT)
    assert result["status"] == "AVAILABLE"
    assert result["first_period"] == "2008-01" and result["last_period"] == "2025-12"
    assert result["quality"]["monthly_periods"] == 216
    assert result["quality"]["county_geographies"] == 507
    assert result["quality"]["state_geographies"] == 51
    assert result["selected_geography"] == {
        "geography_type": "National", "geoid": "-----", "name": "United States", "state": ""
    }
    assert result["rows"][0] == {
        "period": "2008-01", "delinquent_30_89_percent": 3.5, "delinquent_90plus_percent": 1.5
    }
    assert result["rows"][-1]["period"] == "2025-12"
    assert result["rows"][-1]["delinquent_30_89_percent"] == 2.1
    assert result["rows"][-1]["delinquent_90plus_percent"] == 0.9


def test_selected_county_normalizes_fips_text_without_losing_leading_zeroes(tmp_path):
    _fixture(tmp_path)
    result = read(tmp_path, {"geography_type": "County", "geoid": "01003"})
    assert result["selected_geography"]["name"] == "Baldwin County"
    assert result["selected_geography"]["state"] == "AL"
    assert len(result["rows"]) == 216
    assert result["quality"]["selected_source_hashes"].keys() == {"30_89", "90_plus"}


def test_unlisted_query_and_tampered_source_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="accepts geography_type and geoid only"):
        read(ROOT, {"metric": "30_89"})
    source = _fixture(tmp_path)
    county = source / "CountyMortgagesPercent-30-89DaysLate-thru-2025-12.csv"
    county.write_bytes(county.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="hash differs from acquisition receipt"):
        read(tmp_path)


def test_cfpb_mortgage_http_view_and_report_contract(tmp_path):
    source = _fixture(tmp_path)
    web = tmp_path / "apps" / "web"
    web.mkdir(parents=True)
    shutil.copyfile(ROOT / "apps" / "web" / "app.js", web / "app.js")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(
        root=tmp_path, cfpb_mortgage_trends=lambda query: read(tmp_path, query)
    )))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        query = "?geography_type=County&geoid=01003"
        with urlopen(base + "/api/cfpb-mortgage-trends" + query, timeout=5) as response:
            view = json.loads(response.read())
            assert response.status == 200
            assert response.headers.get_content_type() == "application/json"
        assert view["status"] == "AVAILABLE"
        assert view["selected_geography"]["geoid"] == "01003"
        assert len(view["rows"]) == 216
        assert "Baldwin County" in json.dumps(view)

        with urlopen(base + "/api/cfpb-mortgage-trends-report" + query, timeout=5) as response:
            report_payload = json.loads(response.read())
            assert response.status == 200
            assert "CFPB-Mortgage-Performance-Trends-private-context.json" in response.headers[
                "Content-Disposition"
            ]
        assert report_payload == view
        assert report_payload["visibility"] == "private"
        assert "private" not in json.dumps(report_payload.get("rows", []))

        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/cfpb-mortgage-trends?metric=30_89", timeout=5)
        assert error.value.code == 400

        county = source / FILES["county"]["30_89"]
        county.write_bytes(county.read_bytes() + b"\n")
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/cfpb-mortgage-trends-report" + query, timeout=5)
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
