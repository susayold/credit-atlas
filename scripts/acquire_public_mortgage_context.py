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
from pathlib import Path
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


def reuse_existing_macro_series(source_folder, destination_folder, receipt):
    """Copy verified current UNRATE and PMMS inputs without making network calls."""
    metadata_by_id = {row.get("series_id"): row for row in receipt.get("series", [])
                      if isinstance(row, dict)}
    if not {"UNRATE", "MORTGAGE30US"}.issubset(metadata_by_id):
        raise ValueError("Latest macro receipt is missing unemployment or PMMS inputs")
    allowed_unrate_urls = {
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE",
        "https://data.bls.gov/timeseries/LNS14000000",
    }
    if metadata_by_id["UNRATE"].get("source_url") not in allowed_unrate_urls:
        raise ValueError("Existing unemployment input has an unexpected source URL")
    if metadata_by_id["MORTGAGE30US"].get("source_url") != (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"):
        raise ValueError("Existing PMMS snapshot has an unexpected source URL")
    return copy_verified_series(source_folder, destination_folder, metadata_by_id,
                                ("UNRATE", "MORTGAGE30US"))


def copy_verified_series(source_folder, destination_folder, metadata_by_id, series_ids):
    """Copy specified normalized series only when their receipt hashes match."""
    downloads = []
    for series_id in series_ids:
        metadata = metadata_by_id.get(series_id)
        if not isinstance(metadata, dict):
            raise ValueError("Source receipt is missing metadata for a reused series")
        source_path = source_folder / (series_id + ".csv")
        if not source_path.is_file() or sha256(source_path) != metadata.get("sha256"):
            raise ValueError("Reused source series failed its receipt digest check")
        destination_path = destination_folder / source_path.name
        shutil.copyfile(source_path, destination_path)
        if sha256(destination_path) != metadata["sha256"]:
            raise ValueError("Copied source series failed its receipt digest check")
        downloads.append((parse_csv(destination_path.read_bytes(), series_id), metadata))
    return downloads


def latest_macro_run(root):
    candidates = []
    for source_folder in (root / "data/private/public-context").glob("fred-*"):
        receipt_path = source_folder / "run-complete.json"
        if not receipt_path.is_file():
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") == "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE":
            candidates.append((str(receipt.get("completed_at", "")), source_folder, receipt))
    if not candidates:
        raise ValueError("No previous completed macro context run exists")
    _, folder, receipt = max(candidates, key=lambda item: item[0])
    return folder, receipt


def latest_validated_bls_candidate(root):
    candidates = []
    for source_folder in (root / "data/private/public-context").glob("bls-unrate-*"):
        receipt_path = source_folder / "run-complete.json"
        if not receipt_path.is_file():
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (receipt.get("status") == "DOWNLOADED_AND_VALIDATED"
                and receipt.get("source_series_id") == "LNS14000000"):
            candidates.append((str(receipt.get("completed_at", "")), source_folder, receipt))
    if not candidates:
        raise ValueError("No validated direct BLS UNRATE candidate exists")
    _, folder, receipt = max(candidates, key=lambda item: item[0])
    if (receipt.get("macro_context_integrated") is not False
            or receipt.get("public_release_approved") is not False
            or receipt.get("model_training_performed") is not False):
        raise ValueError("BLS source candidate has an invalid integration or release status")
    for name, digest in receipt.get("outputs_sha256", {}).items():
        path = folder / name
        if Path(name).is_absolute() or ".." in Path(name).parts or not path.is_file() or sha256(path) != digest:
            raise ValueError("BLS source candidate failed its receipt digest check")
    comparison = receipt.get("comparison", {})
    if (comparison.get("overlap_count", 0) <= 0
            or comparison.get("value_mismatch_count") != 0
            or comparison.get("only_in_bls_count") != 0
            or comparison.get("only_in_fred_count") != 0):
        raise ValueError("BLS source candidate has not passed exact FRED snapshot parity")
    return folder, receipt


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
    """Refresh FHFA HPI and reuse receipt-verified current unemployment/PMMS inputs."""
    if root.resolve().drive.upper() != "D:":
        raise ValueError("Downloaded data must remain on D:")
    service = ResearchService(root)
    snapshot = service.snapshot(case_id)
    source_folder, prior_receipt = latest_macro_run(root)
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
        reused = reuse_existing_macro_series(source_folder, folder, prior_receipt)
        fhfa_records, fhfa_metadata = fetch_fhfa_us_hpi(folder)
        records = reused[0][0] + fhfa_records + reused[1][0]
        metadata_by_id = {item[1]["series_id"]: item[1] for item in reused}
        metadata = [metadata_by_id["UNRATE"], fhfa_metadata, metadata_by_id["MORTGAGE30US"]]
        return _complete_run(service, case_id, snapshot, folder, records, metadata)
    except Exception as error:
        write_new(folder / "run-failed.json", {"status": "FAIL", "failed_at": timestamp(),
                   "exception_type": type(error).__name__, "model_training_performed": False})
        raise


def run_bls_unrate_refresh(root, case_id="d01-a24484b21a21"):
    """Integrate parity-checked direct BLS UNRATE; reuse FHFA HPI and PMMS snapshots."""
    if root.resolve().drive.upper() != "D:":
        raise ValueError("Downloaded data must remain on D:")
    service = ResearchService(root)
    snapshot = service.snapshot(case_id)
    source_folder, prior_receipt = latest_macro_run(root)
    candidate_folder, candidate_receipt = latest_validated_bls_candidate(root)
    if prior_receipt.get("case_id") != case_id:
        raise ValueError("Existing macro context belongs to a different D01 case")

    prior_metadata = {row.get("series_id"): row for row in prior_receipt.get("series", [])
                      if isinstance(row, dict)}
    if not {"USSTHPI", "MORTGAGE30US"}.issubset(prior_metadata):
        raise ValueError("Existing macro context is missing HPI or PMMS inputs")
    if prior_metadata["USSTHPI"].get("source_url") != FHFA_US_CENSUS_HPI_URL:
        raise ValueError("Existing macro context does not contain verified direct FHFA HPI")
    if prior_metadata["MORTGAGE30US"].get("source_url") != (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"):
        raise ValueError("Existing mortgage-rate snapshot has an unexpected source URL")

    candidate_csv = candidate_folder / "UNRATE.csv"
    candidate_hash = candidate_receipt.get("outputs_sha256", {}).get("UNRATE.csv")
    if not candidate_csv.is_file() or sha256(candidate_csv) != candidate_hash:
        raise ValueError("Direct BLS UNRATE file failed its source receipt digest")
    candidate_records = parse_csv(candidate_csv.read_bytes(), "UNRATE")
    if (len(candidate_records) != candidate_receipt.get("observations")
            or candidate_records[0]["observation_date"].isoformat()
            != candidate_receipt.get("first_reference_date")
            or candidate_records[-1]["observation_date"].isoformat()
            != candidate_receipt.get("last_reference_date")):
        raise ValueError("Direct BLS UNRATE coverage does not match its source receipt")

    folder = root / "data/private/public-context" / ("fred-bls-fhfa-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    write_new(folder / "run-start.json", {
        "started_at": timestamp(), "case_id": case_id,
        "intent": "integrate_direct_bls_unrate_after_exact_fred_snapshot_parity",
        "newly_integrated_series": ["UNRATE"],
        "reused_series": ["USSTHPI", "MORTGAGE30US"],
        "bls_source_candidate": candidate_folder.name,
        "reused_macro_context_run": source_folder.name,
        "fred_network_requests": 0,
    })
    try:
        destination_unrate = folder / "UNRATE.csv"
        shutil.copyfile(candidate_csv, destination_unrate)
        if sha256(destination_unrate) != candidate_hash:
            raise ValueError("Copied direct BLS UNRATE file failed its source receipt digest")
        unrate_metadata = {
            "series_id": "UNRATE",
            "source_series_id": candidate_receipt["source_series_id"],
            "source": candidate_receipt["source"],
            "units": "Percent",
            "frequency": candidate_receipt["frequency"],
            "seasonal_adjustment": candidate_receipt["seasonal_adjustment"],
            "source_url": candidate_receipt["metadata_url"],
            "api_endpoint": candidate_receipt["source_url"],
            "metadata_url": candidate_receipt["metadata_url"],
            "rights_evidence_url": candidate_receipt["rights_evidence_url"],
            "rights_review_status": candidate_receipt["rights_review_status"],
            "attribution": candidate_receipt["attribution"],
            "information_availability": candidate_receipt["information_availability"],
            "snapshot_as_of": candidate_receipt["last_reference_date"],
            "retrieved_at": candidate_receipt["completed_at"],
            "bytes": destination_unrate.stat().st_size,
            "sha256": candidate_hash,
            "observations": candidate_receipt["observations"],
            "missing_values": candidate_receipt["missing_values"],
            "first_reference_date": candidate_receipt["first_reference_date"],
            "last_reference_date": candidate_receipt["last_reference_date"],
            "model_predictor_qualified": False,
            "source_candidate": candidate_folder.name,
        }
        reused = copy_verified_series(source_folder, folder, prior_metadata,
                                      ("USSTHPI", "MORTGAGE30US"))
        hpi_metadata, mortgage_metadata = reused[0][1], reused[1][1]
        hpi_records, mortgage_records = reused[0][0], reused[1][0]
        records = candidate_records + hpi_records + mortgage_records
        metadata = [unrate_metadata, hpi_metadata, mortgage_metadata]
        return _complete_run(service, case_id, snapshot, folder, records, metadata)
    except Exception as error:
        write_new(folder / "run-failed.json", {"status": "FAIL", "failed_at": timestamp(),
                   "exception_type": type(error).__name__, "model_training_performed": False})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=app_root())
    parser.add_argument("--case-id", default="d01-a24484b21a21")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fhfa-only", action="store_true",
                      help="download direct FHFA HPI only; reuse verified unemployment and PMMS files without network calls")
    mode.add_argument("--bls-only", action="store_true",
                      help="integrate a parity-checked BLS UNRATE candidate; reuse HPI and PMMS without network calls")
    mode.add_argument("--legacy-fred", action="store_true",
                      help="explicitly run legacy FRED UNRATE/PMMS acquisition; use only after its terms/use gate is cleared")
    args = parser.parse_args()
    action = (run if args.legacy_fred else run_fhfa_hpi_refresh if args.fhfa_only
              else run_bls_unrate_refresh)
    print(json.dumps(action(args.root, args.case_id), indent=2))
