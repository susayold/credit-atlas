"""Verified public macro context for the private D01 mortgage workspace."""

from __future__ import annotations

import csv
import calendar
import math
import re
import zipfile
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
_MAX_ALFRED_ZIP_BYTES = 50 * 1024 * 1024
_MAX_ALFRED_CSV_BYTES = 40 * 1024 * 1024
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


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


def _latest_alfred_run(root: Path) -> tuple[Path, dict] | None:
    candidates = []
    for folder in (root / "data/private/public-context").glob("alfred-asof-*"):
        manifest_path = folder / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = read_json(manifest_path)
        if manifest.get("status") == "DOWNLOADED_AND_VALIDATED":
            candidates.append((str(manifest.get("completed_at", "")), folder, manifest))
    if not candidates:
        return None
    _, folder, manifest = max(candidates, key=lambda item: item[0])
    return folder, manifest


def _read_alfred_snapshots(folder: Path, manifest: dict, series_id: str) -> dict:
    """Read one verified value map per official ALFRED vintage, fail closed."""
    if manifest.get("visibility") != "private" or manifest.get("predictor_qualified") is not False:
        raise ValueError("ALFRED context has an invalid visibility or qualification state")
    series = manifest.get("series", {}).get(series_id)
    if not isinstance(series, dict):
        raise ValueError("ALFRED context is missing a configured series")
    expected_vintages = set(series.get("selected_vintages", []))
    if not expected_vintages or not isinstance(series.get("batches"), list):
        raise ValueError("ALFRED context has no selected vintage batches")
    snapshots = {}
    for batch in series["batches"]:
        name = batch.get("file")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".zip"):
            raise ValueError("ALFRED archive path is invalid")
        archive_path = folder / name
        if (not archive_path.is_file() or archive_path.stat().st_size > _MAX_ALFRED_ZIP_BYTES
                or sha256(archive_path) != batch.get("sha256")):
            raise ValueError("ALFRED archive is missing or failed its receipt digest")
        with zipfile.ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("ALFRED archive failed CRC validation")
            members = [member for member in archive.infolist() if member.filename.lower().endswith(".csv")]
            if (len(members) != 1 or members[0].file_size > _MAX_ALFRED_CSV_BYTES
                    or Path(members[0].filename).name != members[0].filename):
                raise ValueError("ALFRED archive has an unexpected CSV member")
            with archive.open(members[0]) as stream:
                text = stream.read(_MAX_ALFRED_CSV_BYTES + 1).decode("utf-8-sig")
        if len(text.encode("utf-8")) > _MAX_ALFRED_CSV_BYTES:
            raise ValueError("ALFRED CSV exceeds its configured bound")
        reader = csv.DictReader(text.splitlines())
        vintage_dates = batch.get("vintages")
        if not isinstance(vintage_dates, list) or not vintage_dates:
            raise ValueError("ALFRED batch has no vintage list")
        columns = [f"{series_id}_{date.fromisoformat(value).strftime('%Y%m%d')}" for value in vintage_dates]
        if reader.fieldnames != ["observation_date", *columns]:
            raise ValueError("ALFRED vintage CSV schema does not match its manifest")
        matrices = {value: {} for value in vintage_dates}
        previous = None
        row_count = 0
        for row in reader:
            if None in row or row.get("observation_date") is None:
                raise ValueError("ALFRED vintage CSV contains a malformed row")
            period = date.fromisoformat(row["observation_date"])
            if previous is not None and period <= previous:
                raise ValueError("ALFRED observation dates are not strictly ordered")
            previous = period
            for vintage, column in zip(vintage_dates, columns):
                raw = row.get(column)
                if raw is None:
                    raise ValueError("ALFRED vintage CSV has a missing value column")
                value = None if raw in ("", ".") else float(raw)
                if value is not None and (not math.isfinite(value) or value < 0
                                          or series_id != "USSTHPI" and value > 100):
                    raise ValueError("ALFRED observation is outside its valid numeric domain")
                matrices[vintage][period] = value
            row_count += 1
        if row_count != batch.get("observation_rows") or len(vintage_dates) != batch.get("vintage_columns"):
            raise ValueError("ALFRED vintage CSV row or column count differs from its receipt")
        snapshots.update(matrices)
    if set(snapshots) != expected_vintages:
        raise ValueError("ALFRED context vintage set differs from its manifest")
    return snapshots


