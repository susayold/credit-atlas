"""Acquire official Federal Reserve bank asset-quality series by product.

The raw FRED CSV snapshots and receipt stay in the private D: workspace. This
source is a bank-portfolio benchmark, not Freddie/NSMO loan-level evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SERIES = {
    "DRSFRMACBS": {
        "product": "Single-family mortgage",
        "title": "Delinquency rate on single-family residential mortgages, booked in domestic offices, all commercial banks",
        "unit": "Percent",
        "frequency": "Quarterly, end of period",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "End-of-period loans",
    },
    "CORSFRMACBS": {
        "product": "Single-family mortgage",
        "title": "Charge-off rate on single-family residential mortgages, booked in domestic offices, all commercial banks",
        "unit": "Percent",
        "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "Average loans; annualized net charge-offs after recoveries",
    },
    "DRCCLACBS": {
        "product": "Credit card",
        "title": "Delinquency rate on credit card loans, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly, end of period",
        "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans",
    },
    "CORCCACBS": {
        "product": "Credit card",
        "title": "Charge-off rate on credit card loans, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "Average loans; annualized net charge-offs after recoveries",
    },
    "DROCLACBS": {
        "product": "Other consumer",
        "title": "Delinquency rate on other consumer loans, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly, end of period",
        "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans",
    },
    "COROCLACBS": {
        "product": "Other consumer",
        "title": "Charge-off rate on other consumer loans, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "Average loans; annualized net charge-offs after recoveries",
    },
    "DRCRELEXFACBS": {
        "product": "Commercial real estate",
        "title": "Delinquency rate on commercial real estate loans excluding farmland, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly, end of period",
        "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans",
    },
    "CORCREXFACBS": {
        "product": "Commercial real estate",
        "title": "Charge-off rate on commercial real estate loans excluding farmland, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "Average loans; annualized net charge-offs after recoveries",
    },
    "DRBLACBS": {
        "product": "Business loans",
        "title": "Delinquency rate on business loans, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly, end of period",
        "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans",
    },
    "CORBLACBS": {
        "product": "Business loans",
        "title": "Charge-off rate on business loans, all commercial banks",
        "unit": "Percent", "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "Average loans; annualized net charge-offs after recoveries",
    },
    "DRCCLT100S": {
        "product": "Credit card · Top 100 banks",
        "title": "Delinquency rate on credit card loans, banks ranked 1st to 100th by consolidated assets",
        "unit": "Percent", "frequency": "Quarterly, end of period",
        "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans",
    },
    "CORCCT100S": {
        "product": "Credit card · Top 100 banks",
        "title": "Charge-off rate on credit card loans, banks ranked 1st to 100th by consolidated assets",
        "unit": "Percent", "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "Average loans; annualized net charge-offs after recoveries",
    },
    "DRCCLOBS": {
        "product": "Credit card · Other banks",
        "title": "Delinquency rate on credit card loans, banks not among the 100 largest by assets",
        "unit": "Percent", "frequency": "Quarterly, end of period",
        "seasonal_adjustment": "Seasonally adjusted", "denominator": "End-of-period loans",
    },
    "CORCCOBS": {
        "product": "Credit card · Other banks",
        "title": "Charge-off rate on credit card loans, banks not among the 100 largest by assets",
        "unit": "Percent", "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally adjusted",
        "denominator": "Average loans; annualized net charge-offs after recoveries",
    },
}
FRED_DATA_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
FED_RELEASE_URL = "https://www.federalreserve.gov/releases/ChargeOff/"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_csv(series_id: str, raw: bytes) -> dict:
    text = raw.decode("utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    if not rows or list(rows[0]) != ["observation_date", series_id]:
        raise ValueError(f"Unexpected official FRED CSV schema for {series_id}")
    previous = ""
    for row in rows:
        period, raw_value = row.get("observation_date"), row.get(series_id)
        if not period or period <= previous or not raw_value or raw_value == ".":
            raise ValueError(f"Missing, duplicate, unordered, or nonnumeric {series_id} row")
        year, month, day = (int(part) for part in period.split("-"))
        if month not in (1, 4, 7, 10) or day != 1 or year < 1980:
            raise ValueError(f"Unexpected quarterly period in {series_id}: {period}")
        value = float(raw_value)
        lower_bound = -100 if series_id.startswith("COR") else 0
        if not math.isfinite(value) or not lower_bound <= value <= 100:
            raise ValueError(f"Out-of-domain rate in {series_id}: {raw_value}")
        previous = period
    first, last = rows[0]["observation_date"], rows[-1]["observation_date"]
    expected = ((int(last[:4]) - int(first[:4])) * 4
                + ((int(last[5:7]) - 1) // 3) - ((int(first[5:7]) - 1) // 3) + 1)
    if len(rows) != expected:
        raise ValueError(f"Quarterly coverage gap in {series_id}: {len(rows)} rows, expected {expected}")
    return {"observations": len(rows), "first_reference_date": first,
            "last_reference_date": last, "latest_value": float(rows[-1][series_id])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    args = parser.parse_args()
    root = args.root.resolve()
    parent = root / "data/private/public-context"
    run_id = "fed-bank-mortgage-asset-quality-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = parent / run_id
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "IN_PROGRESS", "run_id": run_id,
        "source": "Board of Governors of the Federal Reserve System via FRED",
        "release": "Charge-Off and Delinquency Rates on Loans and Leases at Commercial Banks",
        "release_url": FED_RELEASE_URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "visibility": "private", "predictor_qualified": False,
        "model_training_performed": False,
        "scope_note": "Aggregate bank-portfolio benchmark; separate from Freddie Mac and NSMO loan-level populations.",
        "series": {},
    }
    manifest_path = folder / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for series_id, definition in SERIES.items():
        try:
            request = urllib.request.Request(
                FRED_DATA_URL.format(series_id=series_id),
                headers={"User-Agent": "CreditAtlas-research/1.0 (public-data acquisition)"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
                if response.status != 200 or len(raw) > 2 * 1024 * 1024:
                    raise RuntimeError(f"FRED download failed or exceeded limit for {series_id}")
            profile = validate_csv(series_id, raw)
            target = folder / f"{series_id}.csv"
            target.write_bytes(raw)
            manifest["series"][series_id] = {
                **definition,
                **profile,
                "source_url": FRED_DATA_URL.format(series_id=series_id),
                "metadata_url": f"https://fred.stlouisfed.org/series/{series_id}",
                "bytes": len(raw),
                "sha256": sha256(raw),
            }
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            manifest["status"] = "FAILED"
            manifest["failure"] = {"series_id": series_id, "error": f"{type(exc).__name__}: {str(exc)[:250]}"}
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            raise
    periods = {item["last_reference_date"] for item in manifest["series"].values()}
    if len(periods) != 1:
        raise ValueError("Federal Reserve mortgage series do not share a latest quarter")
    manifest["latest_common_reference_date"] = periods.pop()
    manifest["status"] = "DOWNLOADED_AND_VALIDATED"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "directory": str(folder),
                      "latest_common_reference_date": manifest["latest_common_reference_date"],
                      "series": manifest["series"]}, indent=2))


if __name__ == "__main__":
    main()
