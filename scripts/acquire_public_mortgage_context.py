"""Acquire public macro sources and build retrospective mortgage context."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import shutil
import statistics
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.request import Request, urlopen

import pyarrow as pa
import pyarrow.parquet as pq

from credit_atlas.service import ResearchService
from credit_atlas.fhfa_hpi import normalize_us_census_hpi_csv
from credit_atlas.workspace import app_root, sha256, timestamp, write_new

SPECS = {
    "UNRATE": {"source": "U.S. Bureau of Labor Statistics via FRED", "units": "Percent",
               "frequency": "Monthly", "seasonal_adjustment": "Seasonally Adjusted"},
    "USSTHPI": {"source": "Federal Housing Finance Agency (direct)",
                "units": "Index 1980:Q1=100", "frequency": "Quarterly",
                "seasonal_adjustment": "Not Seasonally Adjusted"},
    "MORTGAGE30US": {"source": "Freddie Mac via FRED", "units": "Percent",
                     "frequency": "Weekly, Ending Thursday", "seasonal_adjustment": "Not Seasonally Adjusted"},
}
LIMIT = 2 * 1024**2
FHFA_US_CENSUS_HPI_URL = "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_us_and_census.csv"
FHFA_HPI_DATASET_URL = "https://www.fhfa.gov/data/hpi/datasets?tab=master-hpi-data"
FHFA_HPI_FAQ_URL = "https://www.fhfa.gov/document/hpi-faqs"


def parse_csv(raw, series):
    if series not in SPECS:
        raise ValueError("Unconfigured public series")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != ["observation_date", series]:
        raise ValueError("Unexpected FRED CSV schema")
    result, previous = [], None
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed FRED record")
        observed = date.fromisoformat(row["observation_date"])
        if previous is not None and observed <= previous:
            raise ValueError("Duplicate or unordered observation dates")
        previous = observed
        if series == "UNRATE" and observed.day != 1:
            raise ValueError("Unexpected monthly reference date")
        if series == "USSTHPI" and (observed.day != 1 or observed.month not in (1, 4, 7, 10)):
            raise ValueError("Unexpected quarterly reference date")
        value = None if row[series] in ("", ".") else float(row[series])
        if value is not None and (not math.isfinite(value) or value < 0
                                  or series != "USSTHPI" and value > 100):
            raise ValueError("Invalid source numeric value")
        result.append({"series_id": series, "observation_date": observed, "value": value})
    if not result:
        raise ValueError("Empty source series")
    return result


def fetch(series, folder):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series
    for attempt in range(1, 4):
        try:
            # Native Windows HTTP transport; fixed official URLs, no redirects,
            # credentials, shell interpolation or persisted session cookies.
            response = subprocess.run(
                ["curl.exe", "--fail", "--silent", "--show-error", "--proto", "=https",
                 "--max-time", "45", "--max-filesize", str(LIMIT),
                 "--write-out", "\n%{http_code}", url],
                capture_output=True, timeout=50, check=False)
            if response.returncode:
                if attempt < 3 and response.returncode in (6, 7, 28, 35, 56):
                    continue
                raise RuntimeError(f"Public HTTP download failed (curl exit {response.returncode})")
            raw, status = response.stdout.rsplit(b"\n", 1)
            if status != b"200":
                raise ValueError("Unexpected public source HTTP status")
            if len(raw) > LIMIT:
                raise ValueError("Public source exceeds download bound")
            break
        except subprocess.TimeoutExpired:
            if attempt == 3:
                raise
    records = parse_csv(raw, series)
    file = folder / (series + ".csv")
    with file.open("xb") as stream:
        stream.write(raw)
    metadata = {**SPECS[series], "series_id": series, "source_url": url,
                "metadata_url": "https://fred.stlouisfed.org/series/" + series,
                "retrieved_at": timestamp(), "download_attempts": attempt,
                "http_transport": "curl.exe_https_no_redirects", "bytes": len(raw), "sha256": sha256(file),
                "observations": len(records), "missing_values": sum(row["value"] is None for row in records),
                "first_reference_date": records[0]["observation_date"].isoformat(),
                "last_reference_date": records[-1]["observation_date"].isoformat(),
                "information_availability": "latest_revised_snapshot_not_historical_release_vintages",
                "model_predictor_qualified": False}
    return records, metadata


def fetch_fhfa_us_hpi(folder):
    """Acquire the official national All-Transactions HPI and normalize USA rows."""
    request = Request(FHFA_US_CENSUS_HPI_URL, headers={
        "User-Agent": "CreditAtlas public-data research/1.0",
        "Accept": "text/csv",
    })
    with urlopen(request, timeout=45) as response:
        if response.status != 200 or response.geturl() != FHFA_US_CENSUS_HPI_URL:
            raise ValueError("FHFA HPI request returned an unexpected status or redirect")
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/csv" not in content_type:
            raise ValueError("FHFA HPI response is not CSV")
        raw = response.read(LIMIT + 1)
        headers = {name: response.headers.get(name) for name in ("ETag", "Last-Modified", "Content-Length")
                   if response.headers.get(name) is not None}
    if not raw or len(raw) > LIMIT:
        raise ValueError("FHFA HPI source is empty or exceeds the download bound")

    source_path = folder / "fhfa-us-census-hpi-source.csv"
    with source_path.open("xb") as stream:
        stream.write(raw)
    parsed = normalize_us_census_hpi_csv(source_path)
    national = [row for row in parsed.records if row[0] == "USA"]
    if len(national) != parsed.period_count:
        raise ValueError("FHFA national HPI series is not balanced")

    normalized_path = folder / "USSTHPI.csv"
    normalized = io.StringIO(newline="")
    writer = csv.writer(normalized, lineterminator="\n")
    writer.writerow(["observation_date", "USSTHPI"])
    records = []
    for _, year, quarter, value in national:
        observed = date(year, (quarter - 1) * 3 + 1, 1)
        writer.writerow([observed.isoformat(), f"{value:.2f}"])
        records.append({"series_id": "USSTHPI", "observation_date": observed, "value": value})
    normalized_bytes = normalized.getvalue().encode("utf-8")
    with normalized_path.open("xb") as stream:
        stream.write(normalized_bytes)

    metadata = {
        **SPECS["USSTHPI"],
        "series_id": "USSTHPI",
        "source_url": FHFA_US_CENSUS_HPI_URL,
        "metadata_url": FHFA_HPI_DATASET_URL,
        "rights_evidence_url": FHFA_HPI_FAQ_URL,
        "rights_review_status": "FHFA_SAYS_DATA_FREELY_AVAILABLE; ATTRIBUTION_RECOMMENDED; NO_HISTORICAL_RELEASE_VINTAGES",
        "attribution": "Source: FHFA HPI® (all-transactions, U.S., not seasonally adjusted, nominal).",
        "retrieved_at": timestamp(),
        "http_status": 200,
        "http_transport": "python_urllib_https_no_redirect",
        "response_headers": headers,
        "source_object_file": source_path.name,
        "source_object_bytes": len(raw),
        "source_object_sha256": sha256(source_path),
        "bytes": normalized_path.stat().st_size,
        "sha256": sha256(normalized_path),
        "observations": len(records),
        "missing_values": 0,
        "first_reference_date": records[0]["observation_date"].isoformat(),
        "last_reference_date": records[-1]["observation_date"].isoformat(),
        "snapshot_as_of": parsed.latest_period,
        "index_type": "All-Transactions",
        "geography": "U.S. national (FHFA code USA)",
        "seasonal_adjustment": "Not Seasonally Adjusted",
        "index_base": "1980Q1=100",
        "information_availability": "Current FHFA release; historical release vintage/publication availability not preserved",
        "model_predictor_qualified": False,
    }
    return records, metadata


def reuse_existing_fred_series(source_folder, destination_folder, receipt):
    """Copy only the prior FRED snapshots; never make new FRED requests."""
    metadata_by_id = {row.get("series_id"): row for row in receipt.get("series", [])
                      if isinstance(row, dict)}
    if not {"UNRATE", "MORTGAGE30US"}.issubset(metadata_by_id):
        raise ValueError("Latest macro receipt is missing reusable FRED series metadata")
    downloads = []
    for series_id in ("UNRATE", "MORTGAGE30US"):
        metadata = metadata_by_id[series_id]
        expected_url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id
        if metadata.get("source_url") != expected_url:
            raise ValueError("Existing FRED snapshot has an unexpected source URL")
        source_path = source_folder / (series_id + ".csv")
        if not source_path.is_file() or sha256(source_path) != metadata.get("sha256"):
            raise ValueError("Existing FRED snapshot failed its receipt digest check")
        destination_path = destination_folder / source_path.name
        shutil.copyfile(source_path, destination_path)
        if sha256(destination_path) != metadata["sha256"]:
            raise ValueError("Copied FRED snapshot failed its receipt digest check")
        downloads.append((parse_csv(destination_path.read_bytes(), series_id), metadata))
    return downloads


def _complete_run(service, case_id, snapshot, folder, records, metadata):
    schema = pa.schema([("series_id", pa.string()), ("observation_date", pa.date32()), ("value", pa.float64())])
    pq.write_table(pa.Table.from_pylist(records, schema=schema), folder / "native-series.parquet", compression="zstd")
    months = [row["period"][:7] for row in snapshot["snapshot"]["monthly"]]
    context = monthly_context(months, records)
    write_new(folder / "monthly-context.json", {
        "case_id": case_id, "pipeline_run": snapshot["pipeline_run"], "rows": context,
        "quarterly_hpi": [{"reference_quarter_start": row["observation_date"].isoformat(),
                          "index_1980_q1_100": row["value"]}
                         for row in records if row["series_id"] == "USSTHPI"
                         and months[0] <= row["observation_date"].isoformat()[:7] <= months[-1]],
        "use": "retrospective_descriptive_context_only",
        "limitations": ["Latest revised snapshots do not prove historical publication availability.",
                       "Quarterly HPI stays quarterly; no monthly interpolation.",
                       "Monthly mortgage rate is the mean of source weekly observations in that month.",
                       "PMMS methodology changed on 2022-11-17; do not assume one unchanged measurement regime.",
                       "No borrower identification, causal economic effect or model prediction is inferred.",
                       "Macro series do not replace annual mortgage origination/performance samples."]})
    service.case(case_id)
    receipt = {"status": "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE", "completed_at": timestamp(),
               "case_id": case_id, "pipeline_run": snapshot["pipeline_run"],
               "series": metadata, "total_native_observations": len(records),
               "monthly_context_rows": len(context),
               "unemployment_months_available": sum(row["unemployment_percent_latest_revised"] is not None for row in context),
               "mortgage_rate_months_available": sum(row["mortgage30_percent_monthly_mean"] is not None for row in context),
               "loan_vintages_added": [], "model_training_performed": False,
               "predictive_asof_qualified": False, "visibility": "private", "public_release_approved": False,
               "outputs_sha256": {path.name: sha256(path) for path in folder.iterdir() if path.is_file()}}
    write_new(folder / "run-complete.json", receipt)
    return {"data_directory": str(folder), **{key: receipt[key] for key in
            ("status", "total_native_observations", "monthly_context_rows", "model_training_performed")},
            "series": [{key: info[key] for key in ("series_id", "observations", "last_reference_date")}
                       for info in metadata]}


def monthly_context(months, records):
    unemployment = {row["observation_date"].isoformat()[:7]: row["value"]
                    for row in records if row["series_id"] == "UNRATE"}
    weekly = {}
    for row in records:
        if row["series_id"] == "MORTGAGE30US" and row["value"] is not None:
            weekly.setdefault(row["observation_date"].isoformat()[:7], []).append(row["value"])
    return [{"reporting_month": month, "unemployment_percent_latest_revised": unemployment.get(month),
             "mortgage30_percent_monthly_mean": statistics.mean(weekly[month]) if month in weekly else None,
             "mortgage30_observations_in_month": len(weekly.get(month, []))}
            for month in months]


def run(root, case_id="d01-a24484b21a21"):
    if root.resolve().drive.upper() != "D:":
        raise ValueError("Downloaded data must remain on D:")
    service = ResearchService(root)
    snapshot = service.snapshot(case_id)
    folder = root / "data/private/public-context" / ("fred-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    write_new(folder / "run-start.json", {"started_at": timestamp(), "case_id": case_id,
              "intent": "download_and_run_retrospective_macro_context", "series_ids": list(SPECS)})
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            downloads = [
                pool.submit(fetch, "UNRATE", folder),
                pool.submit(fetch_fhfa_us_hpi, folder),
                pool.submit(fetch, "MORTGAGE30US", folder),
            ]
            downloads = [future.result() for future in downloads]
        records = [row for result, _ in downloads for row in result]
        metadata = [info for _, info in downloads]
        return _complete_run(service, case_id, snapshot, folder, records, metadata)
    except Exception as error:
        write_new(folder / "run-failed.json", {"status": "FAIL", "failed_at": timestamp(),
                   "exception_type": type(error).__name__, "model_training_performed": False})
        raise


def run_fhfa_hpi_refresh(root, case_id="d01-a24484b21a21"):
    """Refresh only direct FHFA HPI and reuse immutable prior FRED inputs."""
    if root.resolve().drive.upper() != "D:":
        raise ValueError("Downloaded data must remain on D:")
    service = ResearchService(root)
    snapshot = service.snapshot(case_id)
    candidates = []
    for source_folder in (root / "data/private/public-context").glob("fred-*"):
        receipt_path = source_folder / "run-complete.json"
        if not receipt_path.is_file():
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") == "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE":
            candidates.append((str(receipt.get("completed_at", "")), source_folder, receipt))
    if not candidates:
        raise ValueError("No previous completed macro run exists to reuse FRED snapshots")
    _, source_folder, prior_receipt = max(candidates, key=lambda item: item[0])
    folder = root / "data/private/public-context" / ("fred-fhfa-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    write_new(folder / "run-start.json", {
        "started_at": timestamp(), "case_id": case_id,
        "intent": "refresh_direct_fhfa_hpi_without_new_fred_requests",
        "newly_acquired_series": ["USSTHPI"],
        "reused_series": ["UNRATE", "MORTGAGE30US"],
        "reused_from_private_run": source_folder.name,
    })
    try:
        reused = reuse_existing_fred_series(source_folder, folder, prior_receipt)
        fhfa_records, fhfa_metadata = fetch_fhfa_us_hpi(folder)
        records = reused[0][0] + fhfa_records + reused[1][0]
        metadata_by_id = {item[1]["series_id"]: item[1] for item in reused}
        metadata = [metadata_by_id["UNRATE"], fhfa_metadata, metadata_by_id["MORTGAGE30US"]]
        return _complete_run(service, case_id, snapshot, folder, records, metadata)
    except Exception as error:
        write_new(folder / "run-failed.json", {"status": "FAIL", "failed_at": timestamp(),
                   "exception_type": type(error).__name__, "model_training_performed": False})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=app_root())
    parser.add_argument("--case-id", default="d01-a24484b21a21")
    parser.add_argument("--fhfa-only", action="store_true",
                        help="download direct FHFA HPI only; reuse existing FRED files without network calls")
    args = parser.parse_args()
    action = run_fhfa_hpi_refresh if args.fhfa_only else run
    print(json.dumps(action(args.root, args.case_id), indent=2))