def _read_point_in_time_context(root: Path, expected_months: list[str]) -> dict | None:
    found = _latest_alfred_run(root)
    if found is None:
        return None
    folder, manifest = found
    if (manifest.get("status") != "DOWNLOADED_AND_VALIDATED"
            or manifest.get("case_months") != expected_months
            or manifest.get("model_training_performed") is not False):
        raise ValueError("ALFRED case calendar or training status is invalid")
    if any(not isinstance(month, str) or not _MONTH_RE.fullmatch(month) for month in expected_months):
        raise ValueError("D01 reporting month is not valid YYYY-MM")
    monthly_map = {}
    values = {series_id: _read_alfred_snapshots(folder, manifest, series_id) for series_id in SERIES}
    for series_id in SERIES:
        mapping = manifest["series"][series_id].get("monthly_vintage_map")
        if not isinstance(mapping, dict) or set(mapping) != set(expected_months):
            raise ValueError("ALFRED monthly vintage map does not match the D01 calendar")
        for month, vintage in mapping.items():
            year, month_number = (int(part) for part in month.split("-"))
            cutoff = date(year, month_number, calendar.monthrange(year, month_number)[1])
            vintage_date = date.fromisoformat(vintage)
            if vintage_date > cutoff or vintage not in values[series_id]:
                raise ValueError("ALFRED vintage was not available at the D01 as-of date")
        monthly_map[series_id] = mapping

    output = []
    for month in expected_months:
        year, month_number = (int(part) for part in month.split("-"))
        cutoff = date(year, month_number, calendar.monthrange(year, month_number)[1])
        selected = {series_id: monthly_map[series_id][month] for series_id in SERIES}
        asof: dict[str, dict] = {}
        for series_id in SERIES:
            snapshot = values[series_id][selected[series_id]]
            eligible = [(period, value) for period, value in snapshot.items()
                        if period <= cutoff and value is not None]
            if series_id == "MORTGAGE30US":
                in_month = [(period, value) for period, value in eligible
                            if period.year == year and period.month == month_number]
                asof[series_id] = {
                    "monthly_mean_percent": round(sum(value for _, value in in_month) / len(in_month), 6)
                    if in_month else None,
                    "observation_count": len(in_month),
                    "last_observation_date": max((period for period, _ in in_month), default=None).isoformat()
                    if in_month else None,
                }
            else:
                latest = max(eligible, key=lambda item: item[0]) if eligible else (None, None)
                asof[series_id] = {"reference_date": latest[0].isoformat() if latest[0] else None,
                                   "value": latest[1]}
        output.append({
            "period": month + "-01",
            "as_of_date": cutoff.isoformat(),
            "vintage_dates": selected,
            "unemployment_reference_date": asof["UNRATE"]["reference_date"],
            "unemployment_percent": asof["UNRATE"]["value"],
            "mortgage30_monthly_mean_percent": asof["MORTGAGE30US"]["monthly_mean_percent"],
            "mortgage30_observation_count": asof["MORTGAGE30US"]["observation_count"],
            "mortgage30_last_observation_date": asof["MORTGAGE30US"]["last_observation_date"],
            "hpi_reference_date": asof["USSTHPI"]["reference_date"],
            "hpi_index_1980_q1_100": asof["USSTHPI"]["value"],
        })
    coverage = {
        "monthly_rows": len(output),
        "first_month": expected_months[0],
        "last_month": expected_months[-1],
        "unemployment_months_available": sum(row["unemployment_percent"] is not None for row in output),
        "mortgage_rate_months_available": sum(row["mortgage30_monthly_mean_percent"] is not None for row in output),
        "hpi_months_available": sum(row["hpi_index_1980_q1_100"] is not None for row in output),
    }
    return {
        "status": "AVAILABLE",
        "source": manifest["source"],
        "source_help_url": manifest["source_help_url"],
        "acquired_at": manifest.get("completed_at"),
        "cutoff_rule": manifest["cutoff_rule"],
        "coverage": coverage,
        "monthly_history": output,
        "limitations": [
            "Each month uses the latest actual ALFRED vintage on or before that month-end; publication dates are source-specific.",
            "This is point-in-time macro context, not a qualified PD predictor; underwriting or event-time cutoffs may be earlier than reporting-month end.",
            "House-price index remains quarterly and uses the latest quarter actually published by each month-end; no monthly interpolation is used.",
            "No mortgage borrower records, loan-performance vintages, or default labels are added by this macro dataset.",
        ],
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

    point_in_time = _read_point_in_time_context(root.resolve(), expected_months)

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
        "point_in_time_context": point_in_time,
        "limitations": [
            "Latest revised FRED snapshots do not establish historical publication availability.",
            "Retrospective descriptive context only; no macro series is qualified as a model predictor.",
            "Quarterly HPI remains quarterly; no monthly interpolation is used.",
            "Macro series do not add mortgage loan-performance vintages or borrower-level labels.",
        ],
    }
