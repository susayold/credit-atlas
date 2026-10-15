"""Curate FHFA's official quarterly state-level NMDB performance archive."""

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

from credit_atlas import nmdb_performance as national
from credit_atlas.nmdb_state_performance import DATA_NAME, RECEIPT_NAME, SOURCE_URL, STATE_CODES


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = "nmdb-mortgage-performance-statistics-states-quarterly.csv"
INPUT_HEADERS = {"SOURCE", "FREQUENCY", "GEOLEVEL", "GEOID", "GEONAME", "MARKET", "PERIOD", "YEAR", "QUARTER", "MONTH", "SUPPRESSED", "SERIESID", "VALUE1"}
OUTPUT_FIELDS = ["source", "frequency", "geo_level", "geo_id", "geo_name", "market", "period", "year", "quarter", "month", "suppressed", "series_id", "value_pct"]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_member(archive_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = [name for name in archive.namelist() if Path(name).name == SOURCE_NAME]
        if len(names) != 1:
            raise ValueError("FHFA ZIP must contain exactly one expected state CSV")
        return archive.read(names[0])


def curate(archive_bytes: bytes) -> list[dict[str, str]]:
    text = io.TextIOWrapper(io.BytesIO(read_member(archive_bytes)), encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text)
    if not reader.fieldnames or set(reader.fieldnames) != INPUT_HEADERS:
        raise ValueError("FHFA NMDB state CSV has an unexpected header")
    periods = national._quarters()
    output = []
    seen = set()
    state_names = {}
    for row in reader:
        if row["GEOLEVEL"] != "State":
            raise ValueError("State archive contains a non-state geography")
        if row["GEOID"] not in STATE_CODES:
            raise ValueError(f"Unexpected state GEOID: {row['GEOID']}")
        if row["SOURCE"] != "NMDB" or row["FREQUENCY"] != "Quarterly" or row["PERIOD"] not in periods:
            raise ValueError(f"Unexpected source or quarter: {row}")
        if row["MARKET"] not in national.MARKETS or row["SERIESID"] not in national.SERIES:
            raise ValueError("Unknown NMDB market or performance series")
        quarter = int(row["QUARTER"])
        if row["YEAR"] != row["PERIOD"][:4] or row["PERIOD"] != f"{row['YEAR']}Q{quarter}" or int(row["MONTH"]) != quarter * 3:
            raise ValueError(f"Quarter fields do not reconcile: {row}")
        if row["SUPPRESSED"] not in {"0", "1"}:
            raise ValueError("FHFA SUPPRESSED must be 0 or 1")
        key = (row["GEOID"], row["MARKET"], row["SERIESID"], row["PERIOD"])
        if key in seen:
            raise ValueError(f"Duplicate FHFA state observation: {key}")
        seen.add(key)
        if row["GEOID"] in state_names and state_names[row["GEOID"]] != row["GEONAME"]:
            raise ValueError(f"State name changed within {row['GEOID']}")
        state_names[row["GEOID"]] = row["GEONAME"]
        value = row["VALUE1"]
        if value in {"", "."}:
            value = ""
        else:
            parsed = float(value)
            if not 0 <= parsed <= 100:
                raise ValueError(f"Rate outside 0–100: {key}={value}")
        if row["SUPPRESSED"] == "1" and value:
            raise ValueError(f"Suppressed value must be blank: {key}")
        if row["SERIESID"] != "PFORB" and not value and row["SUPPRESSED"] != "1":
            raise ValueError(f"Unexpected blank value: {key}")
        output.append({"source": row["SOURCE"], "frequency": row["FREQUENCY"], "geo_level": row["GEOLEVEL"],
                       "geo_id": row["GEOID"], "geo_name": row["GEONAME"], "market": row["MARKET"],
                       "period": row["PERIOD"], "year": row["YEAR"], "quarter": row["QUARTER"], "month": row["MONTH"],
                       "suppressed": row["SUPPRESSED"], "series_id": row["SERIESID"], "value_pct": value})
    expected = len(STATE_CODES) * len(national.MARKETS) * len(national.SERIES) * len(periods)
    if len(output) != expected or len(seen) != expected or set(state_names) != STATE_CODES:
        raise ValueError(f"Incomplete state coverage: {len(output)} rows; expected {expected}")
    quarter_index = {period: index for index, period in enumerate(periods)}
    output.sort(key=lambda row: (row["geo_id"], quarter_index[row["period"]], national.MARKETS.index(row["market"]), row["series_id"]))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-zip", type=Path, help="Use an already downloaded official ZIP")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    archive_path = args.source_zip.resolve() if args.source_zip else root / "data/private/nmdb-performance-state/source/nmdb-mortgage-performance-statistics-states-quarterly.zip"
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
    rows = curate(archive_bytes)
    data_path, receipt_path = root / "docs/data" / DATA_NAME, root / "docs/data" / RECEIPT_NAME
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with data_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    periods = national._quarters()
    receipt = {"schema_version": 1, "status": "ACQUIRED_AND_CURATED", "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
               "publisher": "Federal Housing Finance Agency", "release_date": "2026-09-30", "source_url": SOURCE_URL,
               "source_archive": archive_path.name, "source_archive_sha256": sha256_bytes(archive_bytes),
               "source_member": SOURCE_NAME, "source_member_sha256": sha256_bytes(read_member(archive_bytes)),
               "curated_file": f"docs/data/{DATA_NAME}", "curated_file_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
               "geography": "States and District of Columbia only", "states": 51, "quarter_range": [periods[0], periods[-1]],
               "markets": list(national.MARKETS), "series_ids": list(national.SERIES), "rows": len(rows),
               "suppressed_rows": sum(row["suppressed"] == "1" for row in rows),
               "blank_rows": sum(not row["value_pct"] for row in rows),
               "pre_2019q4_forbearance_blank_rows": sum(row["series_id"] == "PFORB" and row["period"] < "2019Q4" and not row["value_pct"] for row in rows),
               "grain": "one state × mortgage market × performance series × quarter aggregate",
               "caveat": "Latest two quarters are preliminary; PFORB starts 2019Q4; publisher suppresses small cells; no loan-level rows.",
               "raw_archive_retained_in_public_repository": False}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"data": str(data_path), "rows": len(rows), "suppressed": receipt["suppressed_rows"], "receipt": str(receipt_path)}, indent=2))


if __name__ == "__main__":
    main()
