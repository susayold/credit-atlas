"""Acquire BLS civilian unemployment-rate data for source-parity review."""

from __future__ import annotations

import argparse
import csv
import json
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

from credit_atlas.workspace import sha256, timestamp, write_new


SERIES_ID = "LNS14000000"
API_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
SERIES_URL = "https://data.bls.gov/timeseries/LNS14000000"
COPYRIGHT_URL = "https://www.bls.gov/opub/copyright-information.htm"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
FIRST_YEAR = 1948


def parse_response(payload: bytes, start_year: int, end_year: int):
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("BLS API response is not valid JSON") from error
    if document.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError("BLS API did not return REQUEST_SUCCEEDED")
    results = document.get("Results", {}).get("series", [])
    if len(results) != 1 or results[0].get("seriesID") != SERIES_ID:
        raise ValueError("BLS API response has an unexpected series identity")

    records, footnotes, seen = [], [], set()
    for item in results[0].get("data", []):
        year = item.get("year")
        period = item.get("period")
        if (not isinstance(year, str) or not year.isdigit() or not isinstance(period, str)
                or not re.fullmatch(r"M(?:0[1-9]|1[0-2])", period)):
            raise ValueError("BLS API returned a non-monthly or malformed period")
        year_number = int(year)
        if not start_year <= year_number <= end_year:
            raise ValueError("BLS API returned an observation outside the requested years")
        observed = date(year_number, int(period[1:]), 1)
        if observed in seen:
            raise ValueError("BLS API returned a duplicate month")
        seen.add(observed)
        raw = item.get("value")
        raw_notes = item.get("footnotes", [])
        notes = [note for note in raw_notes
                 if isinstance(note, dict) and (note.get("code") or note.get("text"))]
        if raw in ("", "-"):
            if raw == "-" and not any(note.get("text") for note in notes):
                raise ValueError("BLS missing-value marker has no explanatory footnote")
            value = None
        else:
            if not isinstance(raw, str):
                raise ValueError("BLS API returned a malformed unemployment value")
            try:
                parsed = Decimal(raw)
            except InvalidOperation as error:
                raise ValueError("BLS API returned a non-numeric unemployment value") from error
            if not parsed.is_finite() or parsed < 0 or parsed > 100:
                raise ValueError("BLS unemployment value is outside its valid domain")
            value = raw
        records.append({"observation_date": observed, "value": value})
        footnotes.extend({"observation_date": observed.isoformat(), **note} for note in notes)
    return sorted(records, key=lambda row: row["observation_date"]), sorted(
        footnotes, key=lambda row: (row["observation_date"], row.get("code", "")))


def fetch_year_chunks(folder: Path, current_year: int):
    all_records, all_footnotes, batch_receipts = [], [], []
    seen = set()
    start_year = FIRST_YEAR
    while start_year <= current_year:
        end_year = min(start_year + 9, current_year)
        request_body = json.dumps({
            "seriesid": [SERIES_ID],
            "startyear": str(start_year),
            "endyear": str(end_year),
        }, separators=(",", ":")).encode("utf-8")
        request = Request(API_URL, data=request_body, headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CreditAtlas public-data research/1.0",
        }, method="POST")
        with urlopen(request, timeout=45) as response:
            if response.status != 200 or response.geturl() != API_URL:
                raise ValueError("BLS API returned an unexpected status or redirect")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
        if not payload or len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("BLS API response is empty or exceeds the configured limit")

        records, footnotes = parse_response(payload, start_year, end_year)
        for row in records:
            if row["observation_date"] in seen:
                raise ValueError("BLS API year chunks overlap")
            seen.add(row["observation_date"])
        response_path = folder / "responses" / f"LNS14000000_{start_year}_{end_year}.json"
        response_path.parent.mkdir(parents=True, exist_ok=True)
        with response_path.open("xb") as stream:
            stream.write(payload)
        all_records.extend(records)
        all_footnotes.extend(footnotes)
        batch_receipts.append({
            "start_year": start_year,
            "end_year": end_year,
            "response_file": response_path.relative_to(folder).as_posix(),
            "response_bytes": len(payload),
            "response_sha256": sha256(response_path),
            "observations": len(records),
            "footnote_count": len(footnotes),
        })
        start_year = end_year + 1
    return sorted(all_records, key=lambda row: row["observation_date"]), all_footnotes, batch_receipts


def read_fred_snapshot(path: Path):
    rows = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["observation_date", "UNRATE"]:
            raise ValueError("Existing FRED UNRATE file has an unexpected schema")
        for row in reader:
            observed = date.fromisoformat(row["observation_date"])
            if observed in rows:
                raise ValueError("Existing FRED UNRATE file has duplicate months")
            rows[observed] = Decimal(row["UNRATE"]) if row["UNRATE"] not in ("", ".") else None
    return rows


