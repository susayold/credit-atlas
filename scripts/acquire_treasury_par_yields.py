"""Acquire Treasury's published daily par-yield curves and audit FRED overlap.

Raw source data and receipts are written only to the private D: workspace.
No values are filled, interpolated, or model-qualified by this utility.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ARCHIVE_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rate-archives/par-yield-curve-rates-1990-2023.csv"
)
ANNUAL_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?{query}"
)
ARCHIVE_PAGE = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rate-archives"
)
CURRENT_PAGE = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView"
)
METHOD_URL = (
    "https://home.treasury.gov/policy-issues/financing-the-government/"
    "interest-rate-statistics/treasury-yield-curve-methodology"
)
FRED_IDS = {"2YR": "DGS2", "10YR": "DGS10", "30YR": "DGS30"}
MATURITIES = {"2YR": "2 yr", "10YR": "10 yr", "30YR": "30 yr"}
MISSING = {"", ".", "N/A", "NA", "N.A."}
MAX_DOWNLOAD = 8_000_000
MAX_CELL_RATE = Decimal("100")
DEFAULT_PRIVATE_ROOT = Path(__file__).resolve().parents[2] / "credit-atlas"


class AcquisitionError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_download(url: str) -> tuple[bytes, dict]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "home.treasury.gov":
        raise AcquisitionError("Treasury download URL is outside the approved HTTPS host")
    request = Request(url, headers={"User-Agent": "CreditAtlas official Treasury research/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            final = urlparse(response.geturl())
            if response.status != 200 or final.scheme != "https" or final.hostname != "home.treasury.gov":
                raise AcquisitionError("Treasury response redirected or returned an unexpected status")
            content_type = (response.headers.get("Content-Type") or "").lower()
            if not ("csv" in content_type or "text/plain" in content_type or "octet-stream" in content_type):
                raise AcquisitionError("Treasury response is not identified as a CSV/text payload")
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_DOWNLOAD:
                raise AcquisitionError("Treasury CSV exceeds the bounded download size")
            body = response.read(MAX_DOWNLOAD + 1)
            if not body or len(body) > MAX_DOWNLOAD:
                raise AcquisitionError("Treasury CSV is empty or exceeds the bounded download size")
            return body, {"final_url": response.geturl(), "content_type": content_type,
                          "content_length_header": length, "response_bytes": len(body)}
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError("Treasury CSV request failed") from exc


def annual_url(year: int) -> str:
    query = urlencode({"type": "daily_treasury_yield_curve",
                       "field_tdr_date_value": str(year), "page": "", "_format": "csv"})
    return ANNUAL_URL.format(year=year, query=query)


def _normal_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower().lstrip("\ufeff"))


def parse_treasury_csv(body: bytes, source_period: str) -> list[dict]:
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AcquisitionError("Treasury CSV is not UTF-8/UTF-8-SIG") from exc
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise AcquisitionError("Treasury CSV is missing a header")
    headers = {_normal_header(name): name for name in reader.fieldnames if name is not None}
    date_key = next((headers[key] for key in ("date", "observationdate") if key in headers), None)
    keys = {maturity: headers.get(_normal_header(label)) for maturity, label in MATURITIES.items()}
    if not date_key or any(value is None for value in keys.values()):
        raise AcquisitionError("Treasury CSV lacks Date, 2 Yr, 10 Yr, or 30 Yr fields")
    rows, seen = [], set()
    for row in reader:
        if None in row:
            raise AcquisitionError("Treasury CSV row contains extra fields")
        raw_date = (row.get(date_key) or "").strip()
        try:
            observed = date.fromisoformat(raw_date) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date) else datetime.strptime(raw_date, "%m/%d/%Y").date()
        except ValueError as exc:
            raise AcquisitionError("Treasury CSV contains an invalid date") from exc
        if observed in seen:
            raise AcquisitionError("Treasury CSV contains duplicate dates")
        seen.add(observed)
        if observed.year not in _expected_years(source_period):
            raise AcquisitionError("Treasury row falls outside its archive/year partition")
        values = {}
        for maturity, header in keys.items():
            raw = (row.get(header) or "").strip()
            if raw.upper() in MISSING:
                values[maturity] = None
                continue
            try:
                value = Decimal(raw)
            except InvalidOperation as exc:
                raise AcquisitionError("Treasury CSV contains a nonnumeric yield") from exc
            if not value.is_finite() or value < 0 or value >= MAX_CELL_RATE or value != value.quantize(Decimal(".0001")):
                raise AcquisitionError("Treasury yield is nonfinite, out of range, or too precise")
            values[maturity] = value
        rows.append({"observation_date": observed, **values})
    if not rows:
        raise AcquisitionError("Treasury CSV contains no observations")
    rows.sort(key=lambda row: row["observation_date"])
    return rows


def _expected_years(period: str) -> range:
    if period == "1990-2023":
        return range(1990, 2024)
    return range(int(period), int(period) + 1)


def parse_fred_csv(path: Path, series: str) -> dict[date, Decimal | None]:
    values = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["observation_date", series]:
            raise AcquisitionError("FRED comparator header does not match its series")
        for row in reader:
            observed = date.fromisoformat(row["observation_date"])
            raw = (row[series] or "").strip()
            if observed in values:
                raise AcquisitionError("FRED comparator has duplicate dates")
            if raw in MISSING:
                values[observed] = None
            else:
                try:
                    values[observed] = Decimal(raw)
                except InvalidOperation as exc:
                    raise AcquisitionError("FRED comparator contains an invalid decimal") from exc
    return values


def compare_series(treasury: list[dict], fred: dict[date, Decimal | None], maturity: str) -> dict:
    direct = {row["observation_date"]: row[maturity] for row in treasury}
    date_union = set(direct) | set(fred)
    both_known = [day for day in date_union if direct.get(day) is not None and fred.get(day) is not None]
    differences = [day for day in both_known if direct[day] != fred[day]]
    direct_only = [day for day in date_union if direct.get(day) is not None and fred.get(day) is None]
    fred_only = [day for day in date_union if fred.get(day) is not None and direct.get(day) is None]
    common_dates = set(direct) & set(fred)
    direct_missing_fred_known = [day for day in common_dates if direct[day] is None and fred[day] is not None]
    fred_missing_direct_known = [day for day in common_dates if fred[day] is None and direct[day] is not None]
    both_missing = [day for day in common_dates if direct[day] is None and fred[day] is None]
    direct_known_no_fred_row = [day for day, value in direct.items() if value is not None and day not in fred]
    fred_known_no_treasury_row = [day for day, value in fred.items() if value is not None and day not in direct]
    return {
        "fred_series": FRED_IDS[maturity],
        "direct_native_dates": len(direct),
        "fred_native_dates": len(fred),
        "direct_known": sum(value is not None for value in direct.values()),
        "fred_known": sum(value is not None for value in fred.values()),
        "same_calendar_dates": len(common_dates),
        "both_known_date_comparisons": len(both_known),
        "exact_value_mismatches": len(differences),
        "exact_match_rate_when_both_known": 1.0 if not both_known else (len(both_known) - len(differences)) / len(both_known),
        "common_date_treasury_missing_fred_known": len(direct_missing_fred_known),
        "common_date_fred_missing_treasury_known": len(fred_missing_direct_known),
        "common_date_both_missing": len(both_missing),
        "treasury_known_dates_without_fred_calendar_row": len(direct_known_no_fred_row),
        "fred_known_dates_without_treasury_calendar_row": len(fred_known_no_treasury_row),
        "common_date_treasury_missing_examples": [day.isoformat() for day in sorted(direct_missing_fred_known)[:20]],
        "common_date_fred_missing_examples": [day.isoformat() for day in sorted(fred_missing_direct_known)[:20]],
        "common_date_both_missing_examples": [day.isoformat() for day in sorted(both_missing)[:20]],
        "mismatch_examples": [
            {"date": day.isoformat(), "treasury": str(direct[day]), "fred": str(fred[day])}
            for day in sorted(differences)[:20]
        ],
        "treasury_known_fred_missing_or_absent": len(direct_only),
        "fred_known_treasury_missing_or_absent": len(fred_only),
        "direct_first_date": min(direct).isoformat(),
        "direct_last_date": max(direct).isoformat(),
        "fred_first_date": min(fred).isoformat(),
        "fred_last_date": max(fred).isoformat(),
    }


def acquire(workspace: Path, fred_suite: str) -> dict:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise AcquisitionError("Private workspace must be on D:")
    suite = workspace / "data" / "private" / "public-suite" / fred_suite
    receipt_path = suite / "acquisition-complete.json"
    if not receipt_path.is_file():
        raise AcquisitionError("Requested private FRED comparator suite is unavailable")
    acquisition = json.loads(receipt_path.read_text(encoding="utf-8"))
    if acquisition.get("status") != "COMPLETE" or acquisition.get("visibility") != "private":
        raise AcquisitionError("FRED comparator receipt is not a complete private receipt")
    fred_records = {item["source_id"]: item for item in acquisition.get("sources", [])}
    for series in FRED_IDS.values():
        item = fred_records.get("fred-" + series.lower())
        if not item or item.get("status") != "DOWNLOADED_AND_PROFILED":
            raise AcquisitionError("FRED comparator series receipt is missing")
        path = suite / item["file"]
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise AcquisitionError("FRED comparator file hash does not match its receipt")

    run_id = "treasury-par-yield-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    out = workspace / "data" / "private" / "market-context" / "treasury-par-yields" / run_id
    out.mkdir(parents=True, exist_ok=False)
    current_year = datetime.now(timezone.utc).year
    requests = [("1990-2023", ARCHIVE_URL)] + [(str(year), annual_url(year)) for year in range(2024, current_year + 1)]
    source_files, rows_all = [], []
    for period, url in requests:
        body, response = safe_download(url)
        raw_name = "treasury-par-yields-" + period + ".csv"
        raw_path = out / raw_name
        raw_path.write_bytes(body)
        rows = parse_treasury_csv(body, period)
        rows_all.extend(rows)
        source_files.append({
            "source_id": "treasury-daily-par-yield-" + period,
            "publisher": "U.S. Department of the Treasury",
            "source_page_url": ARCHIVE_PAGE if period == "1990-2023" else CURRENT_PAGE + "?" + urlencode({"field_tdr_date_value": period, "type": "daily_treasury_yield_curve"}),
            "source_object_url": url,
            "file": raw_name,
            "sha256": sha256_bytes(body),
            "bytes": len(body),
            "row_count": len(rows),
            "first_date": min(row["observation_date"] for row in rows).isoformat(),
            "last_date": max(row["observation_date"] for row in rows).isoformat(),
            "response": response,
        })
    rows_all.sort(key=lambda row: row["observation_date"])
    if len({row["observation_date"] for row in rows_all}) != len(rows_all):
        raise AcquisitionError("Treasury partitions overlap on observation dates")
    if any(left["observation_date"] >= right["observation_date"] for left, right in zip(rows_all, rows_all[1:])):
        raise AcquisitionError("Combined Treasury data are not strictly ordered")
    normalized = out / "normalized-treasury-par-yields.csv"
    with normalized.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["observation_date", "TREASURY2Y", "TREASURY10Y", "TREASURY30Y"])
        for row in rows_all:
            writer.writerow([row["observation_date"].isoformat(), *("" if row[m] is None else str(row[m]) for m in ("2YR", "10YR", "30YR"))])
    fred = {maturity: parse_fred_csv(suite / fred_records["fred-" + FRED_IDS[maturity].lower()]["file"], FRED_IDS[maturity])
            for maturity in FRED_IDS}
    comparisons = {maturity: compare_series(rows_all, fred[maturity], maturity) for maturity in FRED_IDS}
    profiles = {}
    for maturity in FRED_IDS:
        values = [row[maturity] for row in rows_all]
        profiles[maturity] = {
            "rows": len(rows_all), "known": sum(value is not None for value in values),
            "missing": sum(value is None for value in values),
            "first_known_date": next(row["observation_date"].isoformat() for row in rows_all if row[maturity] is not None),
            "last_known_date": next(row["observation_date"].isoformat() for row in reversed(rows_all) if row[maturity] is not None),
            "discontinuation_window_known_30y": sum(
                row["30YR"] is not None and row["observation_date"].isoformat() >= "2002-02-18"
                and row["observation_date"].isoformat() < "2006-02-09" for row in rows_all
            ) if maturity == "30YR" else None,
        }
    receipt = {
        "schema_version": 1, "run_id": run_id, "status": "DOWNLOADED_AND_AUDITED",
        "visibility": "private", "public_release_approved": False,
        "model_training_performed": False, "model_qualified": False,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "acquisition_method_sha256": sha256_file(Path(__file__).resolve()),
        "publisher": "U.S. Department of the Treasury",
        "distributor": None,
        "source_methodology_url": METHOD_URL,
        "methodology_notes": [
            "Treasury par yield curve; values are percent, source-native daily observations.",
            "No interpolation, resampling, fill, or forecast is applied by this acquisition.",
            "Treasury changed to monotone-convex methodology on 2021-12-06; earlier values use historical method/revisions as published.",
            "Treasury 30-year series has a documented discontinuation interval 2002-02-18 through 2006-02-08; source cells are preserved, model usability is not approved here.",
        ],
        "fred_comparator_suite_id": fred_suite,
        "fred_comparator_receipt_sha256": sha256_file(receipt_path),
        "source_files": source_files,
        "normalized_file": {"file": normalized.name, "sha256": sha256_file(normalized), "bytes": normalized.stat().st_size},
        "native_rows": len(rows_all),
        "first_date": rows_all[0]["observation_date"].isoformat(),
        "last_date": rows_all[-1]["observation_date"].isoformat(),
        "profiles": profiles,
        "fred_overlap_comparisons": comparisons,
        "rights_review_status": "OFFICIAL_PUBLIC_ENDPOINT; RAW_RETAINED_PRIVATE; NO_PUBLIC_REHOSTING_APPROVED",
        "rights_note": "Official Treasury public CSV; no separate data redistribution grant was established in this acquisition. Keep raw files and output receipts private pending fuller reuse review.",
        "known_limitations": [
            "Current Treasury snapshot can be revised; not a historical point-in-time vintage.",
            "Exact overlap parity must be judged from fred_overlap_comparisons; this receipt does not qualify any model feature.",
            "H.15/FRED 30-year published values during its documented discontinuation window remain subject to quarantine in the existing market workflow.",
        ],
        "files": [],
    }
    for path in [*sorted(out.glob("treasury-par-yields-*.csv")), normalized]:
        receipt["files"].append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    receipt_file = out / "acquisition-audit.json"
    receipt["receipt_file"] = receipt_file.name
    receipt_file.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=DEFAULT_PRIVATE_ROOT)
    parser.add_argument("--fred-suite", required=True)
    args = parser.parse_args()
    try:
        result = acquire(args.workspace, args.fred_suite)
    except AcquisitionError as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in (
        "run_id", "status", "native_rows", "first_date", "last_date", "profiles", "fred_overlap_comparisons", "rights_review_status"
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
