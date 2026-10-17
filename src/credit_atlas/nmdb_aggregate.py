"""Read the acquired public FHFA NMDB aggregate mortgage-performance series."""
from __future__ import annotations

import json
from pathlib import Path

from .workspace import sha256

SOURCE_URL = "https://www.fhfa.gov/document/d/nmdb/nmdb-mortgage-performance-statistics-all-quarterly.zip"
SERIES = {
    "P3089DL": {
        "label": "30–89 days delinquent",
        "definition": "Share of active mortgages 30–89 days past due at quarter end.",
    },
    "P90DL": {
        "label": "90+ days delinquent",
        "definition": "Share of active mortgages 90 or more days past due at quarter end.",
    },
    "PFORECL": {
        "label": "Foreclosure / bankruptcy / deed-in-lieu",
        "definition": "Share in process of foreclosure, bankruptcy, or deed-in-lieu at quarter end.",
    },
    "PFORB": {
        "label": "Forbearance",
        "definition": "Separate reported forbearance share; available beginning 2019 Q4.",
    },
}


def read(root: Path) -> dict:
    def retrieved_at(path: Path) -> str:
        try:
            receipt = json.loads((path / "receipt.json").read_text(encoding="utf-8"))
            return receipt.get("retrieved_at", "") if receipt.get("status") == "PASS" else ""
        except (OSError, ValueError):
            return ""

    folders = sorted(
        (root / "data" / "private" / "public-context").glob("fhfa-nmdb-performance-*"),
        key=retrieved_at,
        reverse=True,
    )
    for folder in folders:
        receipt_path = folder / "receipt.json"
        profile_path = folder / "profile.json"
        archive_path = folder / "official-performance-quarterly.zip"
        if not (receipt_path.is_file() and profile_path.is_file() and archive_path.is_file()):
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "PASS" or receipt.get("download", {}).get("requested_url") != SOURCE_URL:
            continue
        if sha256(archive_path) != receipt["download"].get("sha256"):
            raise ValueError("FHFA NMDB source archive hash differs from its acquisition receipt")
        if sha256(profile_path) != receipt.get("profile_sha256"):
            raise ValueError("FHFA NMDB profile hash differs from its acquisition receipt")
        series = profile.get("national_all_mortgages_series")
        if not isinstance(series, list) or len(series) != profile.get("distinct_periods"):
            raise ValueError("FHFA NMDB national series coverage is incomplete")
        return {
            "status": "AVAILABLE",
            "dataset": "FHFA NMDB aggregate mortgage-performance statistics",
            "source_page": receipt["source_page"],
            "source_url": SOURCE_URL,
            "source_release_date": receipt["source_release_date"],
            "retrieved_at": receipt["retrieved_at"],
            "geography": "National · United States",
            "market": "All Mortgages",
            "periods": len(series),
            "first_period": profile["first_period_in_file"],
            "last_period": profile["last_period_in_file"],
            "rows": series,
            "series": SERIES,
            "quality": {
                "coverage_observations": profile["rows"],
                "coverage_label": "Aggregate source rows",
                "suppression_label": "Suppressed rows · all geographies",
                "all_geography_rows": profile["rows"],
                "unique_aggregate_keys": profile["unique_aggregate_keys"],
                "suppressed_rows": profile["suppression_row_counts"].get("1", 0),
                "blank_or_dot_value_counts": profile["blank_or_dot_value_counts"],
                "archive_sha256": receipt["download"]["sha256"],
                "selected_csv_sha256": profile["csv_sha256"],
            },
            "scope_notes": [
                "Aggregate context only; not a loan-level panel, not a Freddie vintage, and not a model predictor.",
                "National all-mortgages aggregates do not share the Freddie study sample or denominator.",
                "Performance is reported at quarter end; categories and censoring do not match the monthly Freddie target.",
                "FHFA statistics are a latest revised snapshot, not historical release vintages.",
            ],
        }

    national_data = root / "docs" / "data" / "nmdb-performance-national-quarterly-2026q2.csv"
    national_receipt = root / "docs" / "data" / "nmdb-performance-national-quarterly-2026q2-receipt.json"
    if national_data.is_file() and national_receipt.is_file():
        from .nmdb_performance import nmdb_performance_report

        report = nmdb_performance_report(root)
        national_rows = [
            row for row in report["observations"]
            if row["market"] == "All Mortgages"
        ]
        by_period = {period: {} for period in report["periods"]}
        suppressed_rows = 0
        blank_counts = {code: 0 for code in SERIES}
        for row in national_rows:
            code = row["series_id"]
            by_period[row["period"]][code] = row["value_pct"]
            suppressed_rows += int(row["suppressed"])
            blank_counts[code] += int(row["value_pct"] is None)
        if len(national_rows) != len(report["periods"]) * len(SERIES):
            raise ValueError("FHFA NMDB national slice coverage is incomplete")
        series = [
            {"period": period, **by_period[period]}
            for period in report["periods"]
        ]
        return {
            "status": "AVAILABLE",
            "dataset": report["source"]["title"],
            "source_page": report["source"]["index_url"],
            "source_url": report["source"]["download_url"],
            "source_release_date": report["source"]["release_date"],
            "retrieved_at": json.loads(national_receipt.read_text(encoding="utf-8")).get("acquired_at_utc", ""),
            "geography": report["geography"],
            "market": "All Mortgages",
            "source_package_scope": "National / Census Areas package · National rows only",
            "periods": len(series),
            "first_period": report["periods"][0],
            "last_period": report["periods"][-1],
            "rows": series,
            "series": SERIES,
            "quality": {
                "coverage_observations": len(national_rows),
                "coverage_label": "National All Mortgages series observations",
                "suppression_label": "Suppressed observations · national slice",
                "all_geography_rows": None,
                "unique_aggregate_keys": None,
                "suppressed_rows": suppressed_rows,
                "blank_or_dot_value_counts": blank_counts,
                "archive_sha256": report["source"]["source_archive_sha256"],
                "selected_csv_sha256": report["source"]["curated_file_sha256"],
            },
            "scope_notes": [
                "This public fallback uses only the National rows from FHFA's National / Census Areas package; it does not expose or count the all-geography archive.",
                "Aggregate context only; not a loan-level panel, not a Freddie vintage, and not a model predictor.",
                "National all-mortgages aggregates do not share the Freddie study sample or denominator.",
                "Performance is reported at quarter end; categories and censoring do not match the monthly Freddie target.",
                "Blank and suppressed values remain unavailable; they are not zero-filled or imputed.",
                "FHFA statistics are a latest revised snapshot, not historical release vintages.",
            ],
        }
    return {
        "status": "UNAVAILABLE",
        "reason": "Public FHFA NMDB aggregate performance package has not been acquired in this workspace.",
        "source_page": "https://www.fhfa.gov/data/nmdb",
        "rows": [],
        "series": SERIES,
    }
