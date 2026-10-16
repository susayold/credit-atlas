"""Read the acquired CFPB public monthly mortgage delinquency aggregates."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .workspace import sha256

SOURCE_PAGE = "https://www.consumerfinance.gov/data-research/mortgage-performance-trends/download-the-data/"
ABOUT_PAGE = "https://www.consumerfinance.gov/data-research/mortgage-performance-trends/about-the-data/"
BASE_URL = "https://files.consumerfinance.gov/data/mortgage-performance/downloads/"
FILES = {
    "county": {
        "30_89": "CountyMortgagesPercent-30-89DaysLate-thru-2025-12.csv",
        "90_plus": "CountyMortgagesPercent-90-plusDaysLate-thru-2025-12.csv",
    },
    "state": {
        "30_89": "StateMortgagesPercent-30-89DaysLate-thru-2025-12.csv",
        "90_plus": "StateMortgagesPercent-90-plusDaysLate-thru-2025-12.csv",
    },
}
MONTHS = [f"{year:04d}-{month:02d}" for year in range(2008, 2026) for month in range(1, 13)]
METRIC_LABELS = {"30_89": "30–89 days delinquent", "90_plus": "90+ days delinquent"}


def _fips(value: str | None) -> str:
    return (value or "").strip().strip("'").strip('"')


def read(root: Path, query: dict[str, str] | None = None) -> dict:
    query = query or {}
    allowed = {"geography_type", "geoid"}
    if set(query) - allowed:
        raise ValueError("CFPB mortgage trends accepts geography_type and geoid only")
    geography_type = query.get("geography_type", "National")
    geoid = query.get("geoid", "-----")
    if geography_type not in {"National", "State", "County"}:
        raise ValueError("Unsupported CFPB geography type")

    folders = sorted(
        (root / "data" / "private" / "public-context").glob("cfpb-mortgage-performance-trends-*"),
        reverse=True,
    )
    for folder in folders:
        receipt_path = folder / "receipt.json"
        if not receipt_path.is_file():
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("source") != "CFPB Mortgage Performance Trends":
            continue
        profiles = {profile.get("file"): profile for profile in receipt.get("profiles", [])}
        tables: dict[str, dict[str, dict]] = {"county": {}, "state": {}}
        options: dict[str, dict[str, dict]] = {"National": {}, "State": {}, "County": {}}
        for kind, metric_files in FILES.items():
            for metric, filename in metric_files.items():
                path = folder / filename
                profile = profiles.get(filename)
                if not path.is_file() or not profile:
                    raise ValueError(f"CFPB acquisition file or receipt entry is missing: {filename}")
                if path.stat().st_size != profile.get("bytes") or sha256(path) != profile.get("sha256"):
                    raise ValueError(f"CFPB source file hash differs from acquisition receipt: {filename}")
                with path.open(newline="", encoding="utf-8-sig") as stream:
                    reader = csv.DictReader(stream)
                    expected_geo_fields = ["RegionType", "State", "Name", "FIPSCode"] if kind == "county" else ["RegionType", "Name", "FIPSCode"]
                    if reader.fieldnames != expected_geo_fields + MONTHS:
                        raise ValueError(f"Unexpected CFPB mortgage-trends schema: {filename}")
                    rows = list(reader)
                if len(rows) != profile.get("rows_including_national"):
                    raise ValueError(f"CFPB source row count differs from acquisition receipt: {filename}")
                metric_rows: dict[str, dict] = {}
                for row in rows:
                    region = row["RegionType"]
                    code = _fips(row["FIPSCode"])
                    if region == "National":
                        key = "-----"
                        region_type = "National"
                    else:
                        key = code
                        region_type = "County" if kind == "county" else "State"
                    if not key or key in metric_rows:
                        raise ValueError(f"Duplicate or missing CFPB geography identifier in {filename}")
                    values = []
                    for month in MONTHS:
                        raw = (row.get(month) or "").strip()
                        if not raw:
                            raise ValueError(f"Unexpected blank CFPB observation in {filename} at {key}/{month}")
                        try:
                            value = float(raw)
                        except ValueError as exc:
                            raise ValueError(f"Invalid CFPB percentage in {filename} at {key}/{month}") from exc
                        if not 0 <= value <= 100:
                            raise ValueError(f"CFPB percentage outside [0, 100] in {filename} at {key}/{month}")
                        values.append(value)
                    metric_rows[key] = {"geography_type": region_type, "geoid": key, "name": row["Name"],
                                        "state": row.get("State", ""), "values": values}
                    options[region_type][key] = {"geography_type": region_type, "geoid": key,
                                                 "name": row["Name"], "state": row.get("State", "")}
                tables[kind][metric] = metric_rows
        if geography_type == "National":
            kind = "county"
        else:
            kind = geography_type.lower()
        first = tables[kind]["30_89"].get(geoid)
        second = tables[kind]["90_plus"].get(geoid)
        if not first or not second:
            raise ValueError("Selected CFPB geography is unavailable in both delinquency files")
        if first["name"] != second["name"] or first["values"] is None or second["values"] is None:
            raise ValueError("CFPB delinquency tables disagree on the selected geography")
        series = [{"period": month, "delinquent_30_89_percent": first["values"][i],
                   "delinquent_90plus_percent": second["values"][i]} for i, month in enumerate(MONTHS)]
        selected = {"geography_type": geography_type, "geoid": geoid, "name": first["name"], "state": first["state"]}
        geography_options = [options["National"]["-----"]]
        geography_options.extend(options["State"][key] for key in sorted(options["State"]))
        geography_options.extend(options["County"][key] for key in sorted(options["County"]))
        return {
            "status": "AVAILABLE", "dataset": "CFPB Mortgage Performance Trends",
            "visibility": "private", "public_release_approved": False,
            "source_page": SOURCE_PAGE, "about_page": ABOUT_PAGE,
            "source_release_date": receipt.get("official_published_date"),
            "retrieved_at": receipt.get("retrieved_at"),
            "first_period": MONTHS[0], "last_period": MONTHS[-1],
            "selected_geography": selected, "geographies": geography_options,
            "rows": series,
            "metrics": METRIC_LABELS,
            "quality": {"monthly_periods": len(MONTHS), "county_geographies": len(options["County"]),
                        "state_geographies": len(options["State"]),
                        "selected_source_hashes": {metric: profiles[filename]["sha256"]
                                                    for metric, filename in FILES[kind].items()}},
            "limitations": [
                "Rates are published as percentage points; they are not loan counts, UPB, or borrower-level probabilities.",
                "County/state data derive from the NMDB sample and are not an independent sample from FHFA's NMDB aggregates.",
                "Geographies with fewer than 1,000 sample mortgages are omitted; county coverage is not exhaustive.",
                "Reported-missing periods may be imputed and historical rates can be revised; emergency reporting may suppress delinquency.",
                "90+ day delinquency excludes mortgages already in foreclosure; do not add the two rates as if they were a transition curve.",
                "Do not join this aggregate series to Freddie loan records or treat it as a loan-level feature, target, or vintage.",
            ],
        }
    return {"status": "UNAVAILABLE", "reason": "CFPB mortgage performance trends have not been acquired.",
            "source_page": SOURCE_PAGE, "rows": [], "geographies": []}
