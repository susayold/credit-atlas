"""Validated, national-only FHFA NMDB mortgage performance aggregates."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


SOURCE_URL = (
    "https://www.fhfa.gov/document/d/nmdb/"
    "nmdb-mortgage-performance-statistics-national-census-areas-quarterly.zip"
)
INDEX_URL = "https://www.fhfa.gov/data/nmdb"
DOC_URL = (
    "https://www.fhfa.gov/document/d/nmdb/"
    "nmdb-aggregate-statistics-data-dictionary-technical-notes-2026q1.pdf"
)
DATA_NAME = "nmdb-performance-national-quarterly-2026q2.csv"
RECEIPT_NAME = "nmdb-performance-national-quarterly-2026q2-receipt.json"
MARKETS = (
    "All Mortgages", "Enterprise Acquisitions",
    "Government / Non-Conventional", "Other Conventional Market",
)
SERIES = {
    "P3089DL": {
        "label": "30–89 days delinquent",
        "description": "FHFA combines the 30- and 60-day-past-due categories (30–59 and 60–89 days in the technical notes); divided by active mortgages at quarter end.",
    },
    "P90DL": {
        "label": "90+ days past due",
        "description": "Active mortgages at least 90, 120, 150 or 180 days past due divided by active mortgages at quarter end.",
    },
    "PFORECL": {
        "label": "Foreclosure / bankruptcy / deed-in-lieu",
        "description": "Active mortgages in foreclosure, bankruptcy or deed-in-lieu divided by active mortgages at quarter end.",
    },
    "PFORB": {
        "label": "In forbearance",
        "description": "Active mortgages reported in forbearance divided by active mortgages at quarter end; published starting 2019Q4.",
    },
}
MARKET_DESCRIPTIONS = {
    "All Mortgages": "All first-lien, closed-end single-family mortgages in the NMDB sample.",
    "Enterprise Acquisitions": "Non-government loans acquired by Fannie Mae or Freddie Mac.",
    "Government / Non-Conventional": "Government insured, guaranteed or direct mortgages.",
    "Other Conventional Market": "Non-government, non-enterprise conventional loans; includes jumbo, FHLB AMA, credit-union, private-label and other portfolio loans.",
}
FIELDS = {
    "source", "frequency", "geo_level", "geo_id", "geo_name", "market",
    "period", "year", "quarter", "month", "suppressed", "series_id", "value_pct",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quarters() -> list[str]:
    return [f"{year}Q{quarter}" for year in range(2002, 2027) for quarter in range(1, 5)
            if (year, quarter) <= (2026, 2)]


def nmdb_performance_report(root: Path) -> dict:
    """Read the curated FHFA aggregates and fail closed on data/receipt drift."""
    base = root / "docs" / "data"
    data_path = base / DATA_NAME
    receipt_path = base / RECEIPT_NAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "ACQUIRED_AND_CURATED" or receipt.get("curated_file_sha256") != _sha256(data_path):
        raise ValueError("NMDB curated data does not match its acquisition receipt")
    if receipt.get("source_url") != SOURCE_URL or receipt.get("geography") != "National / USA only":
        raise ValueError("NMDB source provenance or geographic scope changed")
    with data_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames) != FIELDS:
            raise ValueError("Unexpected curated NMDB performance schema")
        rows = list(reader)
    quarters = _quarters()
    if len(rows) != len(quarters) * len(MARKETS) * len(SERIES) or len(rows) != receipt.get("rows"):
        raise ValueError("Curated NMDB performance row count does not reconcile")

    seen: set[tuple[str, str, str]] = set()
    output = []
    for row in rows:
        if row["source"] != "NMDB" or row["frequency"] != "Quarterly" or row["geo_level"] != "National" or row["geo_id"] != "USA":
            raise ValueError("NMDB data contains an unexpected source, frequency or geography")
        if row["market"] not in MARKET_DESCRIPTIONS or row["series_id"] not in SERIES:
            raise ValueError("NMDB data contains an unknown market or series")
        if row["period"] not in quarters or not re.fullmatch(r"\d{4}Q[1-4]", row["period"]):
            raise ValueError("NMDB data contains an invalid quarter")
        key = (row["market"], row["series_id"], row["period"])
        if key in seen:
            raise ValueError(f"Duplicate NMDB observation: {key}")
        seen.add(key)
        if row["suppressed"] not in {"0", "1"}:
            raise ValueError("NMDB suppression flag must be 0 or 1")
        value = None if row["value_pct"] == "" else float(row["value_pct"])
        if value is not None and not 0 <= value <= 100:
            raise ValueError(f"NMDB percentage outside 0–100: {key}")
        output.append({**row, "year": int(row["year"]), "quarter_number": int(row["quarter"]),
                       "suppressed": row["suppressed"] == "1", "value_pct": value})
    expected = {(market, series, quarter) for market in MARKETS for series in SERIES for quarter in quarters}
    if seen != expected:
        raise ValueError("NMDB national quarter × market × series coverage is incomplete")
    output.sort(key=lambda row: (quarters.index(row["period"]), MARKETS.index(row["market"]), row["series_id"]))

    latest_period = quarters[-1]
    latest = [row for row in output if row["period"] == latest_period]
    series_coverage = {}
    for code, meta in SERIES.items():
        valid = [row["period"] for row in output if row["series_id"] == code and row["value_pct"] is not None]
        series_coverage[code] = {**meta, "first_nonblank_quarter": min(valid, key=quarters.index) if valid else None,
                                 "last_nonblank_quarter": max(valid, key=quarters.index) if valid else None,
                                 "nonblank_observations": len(valid)}
    return {
        "schema_version": "fhfa-nmdb-performance-aggregate-v1",
        "status": "AVAILABLE",
        "source": {
            "title": "NMDB Residential Mortgage Performance Statistics — quarterly",
            "publisher": "Federal Housing Finance Agency",
            "release_date": "2026-09-30",
            "data_through": latest_period,
            "index_url": INDEX_URL,
            "download_url": SOURCE_URL,
            "technical_notes_url": DOC_URL,
            "source_archive_sha256": receipt["source_archive_sha256"],
            "source_member_sha256": receipt["source_member_sha256"],
            "curated_file_sha256": receipt["curated_file_sha256"],
        },
        "geography": "United States national aggregate",
        "grain": "one mortgage market × performance series × quarter",
        "periods": quarters,
        "markets": [{"name": market, "description": MARKET_DESCRIPTIONS[market]} for market in MARKETS],
        "series": series_coverage,
        "latest": latest,
        "observations": output,
        "definitions": {
            "denominator": "Active mortgages at quarter end; performance rates are not origination-vintage or fixed-horizon cohort rates.",
            "performance_basis": "Credit-bureau-reported status with FHFA stale-account rules; values are percentages, not fractions.",
            "forbearance": "PFORB is published from 2019Q4; prior quarters remain blank in the source and are not zero.",
            "latest_vintages": "The latest two quarters are preliminary and may be revised as credit-bureau reporting lag closes.",
        },
        "limitations": [
            "This is an aggregate 5% mortgage-sample benchmark, not borrower/loan-level rows; it does not add NSMO event labels or train a PD model.",
            "Performance is measured among active loans at quarter end and does not represent fixed-horizon cumulative default risk.",
            "The series use credit-bureau reporting and FHFA stale-account rules; reporting lag and forbearance conventions can differ from HUD, servicer or delinquency datasets.",
            "FHFA identifies possible undercounting of seriously past-due loans from 2006 through 2012 due to credit-history purging.",
            "The latest two quarters, including 2026Q1 and 2026Q2, are preliminary and may be revised.",
            "The NMDB sample represents owner-occupied and site-built mortgages better than investor or manufactured-home mortgages.",
            "Market categories are presented as separate publisher series; do not sum the overall All Mortgages series with its market components.",
        ],
    }
