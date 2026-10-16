"""Acquire and audit the official HMDA 2025 Dynamic LAR/TS release on D:."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import duckdb

ROOT_DEFAULT = Path(r"D:\data\Codex\credit-atlas")
SOURCE_PAGE = "https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset/2025"
FRONTEND_SOURCE = "https://raw.githubusercontent.com/cfpb/hmda-frontend/master/src/data-publication/constants/dynamic-dataset.js"
DATASETS = {
    "lar": {"url": "https://files.ffiec.cfpb.gov/dynamic-data/2025/2025_lar.zip",
            "filename": "2025_lar.zip", "member": "2025_lar.txt", "max_bytes": 1024**3,
            "last_modified": "Sun, 11 Oct 2026 12:00:30 GMT"},
    "ts": {"url": "https://files.ffiec.cfpb.gov/dynamic-data/2025/2025_ts.zip",
           "filename": "2025_ts.zip", "member": "2025_ts.txt", "max_bytes": 16 * 1024**2,
           "last_modified": "Sun, 11 Oct 2026 12:00:20 GMT"},
}
REQUIRED_LAR = {"activity_year", "lei", "state_code", "action_taken", "loan_type", "loan_purpose", "loan_amount"}
REQUIRED_TS = {"activity_year", "calendar_quarter", "lei", "lar_count"}
SNAPSHOT_ID = "hmda-national-snapshot-2025-9a5e89600e3c"


class AcquisitionError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def head(url: str) -> dict:
    if url not in {item["url"] for item in DATASETS.values()}:
        raise AcquisitionError("URL is outside the exact FFIEC dynamic-data allowlist")
    response = subprocess.run(
        ["curl.exe", "--silent", "--show-error", "--proto", "=https", "--connect-timeout", "15",
         "--max-time", "45", "--head", "--write-out", "\nSTATUS:%{http_code}\nURL:%{url_effective}", url],
        capture_output=True, text=True, check=False)
    import re
    match = re.search(r"\nSTATUS:(\d{3})\nURL:(\S+)", response.stdout)
    if response.returncode or not match or match.group(1) != "200" or match.group(2) != url:
        raise AcquisitionError("FFIEC dynamic HEAD failed, returned non-200, or redirected")
    headers = {}
    for line in response.stdout[:match.start()].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if not 0 < length <= next(item["max_bytes"] for item in DATASETS.values() if item["url"] == url):
        raise AcquisitionError("FFIEC dynamic file size is outside its transfer bound")
    config = next(item for item in DATASETS.values() if item["url"] == url)
    if headers.get("last-modified") != config["last_modified"]:
        raise AcquisitionError("2025 Dynamic release changed; create a new dated acquisition instead of relabeling")
    return {"url": url, "http_status": 200, "bytes": length,
            "content_type": headers.get("content-type", "").split(";", 1)[0].lower(),
            "last_modified": headers["last-modified"], "etag": headers.get("etag")}


def download(config: dict, destination: Path) -> dict:
    metadata = head(config["url"])
    if metadata["content_type"] != "application/octet-stream":
        raise AcquisitionError("Unexpected FFIEC dynamic content type")
    if destination.exists() or destination.with_suffix(destination.suffix + ".partial").exists():
        raise AcquisitionError("Refusing to overwrite an existing or partial source archive")
    partial = destination.with_suffix(destination.suffix + ".partial")
    response = subprocess.run(
        ["curl.exe", "--fail", "--silent", "--show-error", "--proto", "=https", "--connect-timeout", "20",
         "--max-time", "1800", "--max-filesize", str(config["max_bytes"]), "--output", str(partial),
         "--write-out", "%{http_code}\n%{url_effective}", config["url"]],
        capture_output=True, text=True, check=False)
    lines = response.stdout.splitlines()
    if (response.returncode or lines != ["200", config["url"]] or not partial.is_file()
            or partial.stat().st_size != metadata["bytes"]):
        raise AcquisitionError("FFIEC dynamic GET failed, redirected, or byte count differs from HEAD")
    partial.replace(destination)
    return {**metadata, "file": destination.name, "sha256": sha256(destination),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}


def extract(archive_path: Path, config: dict, output_dir: Path) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if len(members) != 1 or members[0].filename != config["member"]:
            raise AcquisitionError("Dynamic ZIP member list differs from the exact expected single-file layout")
        member = members[0]
        if member.file_size > 15 * 1024**3 or member.file_size == 0:
            raise AcquisitionError("Dynamic ZIP member is outside the uncompressed-size bound")
        target = output_dir / config["member"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise AcquisitionError("Refusing to overwrite a pre-existing extracted source")
        digest = hashlib.sha256()
        copied = 0
        with archive.open(member) as src, target.open("xb") as dst:
            while chunk := src.read(1024 * 1024):
                copied += len(chunk)
                if copied > member.file_size:
                    raise AcquisitionError("ZIP member expanded beyond declared size")
                digest.update(chunk)
                dst.write(chunk)
        if copied != member.file_size or archive.testzip() is not None:
            raise AcquisitionError("Dynamic ZIP member size or CRC validation failed")
        return {"member": member.filename, "uncompressed_bytes": copied,
                "crc32": f"{member.CRC:08x}", "sha256": digest.hexdigest()}


def profile_lar(path: Path) -> dict:
    connection = duckdb.connect()
    connection.execute("SET memory_limit='2GB'")
    connection.execute("SET threads=4")
    connection.execute(f"SET temp_directory='{str(path.parent / 'duckdb-temp').replace(chr(39), chr(39)*2)}'")
    source = "read_csv(?, delim='|', header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = [row[0] for row in connection.execute(f"DESCRIBE SELECT * FROM {source}", [str(path)]).fetchall()]
        if len(columns) != 99 or len(set(columns)) != 99 or not REQUIRED_LAR.issubset(columns):
            raise AcquisitionError(f"HMDA dynamic LAR schema is not the expected 99-column public schema ({len(columns)})")
        overall = connection.execute(f"""
            SELECT count(*) AS records, count(DISTINCT lei) AS distinct_LEIs,
                   count(*) FILTER (WHERE activity_year <> '2025' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL) AS invalid_action_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS invalid_state_rows,
                   count(*) FILTER (WHERE loan_type NOT IN ('1','2','3','4') OR loan_type IS NULL) AS invalid_loan_type_rows,
                   count(*) FILTER (WHERE lei IS NULL OR length(lei) <> 20) AS invalid_lei_rows,
                   count(*) FILTER (WHERE TRY_CAST(loan_amount AS BIGINT) IS NULL AND loan_amount NOT IN ('NA','Exempt')) AS invalid_loan_amount_rows,
                   count(*) FILTER (WHERE action_taken IN ('1','2','3')) AS decided_applications,
                   count(*) FILTER (WHERE action_taken='3') AS denied_applications
            FROM {source}
        """, [str(path)]).fetchone()
        names = ["records", "distinct_LEIs", "wrong_year_rows", "invalid_action_rows", "invalid_state_rows",
                 "invalid_loan_type_rows", "invalid_lei_rows", "invalid_loan_amount_rows",
                 "decided_applications", "denied_applications"]
        summary = dict(zip(names, overall))
        actions = connection.execute(f"SELECT action_taken, count(*) FROM {source} GROUP BY 1 ORDER BY 1", [str(path)]).fetchall()
        states = connection.execute(f"SELECT state_code, count(*) FROM {source} GROUP BY 1 ORDER BY 1", [str(path)]).fetchall()
        if (not summary["records"] or summary["wrong_year_rows"] or summary["invalid_action_rows"]
                or summary["invalid_state_rows"] or summary["invalid_loan_type_rows"]
                or summary["invalid_lei_rows"] or summary["invalid_loan_amount_rows"]):
            raise AcquisitionError("HMDA dynamic LAR row-quality contract failed")
        return {"columns": columns, "summary": summary,
                "actions": [{"code": code, "records": count} for code, count in actions],
                "distinct_states": len(states),
                "denial_share_of_actions_1_3": summary["denied_applications"] / summary["decided_applications"],
                "outcome_semantics": "Application and underwriting actions only; no repayment, delinquency, default or PD label."}
    finally:
        connection.close()


def profile_ts(path: Path) -> dict:
    columns = None
    records = blank_or_duplicate_lei = invalid_count_rows = 0
    seen = set()
    years, quarters = set(), set()
    reported_lar_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        columns = reader.fieldnames or []
        if len(columns) != 10 or not REQUIRED_TS.issubset(columns):
            raise AcquisitionError("HMDA dynamic TS schema differs from expected public fields")
        for row in reader:
            records += 1
            lei = row.get("lei", "")
            if not lei or lei in seen:
                blank_or_duplicate_lei += 1
            seen.add(lei)
            years.add(row.get("activity_year", ""))
            quarters.add(row.get("calendar_quarter", ""))
            try:
                reported_lar_count += int(row.get("lar_count", ""))
            except (TypeError, ValueError):
                invalid_count_rows += 1
    if blank_or_duplicate_lei or invalid_count_rows or years != {"2025"}:
        raise AcquisitionError("HMDA dynamic TS quality/year checks failed")
    return {"columns": columns, "summary": {"records": records, "unique_LEIs": len(seen),
            "activity_years": sorted(years), "calendar_quarters": sorted(quarters),
            "sum_reported_lar_count": reported_lar_count,
            "invalid_or_blank_count_rows": invalid_count_rows,
            "blank_or_duplicate_LEI_rows": blank_or_duplicate_lei},
            "privacy_note": "Institution row values and tax identifiers are not copied into receipts or exports."}


def acquire(root: Path) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise AcquisitionError("Private HMDA data must remain under D:")
    folder = root / "data/private/hmda/hmda-national-dynamic-2025-20261011"
    folder.mkdir(parents=True, exist_ok=True)
    payloads = {}
    extracted_dir = folder / "extracted"
    try:
        for name, config in DATASETS.items():
            archive = folder / config["filename"]
            if archive.exists():
                metadata = head(config["url"])
                if archive.stat().st_size != metadata["bytes"]:
                    raise AcquisitionError(f"Existing {name.upper()} archive differs from official current Content-Length")
                http = {**metadata, "file": archive.name, "sha256": sha256(archive), "reused_existing": True}
            else:
                http = download(config, archive)
            csv_meta = extract(archive, config, extracted_dir)
            profile = profile_lar(extracted_dir / config["member"]) if name == "lar" else profile_ts(extracted_dir / config["member"])
            payloads[name] = {"http": http, "archive_sha256": sha256(archive), "csv": csv_meta, "profile": profile}
        lar = payloads["lar"]["profile"]["summary"]
        ts = payloads["ts"]["profile"]["summary"]
        if ts["sum_reported_lar_count"] != lar["records"] or ts["unique_LEIs"] != lar["distinct_LEIs"]:
            raise AcquisitionError("Dynamic TS LAR count or distinct reporter count does not reconcile to LAR")
        snapshot_path = root / "data/private/hmda" / SNAPSHOT_ID / "acquisition-complete.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        static_lar = snapshot["datasets"]["lar"]["profile"]
        static_actions = {row["value"]: row["records"] for row in static_lar["actions"]}
        dynamic_actions = {row["code"]: row["records"] for row in payloads["lar"]["profile"]["actions"]}
        comparison = {code: {"snapshot_2026_06_02": static_actions.get(code, 0),
                             "dynamic_2026_10_11": dynamic_actions.get(code, 0),
                             "difference": dynamic_actions.get(code, 0) - static_actions.get(code, 0)}
                      for code in sorted(set(static_actions) | set(dynamic_actions))}
        result = {"source_id": folder.name, "status": "VERIFIED_HMDA_2025_DYNAMIC_AS_OF_2026_10_11",
                  "publisher": "FFIEC / Consumer Financial Protection Bureau",
                  "source_page": SOURCE_PAGE, "frontend_source": FRONTEND_SOURCE,
                  "release_as_of_utc": {name: config["last_modified"] for name, config in DATASETS.items()},
                  "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                  "datasets": payloads, "comparison_to_snapshot_2026_06_02": comparison,
                  "interpretation": "Dated point-in-time copy of a weekly mutable application/decision dataset; differences versus the static snapshot are submission/resubmission and snapshot-design differences, not borrower outcomes.",
                  "visibility": "private", "public_release_approved": False,
                  "loan_performance_labels": False, "forecast_or_imputation": False,
                  "tax_identifier_rows_exported": False,
                  "limitations": ["Dynamic LAR is updated as institutions submit or resubmit; this archive represents the dated FFIEC file, not an immutable final annual vintage.",
                                  "HMDA contains application and action records, not repayment/default history or calibrated PD.",
                                  "Do not join to Freddie/Fannie/Ginnie performance without a documented authorized stable key."]}
        if any(result["datasets"][name]["http"]["last_modified"] != config["last_modified"]
               for name, config in DATASETS.items()):
            raise AcquisitionError("Release date changed during acquisition")
        (folder / "acquisition-complete.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        shutil.rmtree(extracted_dir)
        return result
    except Exception as error:
        failure = {"source_id": folder.name, "status": "ACQUISITION_OR_AUDIT_FAILED",
                   "failed_at_utc": datetime.now(timezone.utc).isoformat(),
                   "exception_type": type(error).__name__, "message": str(error),
                   "verified_payloads": payloads}
        (folder / "acquisition-failed.json").write_text(json.dumps(failure, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    args = parser.parse_args()
    try:
        print(json.dumps(acquire(args.root), indent=2, ensure_ascii=False))
    except (OSError, zipfile.BadZipFile, duckdb.Error, AcquisitionError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