def compare_fred(records, fred_rows):
    bls_rows = {row["observation_date"]: Decimal(row["value"]) if row["value"] is not None else None
                for row in records}
    common = set(bls_rows) & set(fred_rows)
    mismatches = [{
        "observation_date": observed.isoformat(),
        "bls": str(bls_rows[observed]) if bls_rows[observed] is not None else None,
        "fred": str(fred_rows[observed]) if fred_rows[observed] is not None else None,
    } for observed in sorted(common) if bls_rows[observed] != fred_rows[observed]]
    return {
        "comparison_source": "existing FRED UNRATE private snapshot",
        "comparison_method": "exact Decimal equality by observation_date; no resampling or imputation",
        "bls_observation_count": len(bls_rows),
        "fred_observation_count": len(fred_rows),
        "overlap_count": len(common),
        "only_in_bls_count": len(set(bls_rows) - set(fred_rows)),
        "only_in_fred_count": len(set(fred_rows) - set(bls_rows)),
        "value_mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def latest_fred_unrate_comparator(root: Path):
    candidates = []
    for folder in (root / "data/private/public-context").glob("fred-*"):
        receipt_path = folder / "run-complete.json"
        if not receipt_path.is_file():
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE":
            continue
        unrate = next((row for row in receipt.get("series", [])
                       if isinstance(row, dict) and row.get("series_id") == "UNRATE"), None)
        if (not unrate
                or unrate.get("source_url") != "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE"):
            continue
        csv_path = folder / "UNRATE.csv"
        if not csv_path.is_file() or sha256(csv_path) != unrate.get("sha256"):
            raise ValueError("Historical FRED UNRATE comparator failed its receipt digest")
        candidates.append((str(receipt.get("completed_at", "")), folder, receipt))
    if not candidates:
        raise ValueError("No receipt-verified historical FRED UNRATE comparator exists")
    return max(candidates, key=lambda item: item[0])[1:]


def run(root: Path):
    if root.resolve().drive.upper() != "D:":
        raise ValueError("Downloaded data must remain on D:")
    source_folder, macro_receipt = latest_fred_unrate_comparator(root)
    fred_path = source_folder / "UNRATE.csv"
    expected = next((row for row in macro_receipt.get("series", [])
                     if row.get("series_id") == "UNRATE"), None)
    if not expected or sha256(fred_path) != expected.get("sha256"):
        raise ValueError("Existing FRED UNRATE source failed its receipt digest")

    folder = root / "data/private/public-context" / ("bls-unrate-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    write_new(folder / "run-start.json", {
        "started_at": timestamp(),
        "intent": "direct_bls_unrate_source_parity_candidate",
        "source_series_id": SERIES_ID,
        "years": {"start": FIRST_YEAR, "end": date.today().year},
        "api_version": "1.0_public_unregistered",
        "fred_comparison_run": source_folder.name,
        "model_training_performed": False,
    })
    try:
        records, footnotes, batches = fetch_year_chunks(folder, date.today().year)
        csv_path = folder / "UNRATE.csv"
        with csv_path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["observation_date", "UNRATE"])
            writer.writerows([row["observation_date"].isoformat(), row["value"] or ""] for row in records)
        write_new(folder / "footnotes.json", footnotes)
        comparison = compare_fred(records, read_fred_snapshot(fred_path))
        write_new(folder / "fred-parity.json", comparison)
        receipt = {
            "status": "DOWNLOADED_AND_VALIDATED",
            "completed_at": timestamp(),
            "series_id": "UNRATE",
            "source_series_id": SERIES_ID,
            "source": "U.S. Bureau of Labor Statistics (direct)",
            "source_url": API_URL,
            "metadata_url": SERIES_URL,
            "rights_evidence_url": COPYRIGHT_URL,
            "rights_review_status": "BLS_PUBLIC_DOMAIN; SOURCE_CITATION_REQUESTED",
            "attribution": "Source: U.S. Bureau of Labor Statistics, Current Population Survey, civilian unemployment rate, seasonally adjusted.",
            "definition": "Civilian unemployment rate; persons age 16+; seasonally adjusted; percent of the civilian labor force.",
            "frequency": "Monthly",
            "seasonal_adjustment": "Seasonally Adjusted",
            "information_availability": "Latest-revised BLS series; seasonal factors are reestimated annually; no historical point-in-time vintages in this acquisition.",
            "api_version": "1.0_public_unregistered",
            "request_year_chunks": batches,
            "observations": len(records),
            "missing_values": sum(row["value"] is None for row in records),
            "first_reference_date": records[0]["observation_date"].isoformat() if records else None,
            "last_reference_date": records[-1]["observation_date"].isoformat() if records else None,
            "latest_value": records[-1]["value"] if records else None,
            "footnote_count": len(footnotes),
            "comparison": comparison,
            "macro_context_integrated": False,
            "model_training_performed": False,
            "visibility": "private",
            "public_release_approved": False,
            "outputs_sha256": {path.relative_to(folder).as_posix(): sha256(path)
                               for path in folder.rglob("*") if path.is_file()},
        }
        write_new(folder / "run-complete.json", receipt)
        return {
            "data_directory": str(folder),
            "status": receipt["status"],
            "observations": receipt["observations"],
            "first_reference_date": receipt["first_reference_date"],
            "last_reference_date": receipt["last_reference_date"],
            "comparison": comparison,
            "model_training_performed": False,
        }
    except Exception as error:
        write_new(folder / "run-failed.json", {
            "status": "FAIL", "failed_at": timestamp(),
            "exception_type": type(error).__name__, "model_training_performed": False,
        })
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    print(json.dumps(run(parser.parse_args().root), indent=2))
