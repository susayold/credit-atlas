"""Acquire ALFRED as-of snapshots for the private D01 mortgage macro context.

Downloads only official ALFRED CSV exports. All raw data and receipts remain under
the private workspace's data/private directory; this script is safe to publish.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import math
import re
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


SERIES = {
    "UNRATE": "https://alfred.stlouisfed.org/series/downloaddata?seid=UNRATE",
    "USSTHPI": "https://alfred.stlouisfed.org/series/downloaddata?seid=USSTHPI",
    "MORTGAGE30US": "https://alfred.stlouisfed.org/series/downloaddata?seid=MORTGAGE30US",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def month_end(ym: str) -> date:
    year, month = (int(part) for part in ym.split("-"))
    return date(year, month, calendar.monthrange(year, month)[1])


def load_case_months(root: Path) -> tuple[Path, list[str]]:
    runs = []
    for folder in (root / "data/private/public-context").glob("fred-*"):
        receipt_path = folder / "run-complete.json"
        context_path = folder / "monthly-context.json"
        if not receipt_path.is_file() or not context_path.is_file():
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            context = json.loads(context_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if receipt.get("status") == "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE":
            runs.append((str(receipt.get("completed_at", "")), folder, context))
    if not runs:
        raise RuntimeError("No completed private D01 FRED context run was found")
    _, folder, context = max(runs, key=lambda item: item[0])
    months = [row.get("reporting_month") for row in context.get("rows", [])]
    if not months or any(not isinstance(item, str) or not re.fullmatch(r"\d{4}-\d{2}", item) for item in months):
        raise RuntimeError("The D01 monthly reporting calendar is malformed")
    if months != sorted(set(months)):
        raise RuntimeError("The D01 monthly reporting calendar is duplicated or unordered")
    return folder, months


def read_zip_validate(path: Path, series: str, vintages: list[str]) -> dict:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"ALFRED ZIP CRC failed for {bad}")
        csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_members) != 1:
            raise RuntimeError("ALFRED export must contain exactly one CSV matrix")
        raw = archive.read(csv_members[0]).decode("utf-8-sig")
    reader = csv.DictReader(raw.splitlines())
    expected_columns = [f"{series}_{date.fromisoformat(value).strftime('%Y%m%d')}" for value in vintages]
    if not reader.fieldnames or reader.fieldnames[0] != "observation_date" or reader.fieldnames[1:] != expected_columns:
        raise RuntimeError("ALFRED CSV columns do not match the selected series vintages")
    row_count = 0
    previous = None
    for row in reader:
        observed = date.fromisoformat(row["observation_date"])
        if previous is not None and observed <= previous:
            raise RuntimeError("ALFRED observation dates are not strictly increasing")
        previous = observed
        for column in expected_columns:
            raw_value = row[column]
            if raw_value not in ("", "."):
                value = float(raw_value)
                if not math.isfinite(value):
                    raise RuntimeError("ALFRED contains a non-finite numeric observation")
        row_count += 1
    if not row_count:
        raise RuntimeError("ALFRED export contains no observations")
    return {"csv_member": csv_members[0], "observation_rows": row_count, "vintage_columns": len(expected_columns)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Private D:\\data\\Codex\\credit-atlas workspace root")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--headless", action="store_true", help="Run Edge headlessly")
    args = parser.parse_args()
    root = args.root.resolve()
    if not 1 <= args.batch_size <= 25:
        raise SystemExit("--batch-size must be between 1 and 25")

    _, months = load_case_months(root)
    first_year, first_month = (int(part) for part in months[0].split("-"))
    first_month_start = date(first_year, first_month, 1)
    start_date = first_month_start.replace(year=first_month_start.year - 1).isoformat()
    end_date = month_end(months[-1]).isoformat()
    now = datetime.now(timezone.utc)
    run_id = "alfred-asof-" + now.strftime("%Y%m%dT%H%M%SZ")
    out_dir = root / "data/private/public-context" / run_id
    out_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "IN_PROGRESS",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "visibility": "private",
        "source": "ALFRED, Federal Reserve Bank of St. Louis",
        "source_help_url": "https://alfred.stlouisfed.org/help/downloaddata",
        "source_method": "Official ALFRED Download Data form; observations by vintage date, all observations; zipped CSV",
        "case_calendar_source": "D01 monthly-context.json from private FRED context run",
        "case_months": months,
        "observation_start_date": start_date,
        "observation_end_date": end_date,
        "cutoff_rule": "For each D01 reporting month, use the latest actual ALFRED vintage date on or before that calendar month's final day.",
        "predictor_qualified": False,
        "model_training_performed": False,
        "series": {},
    }
    manifest_path = out_dir / "manifest.json"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=args.headless)
        page = browser.new_page(accept_downloads=True)
        try:
            for series, url in SERIES.items():
                response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                if response is None or response.status != 200:
                    raise RuntimeError(f"ALFRED series form unavailable for {series}")
                choices = page.locator('[name="form[selected_vintage_dates][]"] option').evaluate_all(
                    "options => options.map(option => option.value).filter(Boolean)"
                )
                dates = sorted({date.fromisoformat(value) for value in choices})
                if not dates:
                    raise RuntimeError(f"ALFRED supplied no selectable vintage dates for {series}")
                month_to_vintage = {}
                for month in months:
                    cutoff = month_end(month)
                    eligible = [value for value in dates if value <= cutoff]
                    if not eligible:
                        raise RuntimeError(f"No ALFRED vintage is available by {month} for {series}")
                    month_to_vintage[month] = max(eligible).isoformat()
                selected = sorted(set(month_to_vintage.values()))
                batches = [selected[i:i + args.batch_size] for i in range(0, len(selected), args.batch_size)]
                series_receipt = {
                    "source_url": url,
                    "selected_vintages": selected,
                    "available_vintage_dates": len(dates),
                    "monthly_vintage_map": month_to_vintage,
                    "batches": [],
                }
                for batch_index, batch in enumerate(batches, start=1):
                    batch_name = f"{series.lower()}-{batch_index:03d}.zip"
                    target = out_dir / batch_name
                    last_error = None
                    for attempt in range(1, 4):
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                            page.locator('[name="form[obs_start_date]"]').fill(start_date)
                            page.locator('[name="form[obs_end_date]"]').fill(end_date)
                            page.locator('[name="form[selected_vintage_dates][]"]').select_option(batch)
                            page.locator('[name="form[file_type]"]').select_option("2")
                            page.locator('[name="form[file_format]"]').select_option("csv")
                            with page.expect_download(timeout=90_000) as download_info:
                                page.locator('[name="form[download_data]"]').click(timeout=20_000)
                            download_info.value.save_as(target)
                            details = read_zip_validate(target, series, batch)
                            series_receipt["batches"].append({
                                "file": batch_name,
                                "sha256": sha256(target),
                                "bytes": target.stat().st_size,
                                "vintages": batch,
                                **details,
                            })
                            manifest["series"][series] = series_receipt
                            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
                            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                            print(f"{series}: batch {batch_index}/{len(batches)} verified ({len(batch)} vintages)", flush=True)
                            break
                        except (PlaywrightTimeoutError, OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
                            last_error = f"{type(exc).__name__}: {str(exc)[:250]}"
                            target.unlink(missing_ok=True)
                            if attempt < 3:
                                time.sleep(2 * attempt)
                                continue
                    if last_error and len(series_receipt["batches"]) != batch_index:
                        manifest["failure"] = {"series_id": series, "batch": batch_index,
                                               "error": last_error,
                                               "completed_at": datetime.now(timezone.utc).isoformat()}
                        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                        raise RuntimeError(f"ALFRED download failed: {series} batch {batch_index}: {last_error}")
                manifest["series"][series] = series_receipt
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        finally:
            browser.close()

    manifest["status"] = "DOWNLOADED_AND_VALIDATED"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["total_zip_files"] = sum(len(item["batches"]) for item in manifest["series"].values())
    manifest["total_vintage_columns"] = sum(len(item["selected_vintages"]) for item in manifest["series"].values())
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "directory": str(out_dir),
                      "series": {key: len(value["selected_vintages"]) for key, value in manifest["series"].items()},
                      "zip_files": manifest["total_zip_files"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
