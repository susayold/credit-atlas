"""Verified public macro context for the private D01 mortgage workspace."""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from .workspace import read_json, sha256


SERIES = {
    "UNRATE": {
        "label": "Unemployment rate",
        "source": "U.S. Bureau of Labor Statistics via FRED",
        "unit": "Percent",
        "frequency": "Monthly, seasonally adjusted",
    },
    "USSTHPI": {
        "label": "U.S. house price index",
        "source": "Federal Housing Finance Agency via FRED",
        "unit": "Index (1980 Q1 = 100)",
        "frequency": "Quarterly, not seasonally adjusted",
    },
    "MORTGAGE30US": {
        "label": "30-year fixed mortgage rate",
        "source": "Freddie Mac via FRED",
        "unit": "Percent",
        "frequency": "Weekly, ending Thursday",
    },
}
_MAX_CSV_BYTES = 2 * 1024 * 1024
_MAX_CONTEXT_ROWS = 240


def _latest_successful_run(root: Path) -> tuple[Path, dict]:
    candidates = []
    for folder in (root / "data/private/public-context").glob("fred-*"):
        receipt_path = folder / "run-complete.json"
        if not receipt_path.is_file():
            continue
        receipt = read_json(receipt_path)
        if receipt.get("status") == "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE":
            candidates.append((str(receipt.get("completed_at", "")), folder, receipt))
    if not candidates:
        raise ValueError("No completed public mortgage macro context run exists")
    _, folder, receipt = max(candidates, key=lambda item: item[0])
    return folder, receipt


def _read_series(folder: Path, metadata: dict) -> dict:
    series_id = metadata.get("series_id")
    if series_id not in SERIES:
        raise ValueError("Macro context contains an unexpected series")
    file = folder / f"{series_id}.csv"
    if not file.is_file() or file.stat().st_size > _MAX_CSV_BYTES:
        raise ValueError("Macro context source CSV is missing or exceeds its bound")
    if sha256(file) != metadata.get("sha256"):
        raise ValueError("Macro context source digest does not match its receipt")
    rows = []
    with file.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["observation_date", series_id]:
            raise ValueError("Macro context source CSV schema changed")
        previous = None
        for row in reader:
            if None in row or row.get("observation_date") is None or row.get(series_id) is None:
                raise ValueError("Macro context source CSV has a malformed row")
            observed = date.fromisoformat(row["observation_date"])
            if previous is not None and observed <= previous:
                raise ValueError("Macro context observations are not strictly ordered")
            previous = observed
            raw = row[series_id]
            value = None if raw in ("", ".") else float(raw)
            if value is not None and (not math.isfinite(value) or value < 0
                                      or series_id != "USSTHPI" and value > 100):
                raise ValueError("Macro context observation is outside its valid numeric domain")
            rows.append((observed.isoformat(), value))
    if (len(rows) != metadata.get("observations") or not rows
            or rows[0][0] != metadata.get("first_reference_date")
            or rows[-1][0] != metadata.get("last_reference_date")):
        raise ValueError("Macro context row count or coverage does not match its receipt")
    latest = next(((period, value) for period, value in reversed(rows) if value is not None), None)
    return {
        **SERIES[series_id],
        "series_id": series_id,
        "source_url": metadata.get("source_url"),
        "metadata_url": metadata.get("metadata_url"),
        "observation_count": len(rows),
        "missing_count": sum(value is None for _, value in rows),
        "first_reference_date": rows[0][0],
        "last_reference_date": rows[-1][0],
        "last_known_reference_date": latest[0] if latest else None,
        "last_known_value": latest[1] if latest else None,
        "retrieved_at": metadata.get("retrieved_at"),
        "latest_revised_snapshot": True,
        "predictor_qualified": metadata.get("model_predictor_qualified") is True,
    }


def report(root: Path) -> dict:
    """Return verified aggregates and case-aligned context; never return source IDs."""
    folder, receipt = _latest_successful_run(root.resolve())
    if (receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False
            or receipt.get("model_training_performed") is not False
            or receipt.get("predictive_asof_qualified") is not False):
        raise ValueError("Mortgage macro context receipt has an invalid visibility or qualification state")

    output_hashes = receipt.get("outputs_sha256")
    if not isinstance(output_hashes, dict) or not output_hashes:
        raise ValueError("Mortgage macro context receipt has no output digests")
    for name, digest in output_hashes.items():
        path = folder / name
        if Path(name).name != name or not path.is_file() or sha256(path) != digest:
            raise ValueError("Mortgage macro context output failed its receipt digest check")

    metadata_rows = receipt.get("series")
    if (not isinstance(metadata_rows, list)
            or {item.get("series_id") for item in metadata_rows if isinstance(item, dict)} != set(SERIES)):
        raise ValueError("Mortgage macro context must contain exactly the three configured series")
    series = [_read_series(folder, item) for item in metadata_rows]
    monthly_path = folder / "monthly-context.json"
    context = read_json(monthly_path)
    monthly = context.get("rows")
    hpi = context.get("quarterly_hpi")
    if (context.get("case_id") != receipt.get("case_id")
            or context.get("pipeline_run") != receipt.get("pipeline_run")
            or not isinstance(monthly, list) or not 1 <= len(monthly) <= _MAX_CONTEXT_ROWS
            or not isinstance(hpi, list)):
        raise ValueError("Mortgage macro context alignment artifact is invalid")
    expected_months = [row.get("reporting_month") for row in monthly]
    if any(not isinstance(month, str) or len(month) != 7 for month in expected_months):
        raise ValueError("Mortgage macro context has an invalid reporting month")
    if expected_months != sorted(set(expected_months)):
        raise ValueError("Mortgage macro context months are duplicated or unordered")

    aligned = []
    for row in monthly:
        aligned.append({
            "period": row["reporting_month"] + "-01",
            "unemployment_percent": row.get("unemployment_percent_latest_revised"),
            "mortgage30_monthly_mean_percent": row.get("mortgage30_percent_monthly_mean"),
            "mortgage30_observation_count": row.get("mortgage30_observations_in_month"),
        })
    quarterly = []
    previous = None
    for row in hpi:
        period = row.get("reference_quarter_start")
        value = row.get("index_1980_q1_100")
        if not isinstance(period, str) or (previous is not None and period <= previous):
            raise ValueError("Mortgage macro HPI quarters are invalid or unordered")
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError("Mortgage macro HPI value is invalid")
        previous = period
        quarterly.append({"period": period, "index_1980_q1_100": value})

    return {
        "status": "AVAILABLE",
        "case_id": receipt["case_id"],
        "pipeline_run": receipt["pipeline_run"],
        "completed_at": receipt["completed_at"],
        "series": series,
        "case_alignment": {
            "monthly_rows": len(aligned),
            "first_month": expected_months[0],
            "last_month": expected_months[-1],
            "unemployment_months_available": sum(row["unemployment_percent"] is not None for row in aligned),
            "mortgage_rate_months_available": sum(row["mortgage30_monthly_mean_percent"] is not None for row in aligned),
            "hpi_quarters": len(quarterly),
        },
        "monthly_history": aligned,
        "quarterly_hpi": quarterly,
        "limitations": [
            "Latest revised FRED snapshots do not establish historical publication availability.",
            "Retrospective descriptive context only; no macro series is qualified as a model predictor.",
            "Quarterly HPI remains quarterly; no monthly interpolation is used.",
            "Macro series do not add mortgage loan-performance vintages or borrower-level labels.",
        ],
    }
