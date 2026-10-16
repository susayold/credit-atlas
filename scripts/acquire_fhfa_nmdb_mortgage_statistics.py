"""Acquire and profile official FHFA NMDB new/outstanding mortgage aggregates."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import sys
import urllib.request
import uuid
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.workspace import app_root, timestamp, write_new  # noqa: E402


SOURCE_PAGE = "https://www.fhfa.gov/data/nmdb"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024 * 1024
HEADERS = [
    "SOURCE", "FREQUENCY", "GEOLEVEL", "GEOID", "GEONAME", "MARKET",
    "PERIOD", "YEAR", "QUARTER", "MONTH", "SUPPRESSED", "SERIESID",
    "VALUE1", "VALUE2",
]
DATASETS = {
    "new_annual": {
        "filename": "nmdb-new-mortgage-statistics-all-annual.zip",
        "member": "nmdb-new-mortgage-statistics-all-annual.csv",
        "url": "https://www.fhfa.gov/document/d/nmdb/nmdb-new-mortgage-statistics-all-annual.zip",
        "frequency": "Annual",
        "period_bounds": (1998, 2025),
        "period_check": lambda row: (
            row["PERIOD"] == row["YEAR"] and row["QUARTER"] == "4" and row["MONTH"] == "12"
        ),
    },
    "outstanding_quarterly": {
        "filename": "nmdb-outstanding-mortgage-statistics-all-quarterly.zip",
        "member": "nmdb-outstanding-mortgage-statistics-all-quarterly.csv",
        "url": "https://www.fhfa.gov/document/d/nmdb/nmdb-outstanding-mortgage-statistics-all-quarterly.zip",
        "frequency": "Quarterly",
        "period_bounds": ((2013, 1), (2026, 2)),
        "period_check": lambda row: (
            len(row["PERIOD"]) == 6 and row["PERIOD"][:4] == row["YEAR"]
            and row["PERIOD"][4:] == f"Q{row['QUARTER']}"
            and int(row["MONTH"]) == int(row["QUARTER"]) * 3
        ),
    },
}


class AcquisitionError(ValueError):
    """Raised when the public-source contract is not satisfied."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "www.fhfa.gov" or parsed.fragment:
        raise AcquisitionError("Only the official FHFA HTTPS host is allowed")
    request = urllib.request.Request(url, headers={"User-Agent": "CreditAtlas public aggregate-data research"})
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            final = urlsplit(response.geturl())
            if response.status != 200 or final.scheme != "https" or final.hostname != "www.fhfa.gov":
                raise AcquisitionError("Unexpected FHFA response status or host")
            if response.headers.get_content_type().casefold() != "application/zip":
                raise AcquisitionError("FHFA returned a non-ZIP response")
            with destination.open("xb") as stream:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise AcquisitionError("FHFA archive exceeded the transfer-size bound")
                    stream.write(chunk)
                    digest.update(chunk)
            if response.headers.get("Content-Length") and int(response.headers["Content-Length"]) != total:
                raise AcquisitionError("FHFA Content-Length differs from received byte count")
            return {
                "requested_url": url,
                "response_url": response.geturl(),
                "http_status": response.status,
                "content_type": response.headers.get_content_type(),
                "bytes": total,
                "sha256": digest.hexdigest(),
            }
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def profile_archive(path: Path, dataset: str) -> dict:
    if dataset not in DATASETS:
        raise AcquisitionError("Unknown FHFA NMDB dataset contract")
    spec = DATASETS[dataset]
    try:
        with zipfile.ZipFile(path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) != 1 or members[0].filename != spec["member"]:
                raise AcquisitionError("FHFA archive member name/count differs from the official layout")
            item = members[0]
            if item.flag_bits & 1 or item.file_size > MAX_MEMBER_BYTES:
                raise AcquisitionError("FHFA archive member is encrypted or exceeds the expanded-size bound")
            bad = archive.testzip()
            if bad is not None:
                raise AcquisitionError("FHFA ZIP CRC validation failed")
            raw = archive.read(item)
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise AcquisitionError("Invalid FHFA NMDB aggregate ZIP") from exc

    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict"), newline=""))
    if reader.fieldnames != HEADERS:
        raise AcquisitionError(f"Unexpected FHFA NMDB schema: {reader.fieldnames!r}")
    rows = 0
    unique_keys: set[tuple[str, ...]] = set()
    series, markets, geolevels = Counter(), Counter(), Counter()
    suppressed, missing_value1, missing_value2 = Counter(), Counter(), Counter()
    years: set[int] = set()
    period_ordinals: set[int] = set()
    period_labels: set[str] = set()
    period_min = period_max = None
    national = Counter()
    lower, upper = spec["period_bounds"]

    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise AcquisitionError("Malformed row width in FHFA NMDB file")
        if row["SOURCE"] != "NMDB" or row["FREQUENCY"] != spec["frequency"]:
            raise AcquisitionError("Source/frequency does not match the requested dataset")
        try:
            year = int(row["YEAR"])
            suppression = int(row["SUPPRESSED"])
        except ValueError as exc:
            raise AcquisitionError("YEAR or suppression flag is invalid") from exc
        if suppression not in (0, 1):
            raise AcquisitionError("SUPPRESSED must be 0 or 1")
        if spec["frequency"] == "Annual":
            if not lower <= year <= upper:
                raise AcquisitionError("Annual period is outside the official coverage window")
            ordinal = year
        else:
            try:
                quarter = int(row["QUARTER"])
            except ValueError as exc:
                raise AcquisitionError("Quarter is missing or malformed") from exc
            if not 1 <= quarter <= 4 or not spec["period_check"](row):
                raise AcquisitionError("Quarterly period fields are inconsistent")
            if not (lower <= (year, quarter) <= upper):
                raise AcquisitionError("Quarterly period is outside the official coverage window")
            ordinal = year * 4 + quarter
        if not spec["period_check"](row):
            raise AcquisitionError("PERIOD does not agree with the frequency fields")

        for field, counter in (("VALUE1", missing_value1), ("VALUE2", missing_value2)):
            value = row[field]
            if value in ("", "."):
                counter[field] += 1
            else:
                try:
                    number = float(value)
                except ValueError as exc:
                    raise AcquisitionError(f"{field} contains a non-numeric value") from exc
                if number != number or number in (float("inf"), float("-inf")):
                    raise AcquisitionError(f"{field} contains a non-finite value")

        key = tuple(row[field] for field in (
            "SOURCE", "FREQUENCY", "SERIESID", "GEOLEVEL", "GEOID", "MARKET", "PERIOD"
        ))
        if key in unique_keys:
            raise AcquisitionError("Duplicate aggregate key in FHFA NMDB archive")
        unique_keys.add(key)
        rows += 1
        years.add(year)
        period_ordinals.add(ordinal)
        period_labels.add(row["PERIOD"])
        period_min = ordinal if period_min is None else min(period_min, ordinal)
        period_max = ordinal if period_max is None else max(period_max, ordinal)
        series[row["SERIESID"]] += 1
        markets[row["MARKET"]] += 1
        geolevels[row["GEOLEVEL"]] += 1
        suppressed[str(suppression)] += 1
        if (row["GEOLEVEL"], row["GEOID"], row["MARKET"]) == ("National", "USA", "All Mortgages"):
            national[row["PERIOD"]] += 1

    if rows == 0:
        raise AcquisitionError("FHFA NMDB dataset is empty")
    expected_periods = (
        set(range(lower, upper + 1))
        if spec["frequency"] == "Annual"
        else set(range(lower[0] * 4 + lower[1], upper[0] * 4 + upper[1] + 1))
    )
    if period_ordinals != expected_periods:
        raise AcquisitionError("Official dataset has a missing or unexpected reporting period")
    return {
        "member": spec["member"],
        "uncompressed_bytes": item.file_size,
        "csv_sha256": hashlib.sha256(raw).hexdigest(),
        "rows": rows,
        "columns": HEADERS,
        "unique_aggregate_keys": len(unique_keys),
        "duplicate_aggregate_keys": 0,
        "frequency": spec["frequency"],
        "first_year": min(years),
        "last_year": max(years),
        "first_period_ordinal": period_min,
        "last_period_ordinal": period_max,
        "distinct_periods": len(period_labels),
        "periods_contiguous": True,
        "years": len(years),
        "series_row_counts": dict(sorted(series.items())),
        "market_row_counts": dict(sorted(markets.items())),
        "geography_level_row_counts": dict(sorted(geolevels.items())),
        "suppression_row_counts": dict(sorted(suppressed.items())),
        "missing_value1_rows": missing_value1.get("VALUE1", 0),
        "missing_value2_rows": missing_value2.get("VALUE2", 0),
        "national_all_mortgages_period_observations": sum(national.values()),
        "not_loan_level": True,
        "does_not_add_freddie_vintage": True,
    }


