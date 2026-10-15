"""Acquire and profile FHFA's public quarterly NMDB mortgage performance aggregates."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import uuid
import zipfile
from collections import Counter
from pathlib import Path

from credit_atlas.workspace import app_root, timestamp, write_new

SOURCE_URL = (
    "https://www.fhfa.gov/document/d/nmdb/"
    "nmdb-mortgage-performance-statistics-all-quarterly.zip"
)
SOURCE_PAGE = "https://www.fhfa.gov/data/nmdb"
MAX_BYTES = 128 * 1024 * 1024
EXPECTED_COLUMNS = [
    "SOURCE", "FREQUENCY", "GEOLEVEL", "GEOID", "GEONAME", "MARKET",
    "PERIOD", "YEAR", "QUARTER", "MONTH", "SUPPRESSED", "SERIESID", "VALUE1",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing source archive")
    response = subprocess.run(
        [
            "curl.exe", "--fail", "--silent", "--show-error", "--proto", "=https",
            "--location", "--max-redirs", "3", "--max-time", "120",
            "--max-filesize", str(MAX_BYTES), "--output", str(destination),
            "--write-out", "%{http_code}\n%{url_effective}", SOURCE_URL,
        ],
        capture_output=True, text=True, timeout=130, check=False,
    )
    if response.returncode:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Official-source transfer failed (curl exit {response.returncode})")
    lines = response.stdout.splitlines()
    if len(lines) < 2 or lines[0] != "200" or not lines[1].startswith("https://www.fhfa.gov/"):
        destination.unlink(missing_ok=True)
        raise ValueError("Unexpected status or final host for FHFA archive")
    if destination.stat().st_size > MAX_BYTES:
        destination.unlink(missing_ok=True)
        raise ValueError("FHFA archive exceeded configured download bound")
    return {
        "requested_url": SOURCE_URL,
        "response_url": lines[1],
        "http_status": 200,
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
        "transport": "curl.exe HTTPS; no credentials or cookies",
    }


def profile_archive(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            csv_members = [info for info in members if info.filename.lower().endswith(".csv")]
            if len(csv_members) != 1 or len(members) != 1:
                raise ValueError("Expected exactly one CSV and no other archive members")
            info = csv_members[0]
            if info.file_size > MAX_BYTES or info.compress_size > MAX_BYTES:
                raise ValueError("Archive member exceeds the configured bound")
            raw = archive.read(info)
    except (zipfile.BadZipFile, OSError, RuntimeError) as error:
        raise ValueError("Invalid FHFA ZIP archive") from error

    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict"), newline=""))
    if reader.fieldnames != EXPECTED_COLUMNS:
        raise ValueError(f"Unexpected FHFA CSV schema: {reader.fieldnames!r}")
    row_count = 0
    first_period = last_period = None
    series = Counter()
    geographies = Counter()
    markets = Counter()
    suppressed = Counter()
    unique_keys = set()
    value_nulls = Counter()
    national = {}
    min_quarter = max_quarter = None
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed row width in FHFA CSV")
        if row["SOURCE"] != "NMDB" or row["FREQUENCY"] != "Quarterly":
            raise ValueError("Unexpected source or frequency")
        period = row["PERIOD"]
        if not re.fullmatch(r"\d{4}Q[1-4]", period):
            raise ValueError("Invalid quarterly period")
        year, quarter = int(row["YEAR"]), int(row["QUARTER"])
        if period != f"{year}Q{quarter}" or not 1 <= quarter <= 4:
            raise ValueError("Period disagrees with year/quarter fields")
        if first_period is None:
            first_period = period
        last_period = period
        ordinal = year * 4 + quarter
        min_quarter = ordinal if min_quarter is None else min(min_quarter, ordinal)
        max_quarter = ordinal if max_quarter is None else max(max_quarter, ordinal)
        try:
            suppression = int(row["SUPPRESSED"])
        except ValueError as error:
            raise ValueError("Invalid suppression flag") from error
        if suppression not in (0, 1):
            raise ValueError("Unexpected suppression flag")
        key = tuple(row[name] for name in (
            "SOURCE", "FREQUENCY", "SERIESID", "GEOLEVEL", "GEOID", "MARKET", "PERIOD"
        ))
        if key in unique_keys:
            raise ValueError("Duplicate source aggregate key")
        unique_keys.add(key)
        for value_name in ("VALUE1",):
            value = row[value_name]
            if value in ("", "."):
                value_nulls[value_name] += 1
            elif not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
                raise ValueError("Non-numeric aggregate value")
            elif not 0 <= float(value) <= 100:
                raise ValueError("Aggregate performance percentage outside [0, 100]")
        if (row["GEOLEVEL"], row["GEOID"], row["MARKET"]) == (
            "National", "USA", "All Mortgages"
        ):
            national.setdefault(period, {})[row["SERIESID"]] = (
                None if suppression or row["VALUE1"] in ("", ".") else float(row["VALUE1"])
            )
        row_count += 1
        series[row["SERIESID"]] += 1
        geographies[row["GEOLEVEL"]] += 1
        markets[row["MARKET"]] += 1
        suppressed[str(suppression)] += 1
    if row_count == 0:
        raise ValueError("Empty FHFA aggregate dataset")
    expected_series = {"P3089DL", "P90DL", "PFORB", "PFORECL"}
    if not national or any(set(values) != expected_series for values in national.values()):
        raise ValueError("Incomplete national all-mortgages series coverage")
    observed_quarters = sorted(
        (int(period[:4]) * 4 + int(period[-1])) for period in national
    )
    if observed_quarters != list(range(observed_quarters[0], observed_quarters[-1] + 1)):
        raise ValueError("National quarterly series has a missing or duplicate period")
    national_series = [
        {"period": period, **national[period]}
        for period in sorted(national, key=lambda item: (int(item[:4]), int(item[-1])))
    ]
    return {
        "member": info.filename,
        "uncompressed_bytes": info.file_size,
        "csv_sha256": hashlib.sha256(raw).hexdigest(),
        "rows": row_count,
        "columns": EXPECTED_COLUMNS,
        "unique_aggregate_keys": len(unique_keys),
        "duplicate_aggregate_keys": 0,
        "first_period_in_file": first_period,
        "last_period_in_file": last_period,
        "distinct_periods": max_quarter - min_quarter + 1,
        "series_row_counts": dict(sorted(series.items())),
        "geography_level_row_counts": dict(sorted(geographies.items())),
        "market_row_counts": dict(sorted(markets.items())),
        "suppression_row_counts": dict(sorted(suppressed.items())),
        "blank_or_dot_value_counts": dict(sorted(value_nulls.items())),
        "national_all_mortgages_series": national_series,
    }


def run(root: Path) -> dict:
    if root.resolve().drive.upper() != "D:":
        raise ValueError("Downloaded public datasets must remain on D:")
    output = root / "data" / "private" / "public-context" / ("fhfa-nmdb-performance-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    archive_path = output / "official-performance-quarterly.zip"
    write_new(output / "run-start.json", {
        "started_at": timestamp(),
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "intent": "Acquire public aggregate mortgage-performance context; not loan-level data",
        "credentials_used": False,
        "cookies_used": False,
        "terms_acknowledgement_submitted": False,
    })
    try:
        acquisition = download(archive_path)
        profile = profile_archive(archive_path)
        receipt = {
            "status": "PASS",
            "retrieved_at": timestamp(),
            "source_page": SOURCE_PAGE,
            "source_release_date": "2026-09-30",
            "scope": "Public FHFA NMDB quarterly mortgage-performance aggregates; all geographic areas",
            "not_loan_level": True,
            "not_a_Freddie_annual_vintage": True,
            "availability_vintage": "latest revised aggregate snapshot; not historical release vintages",
            "download": acquisition,
            "profile": profile,
        }
        profile_path = output / "profile.json"
        write_new(profile_path, profile)
        receipt["profile_sha256"] = sha256(profile_path)
        write_new(output / "receipt.json", receipt)
        write_new(output / "run-complete.json", {"status": "PASS", "completed_at": timestamp()})
        return {"status": "PASS", "output": str(output), "rows": profile["rows"],
                "periods": profile["distinct_periods"], "zip_sha256": acquisition["sha256"]}
    except Exception as error:
        write_new(output / "run-failed.json", {
            "status": "FAILED", "failed_at": timestamp(),
            "exception_type": type(error).__name__,
        })
        raise


if __name__ == "__main__":
    print(json.dumps(run(app_root()), indent=2))
