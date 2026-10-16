from __future__ import annotations

import csv
import hashlib
import json
import shutil
import threading
import zipfile
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.mortgage_macro_context import report
from credit_atlas.server import handler_for


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def macro_root(tmp_path):
    folder = tmp_path / "data/private/public-context/fred-0123456789ab"
    folder.mkdir(parents=True)
    observations = {
        "UNRATE": [("2026-08-01", "4.2"), ("2026-09-01", "4.3")],
        "USSTHPI": [("2026-01-01", "745.0"), ("2026-04-01", "751.5")],
        "MORTGAGE30US": [("2026-10-08", "6.25"), ("2026-10-15", "6.20")],
    }
    metadata = []
    hashes = {}
    for series_id, values in observations.items():
        path = folder / f"{series_id}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["observation_date", series_id])
            writer.writerows(values)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[path.name] = digest
        metadata.append({
            "series_id": series_id,
            "source": "official source via FRED",
            "units": "Index" if series_id == "USSTHPI" else "Percent",
            "frequency": "source native",
            "seasonal_adjustment": "source native",
            "source_url": f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
            "metadata_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "retrieved_at": "2026-10-16T00:00:00+00:00",
            "bytes": path.stat().st_size,
            "sha256": digest,
            "observations": len(values),
            "missing_values": 0,
            "first_reference_date": values[0][0],
            "last_reference_date": values[-1][0],
            "model_predictor_qualified": False,
        })

    monthly_path = folder / "monthly-context.json"
    _write_json(monthly_path, {
        "case_id": "d01-a24484b21a21",
        "pipeline_run": "pipeline-0123456789ab",
        "rows": [
            {"reporting_month": "2026-02", "unemployment_percent_latest_revised": 4.1,
             "mortgage30_percent_monthly_mean": 6.15, "mortgage30_observations_in_month": 4},
            {"reporting_month": "2026-03", "unemployment_percent_latest_revised": 4.2,
             "mortgage30_percent_monthly_mean": 6.10, "mortgage30_observations_in_month": 5},
        ],
        "quarterly_hpi": [
            {"reference_quarter_start": "2026-01-01", "index_1980_q1_100": 745.0},
            {"reference_quarter_start": "2026-04-01", "index_1980_q1_100": 751.5},
        ],
    })
    hashes[monthly_path.name] = hashlib.sha256(monthly_path.read_bytes()).hexdigest()
    _write_json(folder / "run-complete.json", {
        "status": "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE",
        "completed_at": "2026-10-16T00:00:01+00:00",
        "case_id": "d01-a24484b21a21",
        "pipeline_run": "pipeline-0123456789ab",
        "series": metadata,
        "visibility": "private",
        "public_release_approved": False,
        "model_training_performed": False,
        "predictive_asof_qualified": False,
        "outputs_sha256": hashes,
    })
    return tmp_path


def test_macro_report_verifies_latest_values_and_native_case_grains(macro_root):
    result = report(macro_root)
    by_id = {item["series_id"]: item for item in result["series"]}
    assert result["status"] == "AVAILABLE"
    assert by_id["UNRATE"]["last_known_value"] == 4.3
    assert by_id["MORTGAGE30US"]["last_known_reference_date"] == "2026-10-15"
    assert by_id["MORTGAGE30US"]["last_known_value"] == 6.2
    assert by_id["USSTHPI"]["last_known_reference_date"] == "2026-04-01"
    assert result["case_alignment"] == {
        "monthly_rows": 2,
        "first_month": "2026-02",
        "last_month": "2026-03",
        "unemployment_months_available": 2,
        "mortgage_rate_months_available": 2,
        "hpi_quarters": 2,
    }
    assert result["monthly_history"][0]["period"] == "2026-02-01"
    assert result["point_in_time_context"] is None
    assert result["limitations"] and "not establish historical publication availability" in result["limitations"][0]