def run(root: Path) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise AcquisitionError("FHFA NMDB archives and receipts must remain on D:")
    output = root / "data" / "private" / "public-context" / ("fhfa-nmdb-composition-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    results = {}
    try:
        for name, spec in DATASETS.items():
            archive_path = output / spec["filename"]
            download = _download(spec["url"], archive_path)
            profile = profile_archive(archive_path, name)
            results[name] = {"download": download, "profile": profile}
            write_new(output / f"{name}-profile.json", profile)
        receipt = {
            "status": "PASS",
            "retrieved_at": timestamp(),
            "source": "FHFA National Mortgage Database Aggregate Statistics",
            "source_page": SOURCE_PAGE,
            "source_release_date": "2026-09-30",
            "terms": "Public aggregate statistics; no credentials/cookies used",
            "interpretation": {
                "new_value1": "Weighted by mortgage count; each sample mortgage represents 20 actual mortgages",
                "new_value2": "Weighted by origination loan amount",
                "outstanding_value1": "Weighted by mortgage count; each sample mortgage represents 20 actual mortgages",
                "outstanding_value2": "Weighted by unpaid principal balance at quarter end",
                "suppression": "Cells based on fewer than 3 loans are suppressed",
            },
            "datasets": results,
            "loan_level_rows_emitted": False,
            "forecast_or_imputation_used": False,
        }
        write_new(output / "receipt.json", receipt)
        write_new(output / "run-complete.json", {"status": "PASS", "completed_at": timestamp()})
        return {
            "status": "PASS",
            "output": str(output),
            "datasets": {
                name: {"rows": value["profile"]["rows"], "bytes": value["download"]["bytes"], "sha256": value["download"]["sha256"]}
                for name, value in results.items()
            },
        }
    except Exception as exc:
        write_new(output / "run-failed.json", {"status": "FAILED", "failed_at": timestamp(), "exception_type": type(exc).__name__})
        raise


def audit_existing(root: Path, source_dir: Path) -> dict:
    """Re-profile already-downloaded official archives without re-downloading them."""
    root, source_dir = root.resolve(), source_dir.resolve()
    private_root = (root / "data" / "private" / "public-context").resolve()
    if root.drive.upper() != "D:" or not source_dir.is_relative_to(private_root):
        raise AcquisitionError("Existing source archives must be within the private D: context store")
    output = private_root / ("fhfa-nmdb-composition-reaudit-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    records = {}
    try:
        for name, spec in DATASETS.items():
            archive_path = source_dir / spec["filename"]
            if not archive_path.is_file():
                raise AcquisitionError("The private source directory is missing an expected FHFA archive")
            profile = profile_archive(archive_path, name)
            records[name] = {
                "source_archive_relative_path": str(archive_path.relative_to(root)),
                "archive_bytes": archive_path.stat().st_size,
                "archive_sha256": sha256(archive_path),
                "profile": profile,
            }
            write_new(output / f"{name}-profile.json", profile)
        receipt = {
            "status": "PASS",
            "audited_at": timestamp(),
            "source": "FHFA National Mortgage Database Aggregate Statistics",
            "source_page": SOURCE_PAGE,
            "source_release_date": "2026-09-30",
            "audit_mode": "Re-profile existing private source archives; no network access",
            "interpretation": {
                "new_value1": "Weighted by mortgage count; each sample mortgage represents 20 actual mortgages",
                "new_value2": "Weighted by origination loan amount",
                "outstanding_value1": "Weighted by mortgage count; each sample mortgage represents 20 actual mortgages",
                "outstanding_value2": "Weighted by unpaid principal balance at quarter end",
                "suppression": "Cells based on fewer than 3 loans are suppressed",
            },
            "datasets": records,
            "loan_level_rows_emitted": False,
            "forecast_or_imputation_used": False,
        }
        write_new(output / "receipt.json", receipt)
        write_new(output / "run-complete.json", {"status": "PASS", "completed_at": timestamp()})
        return {"status": "PASS", "output": str(output), "datasets": {
            name: {"rows": item["profile"]["rows"], "periods": item["profile"]["distinct_periods"]}
            for name, item in records.items()
        }}
    except Exception as exc:
        write_new(output / "run-failed.json", {"status": "FAILED", "failed_at": timestamp(), "exception_type": type(exc).__name__})
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=app_root())
    parser.add_argument("--source-dir", type=Path, help="Re-audit existing official ZIPs in a private source directory")
    args = parser.parse_args()
    result = audit_existing(args.root, args.source_dir) if args.source_dir else run(args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
