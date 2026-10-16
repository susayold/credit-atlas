"""Verified Federal Reserve commercial-bank asset-quality context by product."""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from .workspace import read_json, sha256


SERIES = {
    "DRSFRMACBS": {"product": "Single-family mortgage", "label": "Delinquency rate", "unit": "Percent", "frequency": "Quarterly, end of period", "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans", "interpretation": "30+ days past due and still accruing, plus loans in nonaccrual status", "allow_negative": False},
    "CORSFRMACBS": {"product": "Single-family mortgage", "label": "Net charge-off rate", "unit": "Percent", "frequency": "Quarterly", "seasonal_adjustment": "Seasonally adjusted", "denominator": "Average loans; annualized net charge-offs after recoveries", "interpretation": "A negative value can occur when recoveries exceed charge-offs in the quarter", "allow_negative": True},
    "DRCCLACBS": {"product": "Credit card", "label": "Delinquency rate", "unit": "Percent", "frequency": "Quarterly, end of period", "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans", "interpretation": "30+ days past due and still accruing, plus loans in nonaccrual status", "allow_negative": False},
    "CORCCACBS": {"product": "Credit card", "label": "Net charge-off rate", "unit": "Percent", "frequency": "Quarterly", "seasonal_adjustment": "Seasonally adjusted", "denominator": "Average loans; annualized net charge-offs after recoveries", "interpretation": "A negative value can occur when recoveries exceed charge-offs in the quarter", "allow_negative": True},
    "DROCLACBS": {"product": "Other consumer", "label": "Delinquency rate", "unit": "Percent", "frequency": "Quarterly, end of period", "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans", "interpretation": "30+ days past due and still accruing, plus loans in nonaccrual status", "allow_negative": False},
    "COROCLACBS": {"product": "Other consumer", "label": "Net charge-off rate", "unit": "Percent", "frequency": "Quarterly", "seasonal_adjustment": "Seasonally adjusted", "denominator": "Average loans; annualized net charge-offs after recoveries", "interpretation": "A negative value can occur when recoveries exceed charge-offs in the quarter", "allow_negative": True},
    "DRCRELEXFACBS": {"product": "Commercial real estate", "label": "Delinquency rate", "unit": "Percent", "frequency": "Quarterly, end of period", "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans", "interpretation": "30+ days past due and still accruing, plus loans in nonaccrual status; excludes farmland", "allow_negative": False},
    "CORCREXFACBS": {"product": "Commercial real estate", "label": "Net charge-off rate", "unit": "Percent", "frequency": "Quarterly", "seasonal_adjustment": "Seasonally adjusted", "denominator": "Average loans; annualized net charge-offs after recoveries", "interpretation": "A negative value can occur when recoveries exceed charge-offs in the quarter; excludes farmland", "allow_negative": True},
    "DRBLACBS": {"product": "Business loans", "label": "Delinquency rate", "unit": "Percent", "frequency": "Quarterly, end of period", "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans", "interpretation": "30+ days past due and still accruing, plus loans in nonaccrual status", "allow_negative": False},
    "CORBLACBS": {"product": "Business loans", "label": "Net charge-off rate", "unit": "Percent", "frequency": "Quarterly", "seasonal_adjustment": "Seasonally adjusted", "denominator": "Average loans; annualized net charge-offs after recoveries", "interpretation": "A negative value can occur when recoveries exceed charge-offs in the quarter", "allow_negative": True},
}
RELEASE = "Charge-Off and Delinquency Rates on Loans and Leases at Commercial Banks"
RELEASE_URL = "https://www.federalreserve.gov/releases/ChargeOff/"
_MAX_CSV_BYTES = 2 * 1024 * 1024


def _latest_run(root: Path) -> tuple[Path, dict]:
    candidates = []
    for folder in (root / "data/private/public-context").glob("fed-bank-mortgage-asset-quality-*"):
        manifest_path = folder / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = read_json(manifest_path)
        if manifest.get("status") == "DOWNLOADED_AND_VALIDATED":
            candidates.append((str(manifest.get("completed_at", "")), folder, manifest))
    if not candidates:
        raise ValueError("No completed Federal Reserve bank asset-quality context run exists")
    _, folder, manifest = max(candidates, key=lambda item: item[0])
    return folder, manifest


