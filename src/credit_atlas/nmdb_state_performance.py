"""Validated, state-only FHFA NMDB mortgage performance aggregates."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from . import nmdb_performance as national


SOURCE_URL = "https://www.fhfa.gov/document/d/nmdb/nmdb-mortgage-performance-statistics-states-quarterly.zip"
INDEX_URL = national.INDEX_URL
DOC_URL = national.DOC_URL
DATA_NAME = "nmdb-performance-state-quarterly-2026q2.csv"
RECEIPT_NAME = "nmdb-performance-state-quarterly-2026q2-receipt.json"
FIELDS = national.FIELDS
STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nmdb_state_performance_report(root: Path, state_code: str | None = None) -> dict:
    """Read curated state aggregates and reject provenance, schema or coverage drift."""
    base = root / "docs" / "data"
    data_path, receipt_path = base / DATA_NAME, base / RECEIPT_NAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "ACQUIRED_AND_CURATED" or receipt.get("curated_file_sha256") != _sha256(data_path):
        raise ValueError("NMDB state data does not match its acquisition receipt")
    if receipt.get("source_url") != SOURCE_URL or receipt.get("geography") != "States and District of Columbia only":
        raise ValueError("NMDB state source provenance or geography changed")
    with data_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames) != FIELDS:
            raise ValueError("Unexpected curated NMDB state schema")
        rows = list(reader)
    quarters = national._quarters()
    expected = {(geo, market, series, quarter) for geo in STATE_CODES for market in national.MARKETS for series in national.SERIES for quarter in quarters}
    seen: set[tuple[str, str, str, str]] = set()
    output = []
    names: dict[str, str] = {}
    for row in rows:
        if row["source"] != "NMDB" or row["frequency"] != "Quarterly" or row["geo_level"] != "State" or row["geo_id"] not in STATE_CODES:
            raise ValueError("NMDB state data contains unexpected source or geography")
        if row["market"] not in national.MARKET_DESCRIPTIONS or row["series_id"] not in national.SERIES:
            raise ValueError("NMDB state data contains an unknown market or series")
        if row["period"] not in quarters or not re.fullmatch(r"\d{4}Q[1-4]", row["period"]):
            raise ValueError("NMDB state data contains an invalid quarter")
        if row["suppressed"] not in {"0", "1"}:
            raise ValueError("NMDB suppression flag must be 0 or 1")
        key = (row["geo_id"], row["market"], row["series_id"], row["period"])
        if key in seen:
            raise ValueError(f"Duplicate NMDB state observation: {key}")
        seen.add(key)
        if row["geo_id"] in names and names[row["geo_id"]] != row["geo_name"]:
            raise ValueError(f"NMDB state name changed within {row['geo_id']}")
        names[row["geo_id"]] = row["geo_name"]
        value = None if row["value_pct"] == "" else float(row["value_pct"])
        if value is not None and not 0 <= value <= 100:
            raise ValueError(f"NMDB percentage outside 0–100: {key}")
        if row["suppressed"] == "1" and value is not None:
            raise ValueError(f"Suppressed NMDB value must not be published: {key}")
        if row["series_id"] != "PFORB" and value is None and row["suppressed"] != "1":
            raise ValueError(f"Unexpected blank NMDB state value: {key}")
        output.append({**row, "year": int(row["year"]), "quarter_number": int(row["quarter"]),
                       "suppressed": row["suppressed"] == "1", "value_pct": value})
    if seen != expected:
        raise ValueError(f"NMDB state coverage is incomplete: {len(seen)} of {len(expected)} keys")
    if set(names) != STATE_CODES:
        raise ValueError("NMDB state file must cover 50 states and DC")
    if state_code is not None and state_code not in names:
        raise ValueError("State code must be one of the 50 states or DC")
    quarter_position = {period: index for index, period in enumerate(quarters)}
    output.sort(key=lambda row: (row["geo_id"], quarter_position[row["period"]], national.MARKETS.index(row["market"]), row["series_id"]))
    if state_code is not None:
        output = [row for row in output if row["geo_id"] == state_code]
    latest = [row for row in output if row["period"] == quarters[-1]]
    state_names = [{"geo_id": code, "geo_name": names[code]} for code in sorted(names)]
    return {
        "schema_version": "fhfa-nmdb-performance-state-v1", "status": "AVAILABLE",
        "source": {"title": "NMDB Residential Mortgage Performance Statistics — States", "publisher": "Federal Housing Finance Agency",
                   "release_date": "2026-09-30", "data_through": quarters[-1], "index_url": INDEX_URL,
                   "download_url": SOURCE_URL, "technical_notes_url": DOC_URL,
                   "source_archive_sha256": receipt["source_archive_sha256"], "source_member_sha256": receipt["source_member_sha256"],
                   "curated_file_sha256": receipt["curated_file_sha256"]},
        "geography": "50 states and District of Columbia", "selected_state": state_code, "states": state_names,
        "grain": "one state × mortgage market × performance series × quarter", "periods": quarters,
        "markets": [{"name": market, "description": national.MARKET_DESCRIPTIONS[market]} for market in national.MARKETS],
        "series": national.SERIES, "latest": latest, "observations": output,
        "definitions": {"denominator": "Active mortgages at quarter end; not an origination-vintage or fixed-horizon cohort denominator.",
                        "suppression": "Publisher suppresses cells with fewer than three loan records; blank suppressed values must not be treated as zero.",
                        "forbearance": "PFORB starts 2019Q4; earlier blanks mean unavailable, not zero.",
                        "preliminary": "Latest two quarters are preliminary and may be revised due to credit-bureau reporting lag."},
        "limitations": ["Aggregate 5% NMDB sample estimates, not state loan-level records or independent event labels; do not train D01 or estimate state borrower PD directly from these rates.",
                        "Performance is the quarter-end status share among active loans, not a fixed-horizon default probability.",
                        "Small cells are suppressed (<3 loan records); missing/suppressed values are not zero.",
                        "FHFA warns seriously past-due loans may be undercounted in 2006–2012 due to credit-history purging.",
                        "Latest two quarters (2026Q1–2026Q2) are preliminary; state differences reflect coverage and portfolio mix as well as risk.",
                        "The sample represents owner-occupied and site-built mortgages better than investor or manufactured-home mortgages.",
                        "Do not sum All Mortgages with its market components or join this aggregate panel to individual NSMO/Freddie loans."],
    }
