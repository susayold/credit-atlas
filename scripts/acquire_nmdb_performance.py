"""Acquire and curate FHFA's public NMDB quarterly performance aggregates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = (
    "https://www.fhfa.gov/document/d/nmdb/"
    "nmdb-mortgage-performance-statistics-national-census-areas-quarterly.zip"
)
SOURCE_NAME = "nmdb-mortgage-performance-statistics-national-census-areas-quarterly.csv"
DATA_NAME = "nmdb-performance-national-quarterly-2026q2.csv"
RECEIPT_NAME = "nmdb-performance-national-quarterly-2026q2-receipt.json"
HEADERS = {
    "SOURCE", "FREQUENCY", "GEOLEVEL", "GEOID", "GEONAME", "MARKET",
    "PERIOD", "YEAR", "QUARTER", "MONTH", "SUPPRESSED", "SERIESID", "VALUE1",
}
MARKETS = {
    "All Mortgages",
    "Enterprise Acquisitions",
    "Government / Non-Conventional",
    "Other Conventional Market",
}
SERIES = {"P3089DL", "P90DL", "PFORECL", "PFORB"}
OUTPUT_FIELDS = [
    "source", "frequency", "geo_level", "geo_id", "geo_name", "market",
    "period", "year", "quarter", "month", "suppressed", "series_id", "value_pct",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def quarter_periods() -> list[str]:
    return [f"{year}Q{quarter}" for year in range(2002, 2027) for quarter in range(1, 5)
            if (year, quarter) <= (2026, 2)]


def read_official_rows(archive_bytes: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = [name for name in archive.namelist() if Path(name).name == SOURCE_NAME]
        if len(names) != 1:
            raise ValueError("FHFA ZIP must contain exactly one expected quarterly CSV")
        with archive.open(names[0]) as stream:
            text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            if not reader.fieldnames or set(reader.fieldnames) != HEADERS:
                raise ValueError("FHFA NMDB performance CSV has an unexpected header")
            rows = list(reader)
    if not rows:
        raise ValueError("FHFA NMDB performance CSV is empty")
    return rows


def curate(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = [row for row in rows if row["GEOLEVEL"] == "National" and row["GEOID"] == "USA"]
    if not selected:
        raise ValueError("FHFA NMDB file has no United States national observations")
    if {row["MARKET"] for row in selected} != MARKETS or {row["SERIESID"] for row in selected} != SERIES:
        raise ValueError("FHFA national observations do not cover the four expected markets/series")
    periods = quarter_periods()
    seen: set[tuple[str, str, str]] = set()
    result = []
    for row in selected:
        key = (row["MARKET"], row["SERIESID"], row["PERIOD"])
        if key in seen:
            raise ValueError(f"Duplicate FHFA national observation: {key}")
        seen.add(key)
        if row["PERIOD"] not in periods or row["SOURCE"] != "NMDB" or row["FREQUENCY"] != "Quarterly":
            raise ValueError(f"Unexpected FHFA NMDB observation scope: {row}")
        if row["SUPPRESSED"] not in {"0", "1"}:
            raise ValueError("FHFA SUPPRESSED must be 0 or 1")
        if row["VALUE1"]:
            value = float(row["VALUE1"])
            if not 0 <= value <= 100:
                raise ValueError(f"FHFA performance percent outside 0–100: {key}={value}")
        result.append({
            "source": row["SOURCE"], "frequency": row["FREQUENCY"],
            "geo_level": row["GEOLEVEL"], "geo_id": row["GEOID"],
            "geo_name": row["GEONAME"], "market": row["MARKET"],
            "period": row["PERIOD"], "year": row["YEAR"],
            "quarter": row["QUARTER"], "month": row["MONTH"],
            "suppressed": row["SUPPRESSED"], "series_id": row["SERIESID"],
            "value_pct": row["VALUE1"],
        })
    expected_count = len(MARKETS) * len(SERIES) * len(periods)
    if len(result) != expected_count or len(seen) != expected_count:
        raise ValueError(
            f"Incomplete FHFA national coverage: {len(result)} rows; expected {expected_count}"
        )
    if {row["period"] for row in result} != set(periods):
        raise ValueError("FHFA quarterly coverage is not contiguous from 2002Q1 to 2026Q2")
    result.sort(key=lambda row: (periods.index(row["period"],), row["market"], row["series_id"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-zip", type=Path, help="Use an already-downloaded official ZIP")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    archive_path = args.source_zip.resolve() if args.source_zip else (
        root / "data/public/mortgage/nmdb-2026q2/fhfa-nmdb-performance-national-census-areas-quarterly.zip"
    )
    if args.source_zip:
        archive_bytes = archive_path.read_bytes()
    else:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "CreditAtlas public data research"})
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status != 200:
                raise RuntimeError(f"FHFA download returned HTTP {response.status}")
            archive_bytes = response.read()
        archive_path.write_bytes(archive_bytes)

    rows = curate(read_official_rows(archive_bytes))
    data_path = root / "docs/data" / DATA_NAME
    receipt_path = root / "docs/data" / RECEIPT_NAME
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with data_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    data_bytes = data_path.read_bytes()
    receipt = {
        "schema_version": 1,
        "status": "ACQUIRED_AND_CURATED",
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "publisher": "Federal Housing Finance Agency",
        "source_url": SOURCE_URL,
        "source_archive": archive_path.name,
        "source_archive_sha256": sha256_bytes(archive_bytes),
        "source_member": SOURCE_NAME,
        "source_member_sha256": sha256_bytes(read_official_rows_member(archive_bytes)),
        "curated_file": f"docs/data/{DATA_NAME}",
        "curated_file_sha256": sha256_bytes(data_bytes),
        "geography": "National / USA only",
        "quarter_range": [rows[0]["period"], rows[-1]["period"]],
        "markets": sorted(MARKETS),
        "series_ids": sorted(SERIES),
        "rows": len(rows),
        "suppressed_rows": sum(row["suppressed"] == "1" for row in rows),
        "grain": "one national market × performance series × quarter aggregate",
        "source_caveat": "latest two quarters are preliminary and may be revised per FHFA documentation",
        "raw_archive_retained_in_public_repository": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"data": str(data_path), "rows": len(rows), "receipt": str(receipt_path),
                      "source_zip_sha256": receipt["source_archive_sha256"]}, indent=2))


def read_official_rows_member(archive_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = [name for name in archive.namelist() if Path(name).name == SOURCE_NAME]
        if len(names) != 1:
            raise ValueError("FHFA ZIP must contain exactly one expected quarterly CSV")
        return archive.read(names[0])


if __name__ == "__main__":
    main()
