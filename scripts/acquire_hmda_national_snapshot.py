"""Acquire and aggregate-audit the official 2025 HMDA snapshot privately on D:."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import time
import uuid
import zipfile
from pathlib import Path, PurePosixPath

import duckdb

ROOT_DEFAULT = Path(r"D:\data\Codex\credit-atlas")
SOURCE_PAGE = "https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2025"
PRESS_RELEASE = "https://www.ffiec.gov/news/press-releases/2026/an-06-23"
FRONTEND_SOURCE = "https://github.com/cfpb/hmda-frontend/blob/master/src/data-publication/constants/snapshot-dataset.jsx"
DATASETS = {
    "lar": {
        "url": "https://files.ffiec.cfpb.gov/static-data/snapshot/2025/2025_public_lar_csv.zip",
        "filename": "2025_public_lar_csv.zip",
        "max_bytes": 1024**3,
    },
    "ts": {
        "url": "https://files.ffiec.cfpb.gov/static-data/snapshot/2025/2025_public_ts_csv.zip",
        "filename": "2025_public_ts_csv.zip",
        "max_bytes": 16 * 1024**2,
    },
    "msamd": {
        "url": "https://files.ffiec.cfpb.gov/static-data/snapshot/2025/2025_public_msamd_csv.zip",
        "filename": "2025_public_msamd_csv.zip",
        "max_bytes": 16 * 1024**2,
    },
}
REQUIRED_LAR = {"activity_year", "lei", "state_code", "action_taken", "loan_type",
                "loan_purpose", "construction_method", "occupancy_type", "loan_amount"}
REQUIRED_TS = {"activity_year", "calendar_quarter", "lei", "tax_id", "agency_code",
               "respondent_name", "respondent_state", "respondent_city", "respondent_zip_code", "lar_count"}
REQUIRED_MSAMD = {"msa_md", "msa_md_name", "state"}


class AcquisitionError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def request_headers(url: str) -> dict:
    if url not in {item["url"] for item in DATASETS.values()}:
        raise AcquisitionError("URL is outside the exact FFIEC snapshot allowlist")
    response = subprocess.run(["curl.exe", "--silent", "--show-error", "--proto", "=https",
        "--connect-timeout", "15", "--max-time", "45", "--head", "--write-out",
        "\nSTATUS:%{http_code}\nURL:%{url_effective}", url], capture_output=True, text=True)
    raw = response.stdout
    status_match = __import__("re").search(r"\nSTATUS:(\d{3})\nURL:(\S+)", raw)
    if response.returncode or not status_match or int(status_match.group(1)) != 200 or status_match.group(2) != url:
        raise AcquisitionError(f"FFIEC HEAD failed or redirected: curl={response.returncode}, status={status_match.group(1) if status_match else 'unknown'}")
    headers = raw[:status_match.start()].splitlines()
    normalized = {}
    for line in headers:
        if ":" in line:
            key, value = line.split(":", 1)
            normalized[key.strip().lower()] = value.strip()
    return {"status": 200, "url": url,
            "content_type": normalized.get("content-type", "").split(";", 1)[0].lower(),
            "content_length": int(normalized.get("content-length", "0")),
            "last_modified": normalized.get("last-modified"),
            "etag": normalized.get("etag")}


def download(url: str, destination: Path, max_bytes: int) -> dict:
    metadata = request_headers(url)
    if metadata["content_type"] != "application/zip" or not 0 < metadata["content_length"] <= max_bytes:
        raise AcquisitionError("Unexpected source type or archive size")
    if destination.exists() or destination.with_suffix(destination.suffix + ".partial").exists():
        raise AcquisitionError("Refusing to overwrite an existing or partial source file")
    partial = destination.with_suffix(destination.suffix + ".partial")
    headers_path = destination.with_suffix(destination.suffix + ".headers.partial")
    response = subprocess.run(["curl.exe", "--fail", "--silent", "--show-error", "--proto", "=https",
        "--connect-timeout", "20", "--max-time", "1800", "--max-filesize", str(max_bytes),
        "--dump-header", str(headers_path), "--output", str(partial), "--write-out",
        "%{http_code}\n%{url_effective}", url], capture_output=True, text=True)
    lines = response.stdout.splitlines()
    if (response.returncode or len(lines) != 2 or lines[0] != "200" or lines[1] != url
            or not partial.is_file()):
        raise AcquisitionError(f"FFIEC GET failed or redirected: curl={response.returncode}, response={response.stdout[-120:]}")
    received = partial.stat().st_size
    if received != metadata["content_length"] or received > max_bytes:
        raise AcquisitionError("Downloaded bytes differ from official HEAD Content-Length")
    headers_path.unlink(missing_ok=True)
    partial.replace(destination)
    return {"url": url, "file": destination.name, "http_status": 200,
            "content_type": metadata["content_type"], "bytes": received,
            "last_modified": metadata["last_modified"], "etag": metadata["etag"],
            "sha256": sha256(destination), "retrieved_unix": int(time.time())}


def extract_single_csv(archive_path: Path, output_dir: Path, max_uncompressed: int) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        files = [member for member in archive.infolist() if not member.is_dir()]
        csvs = [member for member in files
                if member.filename.casefold().endswith(".csv")
                and not PurePosixPath(member.filename).name.startswith("._")]
        if len(csvs) != 1:
            raise AcquisitionError("Expected exactly one CSV member")
        member = csvs[0]
        # FFIEC's Transmittal Sheet ZIP contains a harmless macOS resource-fork
        # sidecar. Permit only the exact companion filename; never extract it.
        allowed_sidecars = {f"__MACOSX/._{member.filename}"}
        unexpected = [item.filename for item in files if item is not member and item.filename not in allowed_sidecars]
        if unexpected:
            raise AcquisitionError(f"Unexpected non-CSV ZIP members: {unexpected[:3]}")
        if (PurePosixPath(member.filename).name != member.filename or member.file_size <= 0
                or member.file_size > max_uncompressed):
            raise AcquisitionError("Unsafe CSV member name or size")
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / member.filename
        partial = destination.with_suffix(destination.suffix + ".partial")
        if partial.exists():
            raise AcquisitionError("Refusing to overwrite an existing partial extracted source")
        if destination.exists():
            member_digest = hashlib.sha256()
            with archive.open(member) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    member_digest.update(chunk)
            if destination.stat().st_size != member.file_size or sha256(destination) != member_digest.hexdigest():
                raise AcquisitionError("Existing extracted CSV does not match its ZIP member")
            if archive.testzip() is not None:
                raise AcquisitionError("ZIP CRC failed for existing extracted source")
            return {"member": member.filename, "bytes": member.file_size, "crc32": f"{member.CRC:08x}",
                    "sha256": member_digest.hexdigest(), "path": str(destination), "verified_existing": True}
        digest = hashlib.sha256()
        copied = 0
        with archive.open(member) as source, partial.open("xb") as target:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > member.file_size:
                    raise AcquisitionError("ZIP member expanded beyond its declared size")
                target.write(chunk)
                digest.update(chunk)
        if copied != member.file_size:
            raise AcquisitionError("Extracted bytes differ from ZIP metadata")
        bad_member = archive.testzip()
        if bad_member is not None:
            raise AcquisitionError(f"ZIP CRC failed for {bad_member}")
        partial.replace(destination)
        return {"member": member.filename, "bytes": copied, "crc32": f"{member.CRC:08x}",
                "sha256": digest.hexdigest(), "path": str(destination)}


def profile_lar(path: Path) -> dict:
    connection = duckdb.connect()
    connection.execute("SET memory_limit='2GB'")
    connection.execute("SET threads=4")
    connection.execute(f"SET temp_directory='{str(path.parent / 'duckdb-temp').replace(chr(39), chr(39)*2)}'")
    relation = "read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        names = [row[0] for row in connection.execute(f"DESCRIBE SELECT * FROM {relation}", [str(path)]).fetchall()]
        if len(names) != 99 or len(set(names)) != 99 or not REQUIRED_LAR.issubset(names):
            raise AcquisitionError(f"2025 public LAR schema contract failed: {len(names)} fields")
        summary = connection.execute(f"""
            SELECT count(*) AS records,
                   count(DISTINCT lei) AS distinct_reporting_LEIs,
                   count(*) FILTER (WHERE activity_year <> '2025' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8')
                                      OR action_taken IS NULL) AS invalid_action_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS invalid_state_rows,
                   count(*) FILTER (WHERE loan_type NOT IN ('1','2','3','4') OR loan_type IS NULL) AS invalid_loan_type_rows,
                   count(*) FILTER (WHERE lei IS NULL OR length(lei) <> 20) AS invalid_lei_rows,
                   count(*) FILTER (WHERE action_taken IN ('1','2','3')) AS decided_applications,
                   count(*) FILTER (WHERE action_taken='3') AS denied_applications
            FROM {relation}
        """, [str(path)]).fetchone()
        summary_names = ["records", "distinct_reporting_LEIs", "wrong_year_rows", "invalid_action_rows",
                         "invalid_state_rows", "invalid_loan_type_rows", "invalid_lei_rows",
                         "decided_applications", "denied_applications"]
        overall = dict(zip(summary_names, summary))
        actions = connection.execute(f"""
            SELECT action_taken AS value, count(*) AS records
            FROM {relation} GROUP BY 1 ORDER BY 1
        """, [str(path)]).fetchall()
        states = connection.execute(f"""
            SELECT state_code AS value, count(*) AS records
            FROM {relation} GROUP BY 1 ORDER BY 1
        """, [str(path)]).fetchall()
        loan_types = connection.execute(f"""
            SELECT loan_type AS value, count(*) AS records
            FROM {relation} GROUP BY 1 ORDER BY 1
        """, [str(path)]).fetchall()
        if not overall["records"] or not overall["decided_applications"]:
            raise AcquisitionError("National LAR is empty or has no decision records")
        return {"columns": names, "summary": overall,
                "actions": [{"value": value, "records": count} for value, count in actions],
                "state_counts": [{"value": value, "records": count} for value, count in states],
                "loan_type_counts": [{"value": value, "records": count} for value, count in loan_types],
                "denial_share_of_decided": overall["denied_applications"] / overall["decided_applications"],
                "outcome_semantics": "application/underwriting action only; not delinquency, default, PD, or repayment performance"}
    finally:
        connection.close()


def profile_reference(path: Path, dataset_key: str) -> dict:
    expected = REQUIRED_TS if dataset_key == "ts" else REQUIRED_MSAMD
    columns = None
    rows = 0
    blank_key_rows = 0
    key_values = set()
    duplicates = 0
    invalid_rows = 0
    lar_count_total = 0
    years = set()
    quarters = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if len(columns) != len(expected) or set(columns) != expected:
            raise AcquisitionError(f"{dataset_key.upper()} header does not match expected published schema")
        key_field = "lei" if dataset_key == "ts" else "msa_md"
        for row in reader:
            rows += 1
            key = row.get(key_field, "")
            if not key:
                blank_key_rows += 1
            elif key in key_values:
                duplicates += 1
            key_values.add(key)
            if dataset_key == "ts":
                years.add(row.get("activity_year", ""))
                quarters.add(row.get("calendar_quarter", ""))
                try:
                    lar_count_total += int(row.get("lar_count", ""))
                except (TypeError, ValueError):
                    invalid_rows += 1
    if not rows or blank_key_rows or duplicates or invalid_rows:
        raise AcquisitionError(f"{dataset_key.upper()} has blank/duplicate keys or invalid count values")
    summary = {"records": rows, "distinct_keys": len(key_values), "blank_key_rows": blank_key_rows,
               "duplicate_key_rows": duplicates}
    if dataset_key == "ts":
        if years != {"2025"} or quarters != {"4"}:
            raise AcquisitionError("TS activity year/calendar quarter is outside the 2025 Q4 snapshot")
        summary.update({"activity_years": sorted(years), "calendar_quarters": sorted(quarters),
                        "sum_reported_lar_count": lar_count_total, "invalid_lar_count_rows": invalid_rows})
    return {"columns": columns, "summary": summary,
            "privacy_note": "Institution-level rows and tax identifiers are not written to public receipts."}


def validate_cross_dataset(payloads: dict) -> None:
    lar = payloads["lar"]["profile"]["summary"]
    ts = payloads["ts"]["profile"]["summary"]
    msamd = payloads["msamd"]["profile"]["summary"]
    if ts["records"] != ts["distinct_keys"] or ts["distinct_keys"] != lar["distinct_reporting_LEIs"]:
        raise AcquisitionError("TS record/LEI count does not reconcile to national LAR reporters")
    if ts["sum_reported_lar_count"] != lar["records"]:
        raise AcquisitionError("TS reported LAR count does not reconcile to LAR rows")
    if msamd["records"] != msamd["distinct_keys"]:
        raise AcquisitionError("MSA/MD lookup contains repeated geographic codes")


def audit_csv(root: Path, folder: Path, dataset_key: str) -> dict:
    if dataset_key not in DATASETS or root.drive.upper() != "D:":
        raise AcquisitionError("Invalid dataset or non-D: workspace")
    archive = folder / DATASETS[dataset_key]["filename"]
    extracted = extract_single_csv(archive, folder / "extracted", max_uncompressed=15 * 1024**3)
    if dataset_key == "lar":
        profile = profile_lar(Path(extracted["path"]))
    else:
        profile = profile_reference(Path(extracted["path"]), dataset_key)
    return {"archive": {"file": archive.name, "bytes": archive.stat().st_size,
                         "sha256": sha256(archive)}, "csv": extracted, "profile": profile}


def acquire(root: Path) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise AcquisitionError("Private data and receipts must remain on D:")
    identifier = "hmda-national-snapshot-2025-" + uuid.uuid4().hex[:12]
    folder = root / "data/private/hmda" / identifier
    folder.mkdir(parents=True, exist_ok=False)
    payloads = {}
    try:
        for name, config in DATASETS.items():
            item = download(config["url"], folder / config["filename"], config["max_bytes"])
            payloads[name] = audit_csv(root, folder, name)
            payloads[name]["http"] = item
        validate_cross_dataset(payloads)
        reporters = payloads["lar"]["profile"]["summary"]["distinct_reporting_LEIs"]
        result = {"source_id": identifier, "status": "VERIFIED_HMDA_NATIONAL_SNAPSHOT_2025",
                  "publisher": "FFIEC / Consumer Financial Protection Bureau",
                  "source_page": SOURCE_PAGE, "press_release": PRESS_RELEASE,
                  "frontend_source": FRONTEND_SOURCE, "snapshot_freeze_date": "2026-06-02",
                  "release_summary_reporters": 4782, "distinct_LEIs_in_LAR": reporters,
                  "reporter_count_match": reporters == 4782,
                  "retrieved_at_unix": int(time.time()), "datasets": payloads,
                  "visibility": "private", "public_release_approved": False,
                  "loan_performance_labels": False, "forecast_or_imputation": False,
                  "limitations": [
                      "HMDA LAR records applications and actions, not monthly repayment or default outcomes.",
                      "Public privacy modifications and lack of borrower/loan linkage constrain longitudinal joins.",
                      "2025 snapshot may differ from eventual one-year dataset after later resubmissions.",
                      "This new national source is a separate D08 case and does not qualify D01 Freddie multi-vintage gates.",
                  ]}
        output = folder / "acquisition-complete.json"
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return result
    except Exception as error:
        failed = {"source_id": identifier, "status": "ACQUISITION_OR_AUDIT_FAILED",
                  "failed_at_unix": int(time.time()), "exception_type": type(error).__name__,
                  "message": str(error), "verified_payloads": payloads}
        (folder / "acquisition-failed.json").write_text(json.dumps(failed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise


def resume(root: Path, folder: Path) -> dict:
    """Resume a failed acquisition without reacquiring already audited payloads."""
    root = root.resolve()
    folder = folder.resolve()
    expected_parent = (root / "data/private/hmda").resolve()
    if root.drive.upper() != "D:" or folder.parent != expected_parent:
        raise AcquisitionError("Resume folder must be a direct child of D:\\data\\Codex\\credit-atlas\\data\\private\\hmda")
    receipt_path = folder / "acquisition-failed.json"
    if not receipt_path.is_file():
        raise AcquisitionError("Resume requires an acquisition-failed.json receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "ACQUISITION_OR_AUDIT_FAILED" or receipt.get("source_id") != folder.name:
        raise AcquisitionError("Resume receipt identity/status mismatch")
    payloads = receipt.get("verified_payloads") or {}
    lar = payloads.get("lar")
    if not lar or lar.get("profile", {}).get("summary", {}).get("records", 0) <= 0:
        raise AcquisitionError("No previously verified national LAR is available to resume")
    lar_archive = folder / DATASETS["lar"]["filename"]
    lar_csv = folder / "extracted" / lar["csv"]["member"]
    if sha256(lar_archive) != lar["archive"]["sha256"] or sha256(lar_csv) != lar["csv"]["sha256"]:
        raise AcquisitionError("Previously audited LAR files changed since failure receipt")
    with zipfile.ZipFile(lar_archive) as archive:
        if archive.testzip() is not None:
            raise AcquisitionError("Previously audited LAR archive CRC no longer passes")
    for name in ("ts", "msamd"):
        if name not in payloads:
            config = DATASETS[name]
            archive_path = folder / config["filename"]
            if archive_path.exists():
                # This can occur when GET succeeded but CSV extraction failed.
                metadata = request_headers(config["url"])
                if archive_path.stat().st_size != metadata["content_length"]:
                    raise AcquisitionError(f"Existing {name} archive differs from official Content-Length")
                with zipfile.ZipFile(archive_path) as archive:
                    if archive.testzip() is not None:
                        raise AcquisitionError(f"Existing {name} archive CRC failed")
                item = {"url": config["url"], "file": archive_path.name, "http_status": 200,
                        "content_type": metadata["content_type"], "bytes": archive_path.stat().st_size,
                        "last_modified": metadata["last_modified"], "etag": metadata["etag"],
                        "sha256": sha256(archive_path), "retrieved_unix": int(time.time())}
            else:
                item = download(config["url"], archive_path, config["max_bytes"])
            payloads[name] = audit_csv(root, folder, name)
            payloads[name]["http"] = item
    validate_cross_dataset(payloads)
    reporters = payloads["lar"]["profile"]["summary"]["distinct_reporting_LEIs"]
    result = {"source_id": folder.name, "status": "VERIFIED_HMDA_NATIONAL_SNAPSHOT_2025",
              "publisher": "FFIEC / Consumer Financial Protection Bureau",
              "source_page": SOURCE_PAGE, "press_release": PRESS_RELEASE,
              "frontend_source": FRONTEND_SOURCE, "snapshot_freeze_date": "2026-06-02",
              "release_summary_reporters": 4782, "distinct_LEIs_in_LAR": reporters,
              "reporter_count_match": reporters == 4782,
              "retrieved_at_unix": int(time.time()), "datasets": payloads,
              "visibility": "private", "public_release_approved": False,
              "loan_performance_labels": False, "forecast_or_imputation": False,
              "limitations": [
                  "HMDA LAR records applications and actions, not monthly repayment or default outcomes.",
                  "Public privacy modifications and lack of borrower/loan linkage constrain longitudinal joins.",
                  "2025 snapshot may differ from eventual one-year dataset after later resubmissions.",
                  "This new national source is a separate D08 case and does not qualify D01 Freddie multi-vintage gates.",
              ]}
    output = folder / "acquisition-complete.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--resume-from", type=Path, help="resume a failed acquisition folder without overwriting verified payloads")
    args = parser.parse_args()
    try:
        result = resume(args.root, args.resume_from) if args.resume_from else acquire(args.root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, zipfile.BadZipFile, duckdb.Error, AcquisitionError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