def _write_alfred_fixture(root: Path) -> Path:
    folder = root / "data/private/public-context/alfred-asof-20261016T010000Z"
    folder.mkdir(parents=True)
    month_map = {
        "UNRATE": {"2026-02": "2026-02-06", "2026-03": "2026-03-06"},
        "MORTGAGE30US": {"2026-02": "2026-02-26", "2026-03": "2026-03-26"},
        "USSTHPI": {"2026-02": "2026-02-24", "2026-03": "2026-03-24"},
    }
    matrices = {
        "UNRATE": {
            "2026-02-06": [("2026-01-01", "4.0")],
            "2026-03-06": [("2026-01-01", "4.0"), ("2026-02-01", "4.1")],
        },
        "MORTGAGE30US": {
            "2026-02-26": [("2026-02-05", "6.0"), ("2026-02-12", "6.2")],
            "2026-03-26": [("2026-03-05", "6.4"), ("2026-03-12", "6.6")],
        },
        "USSTHPI": {
            "2026-02-24": [("2025-10-01", "700.0")],
            "2026-03-24": [("2025-10-01", "700.0"), ("2026-01-01", "705.0")],
        },
    }
    series_receipts = {}
    for series_id, monthly_vintage_map in month_map.items():
        vintages = sorted(set(monthly_vintage_map.values()))
        by_period = {}
        for vintage, rows in matrices[series_id].items():
            for period, value in rows:
                by_period.setdefault(period, {})[vintage] = value
        path = folder / f"{series_id.lower()}-001.zip"
        csv_name = f"vintages_starting_{vintages[0]}.csv"
        import io
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["observation_date", *[f"{series_id}_{v.replace('-', '')}" for v in vintages]])
        for period in sorted(by_period):
            writer.writerow([period, *[by_period[period].get(v, ".") for v in vintages]])
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(csv_name, out.getvalue())
        series_receipts[series_id] = {
            "source_url": f"https://alfred.stlouisfed.org/series/downloaddata?seid={series_id}",
            "selected_vintages": vintages,
            "available_vintage_dates": len(vintages),
            "monthly_vintage_map": monthly_vintage_map,
            "batches": [{
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "vintages": vintages,
                "csv_member": csv_name,
                "observation_rows": len(by_period),
                "vintage_columns": len(vintages),
            }],
        }
    _write_json(folder / "manifest.json", {
        "status": "DOWNLOADED_AND_VALIDATED",
        "completed_at": "2026-10-16T01:00:00+00:00",
        "visibility": "private",
        "source": "ALFRED, Federal Reserve Bank of St. Louis",
        "source_help_url": "https://alfred.stlouisfed.org/help/downloaddata",
        "case_months": ["2026-02", "2026-03"],
        "cutoff_rule": "Latest ALFRED vintage on or before month end",
        "predictor_qualified": False,
        "model_training_performed": False,
        "series": series_receipts,
    })
    return folder


def test_alfred_report_uses_only_values_available_by_each_month_end(macro_root):
    _write_alfred_fixture(macro_root)
    result = report(macro_root)["point_in_time_context"]
    assert result["status"] == "AVAILABLE"
    assert result["coverage"] == {
        "monthly_rows": 2,
        "first_month": "2026-02",
        "last_month": "2026-03",
        "unemployment_months_available": 2,
        "mortgage_rate_months_available": 2,
        "hpi_months_available": 2,
    }
    feb, mar = result["monthly_history"]
    assert feb["as_of_date"] == "2026-02-28"
    assert feb["unemployment_reference_date"] == "2026-01-01"
    assert feb["unemployment_percent"] == 4.0
    assert feb["mortgage30_monthly_mean_percent"] == 6.1
    assert feb["mortgage30_observation_count"] == 2
    assert feb["hpi_reference_date"] == "2025-10-01"
    assert mar["unemployment_reference_date"] == "2026-02-01"
    assert mar["mortgage30_monthly_mean_percent"] == 6.5
    assert mar["hpi_reference_date"] == "2026-01-01"


def test_alfred_report_fails_closed_on_archive_digest_mismatch(macro_root):
    folder = _write_alfred_fixture(macro_root)
    archive = folder / "unrate-001.zip"
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="failed its receipt digest"):
        report(macro_root)


def test_macro_report_fails_closed_on_source_digest_mismatch(macro_root):
    source = macro_root / "data/private/public-context/fred-0123456789ab/MORTGAGE30US.csv"
    source.write_text(source.read_text(encoding="utf-8") + "2026-10-22,6.1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="output failed its receipt digest"):
        report(macro_root)


def test_macro_report_does_not_fallback_from_newer_corrupt_successful_run(macro_root):
    newest = macro_root / "data/private/public-context/fred-ffffffffffff"
    newest.mkdir()
    _write_json(newest / "run-complete.json", {
        "status": "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE",
        "completed_at": "2026-10-17T00:00:00+00:00",
        "visibility": "private",
        "public_release_approved": False,
        "model_training_performed": False,
        "predictive_asof_qualified": False,
        "series": [],
        "outputs_sha256": {},
    })
    with pytest.raises(ValueError, match="no output digests"):
        report(macro_root)


@pytest.fixture
def macro_api(macro_root):
    web = macro_root / "apps/web"
    web.mkdir(parents=True)
    source = Path(__file__).parents[1] / "apps/web/app.js"
    shutil.copyfile(source, web / "app.js")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=macro_root)))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_macro_api_is_unfiltered_and_sources_view_exposes_context(macro_api):
    with urlopen(macro_api + "/api/mortgage-macro-context", timeout=5) as response:
        result = json.loads(response.read())
    assert result["status"] == "AVAILABLE"
    assert len(result["series"]) == 3
    with pytest.raises(HTTPError) as error:
        urlopen(macro_api + "/api/mortgage-macro-context?series=UNRATE", timeout=5)
    assert error.value.code == 400
    with urlopen(macro_api + "/app.js", timeout=5) as response:
        source = response.read().decode("utf-8")
    assert "Mortgage macro context · US national" in source
    assert "ALFRED · Lịch sử theo thông tin đã công bố tại thời điểm đó" in source
    assert "/api/mortgage-macro-context" in source
