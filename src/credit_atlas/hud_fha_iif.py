"""Private aggregate profile for HUD FHA Insurance-in-Force by Census tract."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from .workspace import write_new

SOURCE_PAGE = "https://catalog.data.gov/dataset/fha-insurance-in-force-by-tract"
SOURCE_URL = "https://hudgis-hud.opendata.arcgis.com/api/download/v1/items/8f7af6a831dc45f1befc5bee7bc682df/csv?layers=0"
EXPECTED_HEADERS = [
    "OBJECTID", "GEOID", "STUSAB", "STATE", "COUNTY", "TRACT", "EACODE", "EANAME", "NAME",
    "AREALAND", "AREASQMI", "POPDENSITY", "HUDENSITY", "P001001", "H001001",
    "UNPD_BAL_SUM", "IIF_CNT", "ORIG_MRTG_AMT_SUM", "Shape__Area", "Shape__Length",
]
EXPECTED_ROWS = 85154
METADATA_COVERAGE = "2025-03"
LIMITATIONS = [
    "Aggregate FHA active-loan exposure by 2010 Census tract; no loan-level rows, repayment histories, delinquency/default labels, denials, or realized losses.",
    "The download contains a static tract snapshot. The catalog/metadata declares coverage through 2025-03, while the FeatureServer layer description still says 09/2021; reconcile this publisher metadata discrepancy before trend or current-exposure claims.",
    "Blank balance/count cells remain missing and are never recoded to zero. The source also contains -4 in balance/amount fields; its meaning is undocumented, so it is quarantined as a source code and excluded from sums.",
    "Do not join to the Freddie loan-level sample, infer borrower risk, or use tract balances/counts as individual model predictors.",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_csv(path: Path, *, expected_rows: int | None = None, verify_release: bool = True) -> dict:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("HUD FHA tract CSV is missing or exceeds the 100 MiB bound")
    keys: set[str] = set()
    state_counts: dict[str, int] = defaultdict(int)
    state_totals: dict[str, dict[str, float | int]] = defaultdict(lambda: {
        "tract_rows": 0, "tracts_with_balance": 0, "active_insured_loans": 0,
        "unpaid_balance_usd": 0.0, "original_mortgage_amount_usd": 0.0,
    })
    totals = {"active_insured_loans": 0, "unpaid_balance_usd": 0.0, "original_mortgage_amount_usd": 0.0}
    missing = {"active_insured_loans": 0, "unpaid_balance_usd": 0, "original_mortgage_amount_usd": 0}
    special_values: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rows = 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != EXPECTED_HEADERS:
                raise ValueError("Unexpected HUD FHA tract CSV schema")
            for row in reader:
                rows += 1
                if None in row or any(row.get(name) is None for name in EXPECTED_HEADERS):
                    raise ValueError("Malformed HUD FHA tract CSV row")
                geoid = row["GEOID"].strip()
                state = row["STUSAB"].strip()
                if len(geoid) != 11 or not geoid.isdigit() or not state or geoid in keys:
                    raise ValueError("Blank/duplicate tract key or state in HUD FHA file")
                keys.add(geoid)
                state_counts[state] += 1
                bucket = state_totals[state]
                bucket["tract_rows"] += 1
                for field, output in (("IIF_CNT", "active_insured_loans"),
                                      ("UNPD_BAL_SUM", "unpaid_balance_usd"),
                                      ("ORIG_MRTG_AMT_SUM", "original_mortgage_amount_usd")):
                    raw = row[field].strip()
                    if not raw:
                        missing[output] += 1
                        continue
                    value = float(raw)
                    if value < 0:
                        special_values[output][raw] += 1
                        continue
                    if output == "active_insured_loans":
                        if not value.is_integer():
                            raise ValueError("Non-integer insured-loan count in HUD FHA file")
                        totals[output] += int(value)
                        bucket[output] += int(value)
                    else:
                        totals[output] += value
                        bucket[output] += value
                    if output == "unpaid_balance_usd":
                        bucket["tracts_with_balance"] += 1
    except (OSError, UnicodeError, csv.Error) as error:
        raise ValueError("Unable to parse HUD FHA tract CSV") from error
    if rows != len(keys):
        raise ValueError("HUD FHA tract unique-key count differs from row count")
    if expected_rows is not None and rows != expected_rows:
        raise ValueError(f"HUD FHA tract row count differs from expected {expected_rows}")
    if verify_release and rows != EXPECTED_ROWS:
        raise ValueError(f"HUD FHA tract row count differs from source contract {EXPECTED_ROWS}")
    return {
        "schema_version": 1,
        "dataset": "HUD FHA Insurance in Force by Tract",
        "source_page": SOURCE_PAGE,
        "source_url": SOURCE_URL,
        "metadata_coverage": METADATA_COVERAGE,
        "source_sha256": sha256(path),
        "bytes": path.stat().st_size,
        "rows": rows,
        "columns": len(EXPECTED_HEADERS),
        "unique_tracts": len(keys),
        "duplicate_tracts": 0,
        "malformed_rows": 0,
        "states_or_territories": len(state_counts),
        "national_totals_nonblank_tracts": totals,
        "missing_metric_tracts": missing,
        "uninterpreted_source_codes": {field: dict(codes) for field, codes in special_values.items()},
        "state_aggregates": {key: state_totals[key] for key in sorted(state_totals)},
        "limitations": LIMITATIONS,
        "visibility": "private",
        "public_release_approved": False,
    }


def acquire_and_profile(root: Path, source_path: Path | None = None) -> dict:
    folder = Path(root).resolve() / "data" / "private" / "hud-fha-iif-tract"
    folder.mkdir(parents=True, exist_ok=True)
    dataset = Path(source_path) if source_path else folder / "fha-insurance-in-force-by-tract.csv"
    profile = profile_csv(dataset)
    version = profile["source_sha256"][:12]
    profile_name = f"profile-{version}.json"
    receipt_name = f"receipt-{version}.json"
    profile_path = folder / profile_name
    profile_text = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    if profile_path.exists():
        if profile_path.read_text(encoding="utf-8") != profile_text:
            raise ValueError("An existing HUD FHA profile for this source hash differs")
    else:
        write_new(profile_path, profile)
    receipt = {
        "status": "PASS", "dataset": profile["dataset"], "source_sha256": profile["source_sha256"],
        "profile_file": profile_name, "profile_sha256": sha256(profile_path), "rows": profile["rows"],
        "source_url": SOURCE_URL, "catalog_page": SOURCE_PAGE,
    }
    receipt_path = folder / receipt_name
    if receipt_path.exists():
        if json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
            raise ValueError("An existing HUD FHA receipt for this source hash differs")
    else:
        write_new(receipt_path, receipt)
    return {**receipt, "profile": profile}


def read(root: Path) -> dict:
    folder = Path(root).resolve() / "data" / "private" / "hud-fha-iif-tract"
    receipts = sorted(folder.glob("receipt-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not receipts:
        return {"status": "UNAVAILABLE", "reason": "HUD FHA tract source profile is not available locally."}
    try:
        receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
        source = folder / "fha-insurance-in-force-by-tract.csv"
        profile_path = folder / receipt["profile_file"]
        if receipt.get("status") != "PASS" or sha256(source) != receipt.get("source_sha256"):
            raise ValueError("HUD FHA tract source file does not match its receipt")
        if sha256(profile_path) != receipt.get("profile_sha256"):
            raise ValueError("HUD FHA tract profile does not match its receipt")
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if profile.get("rows") != EXPECTED_ROWS or profile.get("unique_tracts") != EXPECTED_ROWS:
            raise ValueError("HUD FHA tract profile failed its row/key contract")
        return {"status": "AVAILABLE", **profile}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "UNAVAILABLE", "reason": str(error)}