def _quarter_index(value: str) -> int:
    observed = date.fromisoformat(value)
    if observed.day != 1 or observed.month not in (1, 4, 7, 10):
        raise ValueError("Federal Reserve context contains a non-quarterly date")
    return observed.year * 4 + ((observed.month - 1) // 3)


def report(root: Path) -> dict:
    folder, manifest = _latest_run(root.resolve())
    if (manifest.get("visibility") != "private"
            or manifest.get("predictor_qualified") is not False
            or manifest.get("model_training_performed") is not False
            or manifest.get("release") != RELEASE):
        raise ValueError("Federal Reserve context has an invalid source or qualification state")
    metadata = manifest.get("series")
    if not isinstance(metadata, dict) or set(metadata) != set(SERIES):
        raise ValueError("Federal Reserve context must contain exactly the configured product series")

    values_by_period: dict[str, dict[str, float]] = {}
    profiles = []
    for series_id, definition in SERIES.items():
        info = metadata[series_id]
        filename = f"{series_id}.csv"
        path = folder / filename
        if (not path.is_file() or path.stat().st_size > _MAX_CSV_BYTES
                or sha256(path) != info.get("sha256")
                or info.get("source_url") != f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"):
            raise ValueError(f"Federal Reserve source digest or URL failed for {series_id}")
        rows = []
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["observation_date", series_id]:
                raise ValueError(f"Federal Reserve CSV schema changed for {series_id}")
            previous_index = None
            for row in reader:
                if None in row or not row.get("observation_date") or row.get(series_id) in (None, "", "."):
                    raise ValueError(f"Federal Reserve CSV has an invalid row for {series_id}")
                period = date.fromisoformat(row["observation_date"]).isoformat()
                index = _quarter_index(period)
                if previous_index is not None and index != previous_index + 1:
                    raise ValueError(f"Federal Reserve CSV has a gap or duplicate for {series_id}")
                value = float(row[series_id])
                if (not math.isfinite(value) or value > 100
                        or not definition["allow_negative"] and value < 0
                        or definition["allow_negative"] and value < -100):
                    raise ValueError(f"Federal Reserve value is outside domain for {series_id}")
                rows.append((period, value))
                previous_index = index
        if (not rows or len(rows) != info.get("observations")
                or rows[0][0] != info.get("first_reference_date")
                or rows[-1][0] != info.get("last_reference_date")):
            raise ValueError(f"Federal Reserve coverage differs from manifest for {series_id}")
        for period, value in rows:
            values_by_period.setdefault(period, {})[series_id] = value
        profiles.append({
            **{key: value for key, value in definition.items() if key != "allow_negative"},
            "series_id": series_id,
            "source": manifest["source"],
            "source_url": info["source_url"],
            "metadata_url": info["metadata_url"],
            "observation_count": len(rows),
            "first_reference_date": rows[0][0],
            "last_reference_date": rows[-1][0],
            "last_known_value": rows[-1][1],
            "historical_high_value": max(value for _, value in rows),
            "historical_high_date": next(period for period, value in rows
                                         if value == max(item[1] for item in rows)),
            "historical_percentile": round(100 * sum(value <= rows[-1][1] for _, value in rows) / len(rows), 1),
        })

    latest_common = min(profile["last_reference_date"] for profile in profiles)
    if manifest.get("latest_common_reference_date") != latest_common:
        raise ValueError("Federal Reserve latest-common-quarter manifest does not reconcile")
    rows = [{"period": period, **values}
            for period, values in sorted(values_by_period.items())]
    return {
        "status": "AVAILABLE", "source": manifest["source"],
        "release": manifest["release"], "release_url": manifest["release_url"],
        "retrieved_at": manifest["retrieved_at"], "completed_at": manifest["completed_at"],
        "first_period": rows[0]["period"], "last_period": latest_common,
        "quarter_count": len(rows), "products": sorted({item["product"] for item in profiles}),
        "series": profiles, "rows": rows,
        "limitations": [
            "These are aggregate rates for U.S. commercial banks, not borrower-level records or a complete census of all lenders.",
            "Delinquency is 30+ days past due and still accruing or nonaccrual, divided by end-of-period loans; charge-off is annualized net of recoveries divided by average loans.",
            "Not all product series begin on the same date; blank cells in earlier quarters mean the series was not yet published, not zero risk.",
            "Commercial real estate measures exclude farmland; these product groups remain bank portfolios rather than homogeneous borrowers or loans.",
            "This is a latest-revised snapshot, not a point-in-time publication-vintage series or a qualified model predictor.",
        ],
    }
