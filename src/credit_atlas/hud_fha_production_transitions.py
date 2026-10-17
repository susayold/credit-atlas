"""Curated monthly FHA serious-delinquency transitions from HUD Table 2."""

from __future__ import annotations

import csv
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPORT_URL = "https://www.hud.gov/sites/default/files/Housing/documents/FHAProd_AUG2026.pdf"
INDEX_URL = "https://www.hud.gov/hud-partners/fha-production-report"
DATA_FILE = "hud-fha-production-transitions-2026-08.csv"
REQUIRED_FIELDS = {
    "period", "performance_year", "month",
    "beginning_serious_delinquency_inventory", "serious_delinquency_entries",
    "cures_leaving_serious_delinquency", "claims",
    "prepayments_from_serious_delinquency_inventory",
    "ending_serious_delinquency_inventory", "late_posting_adjustment",
    "cure_ratio_pct", "source_table", "source_page",
}
EXPECTED_PERIODS = [
    f"2025-{month:02d}" for month in range(8, 13)
] + [f"2026-{month:02d}" for month in range(1, 9)]
COUNT_FIELDS = (
    "performance_year", "beginning_serious_delinquency_inventory",
    "serious_delinquency_entries", "cures_leaving_serious_delinquency",
    "claims", "prepayments_from_serious_delinquency_inventory",
    "ending_serious_delinquency_inventory", "late_posting_adjustment",
    "source_table", "source_page",
)


def hud_fha_production_transitions(root: Path) -> dict:
    """Load official aggregate transition counts and enforce source identities."""
    path = root / "docs" / "data" / DATA_FILE
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED_FIELDS.issubset(reader.fieldnames):
            raise ValueError(f"Unexpected HUD FHA production schema: {path.name}")
        raw_rows = list(reader)
    if [row["period"] for row in raw_rows] != EXPECTED_PERIODS:
        raise ValueError("HUD FHA production coverage must be Aug 2025 through Aug 2026")

    rows: list[dict] = []
    for raw in raw_rows:
        row = dict(raw)
        for field in COUNT_FIELDS:
            if not re.fullmatch(r"-?\d+", raw[field] or ""):
                raise ValueError(f"HUD FHA production count is not an integer: {field}")
            row[field] = int(raw[field])
        if any(row[field] < 0 for field in COUNT_FIELDS if field != "late_posting_adjustment"):
            raise ValueError("HUD FHA production counts cannot be negative")
        try:
            row["cure_ratio_pct"] = float(raw["cure_ratio_pct"])
        except (TypeError, ValueError) as exc:
            raise ValueError("HUD FHA published cure ratio must be numeric") from exc
        if not 0 <= row["cure_ratio_pct"] <= 200:
            raise ValueError("HUD FHA published cure ratio is outside a plausible display range")
        if (row["source_table"], row["source_page"]) != (2, 3):
            raise ValueError("HUD FHA production rows must cite Table 2, report page 3")

        flow_total = (
            row["beginning_serious_delinquency_inventory"]
            + row["serious_delinquency_entries"]
            - row["cures_leaving_serious_delinquency"]
            - row["claims"]
            - row["prepayments_from_serious_delinquency_inventory"]
        )
        row["flow_identity_difference"] = row["ending_serious_delinquency_inventory"] - flow_total
        if row["flow_identity_difference"] != 0:
            raise ValueError(f"HUD FHA production flow does not reconcile in {row['period']}")
        recomputed = (Decimal(row["cures_leaving_serious_delinquency"])
                      / Decimal(row["serious_delinquency_entries"])
                      * Decimal(100)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        row["recomputed_cure_ratio_pct"] = float(recomputed)
        if recomputed != Decimal(str(row["cure_ratio_pct"])):
            raise ValueError(f"HUD FHA cure ratio does not match source counts in {row['period']}")
        rows.append(row)

    for prior, current in zip(rows, rows[1:]):
        expected_beginning = prior["ending_serious_delinquency_inventory"] + current["late_posting_adjustment"]
        current["prior_ending_plus_adjustment_difference"] = (
            current["beginning_serious_delinquency_inventory"] - expected_beginning
        )
        if current["prior_ending_plus_adjustment_difference"] != 0:
            raise ValueError(f"HUD FHA beginning inventory does not reconcile in {current['period']}")
    rows[0]["prior_ending_plus_adjustment_difference"] = None

    latest = rows[-1]
    return {
        "schema_version": "hud-fha-production-transitions-v1",
        "status": "AVAILABLE",
        "source": {
            "title": "FHA Single Family Production Report — August 2026",
            "publisher": "U.S. Department of Housing and Urban Development / FHA",
            "report_month": "2026-08",
            "index_url": INDEX_URL,
            "report_url": REPORT_URL,
            "source_table": 2,
            "source_page": 3,
            "extraction": "Thirteen monthly rows transcribed from the official HUD report table. Direct PDF binary retrieval returned HTTP 403; the binary is not stored locally and no raw-PDF hash is claimed.",
            "raw_pdf_sha256": None,
        },
        "monthly": rows,
        "latest": latest,
        "definitions": {
            "serious_delinquency_inventory": "HUD Table 2 inventory includes loans 90+ days delinquent, in foreclosure, and in bankruptcy; excludes HECM.",
            "cures_leaving_serious_delinquency": "Loans leaving serious delinquency and becoming fewer than 90 days delinquent through full or partial cure, with or without loss mitigation or lender assistance.",
            "late_posting_adjustment": "HUD adjustment for late posting of previous-period activity; the next beginning inventory equals the prior ending inventory plus this adjustment.",
            "cure_ratio_pct": "HUD's same-month cured count divided by serious-delinquency entries. It is not a matched-cohort cure probability and can exceed 100%.",
            "flow_identity": "Ending inventory = beginning inventory + entries - cures - claims - prepayments from serious delinquency inventory.",
        },
        "limitations": [
            "This is an aggregate FHA program series, not loan-level performance data or a borrower outcome label.",
            "HUD states the serious-delinquency inventory may not fully reconcile with the separate FHA Loan Performance Trends report because timing and data sources differ.",
            "The cure ratio compares monthly aggregate counts rather than following a matched entry cohort; values above 100% are possible and are not probabilities.",
            "Only the 13 monthly rows published in the August 2026 report are included; no values are forecast or imputed.",
            "The August 2026 PDF binary returned HTTP 403 when directly retrieved; the project records no local raw PDF or SHA-256.",
        ],
    }
