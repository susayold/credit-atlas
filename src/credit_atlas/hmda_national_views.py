"""Private aggregate view for the official 2025 national HMDA snapshot."""
from __future__ import annotations

import json
import hashlib
import re
import shutil
import zipfile
from decimal import Decimal
from pathlib import Path

import duckdb

from .workspace import contained, read_json, sha256, timestamp, write_new

SOURCE_PATTERN = re.compile(r"hmda-national-(?:snapshot-2025-[0-9a-f]{12}|dynamic-2025-20261011)\Z")
VIEW_PATTERN = re.compile(r"hmda-national-view-[0-9a-f]{12}\Z")
DATASET_PAGE = "https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2025"
LAR_URL = "https://files.ffiec.cfpb.gov/static-data/snapshot/2025/2025_public_lar_csv.zip"
DIMENSIONS = {
    "state_code": "State / territory",
    "county_code": "County FIPS",
    "lei": "Reporting institution LEI",
    "loan_type": "Loan type",
    "loan_purpose": "Loan purpose",
    "lien_status": "Lien status",
    "occupancy_type": "Occupancy type",
    "derived_dwelling_category": "Derived dwelling category",
    "debt_to_income_ratio": "Public DTI category",
    "derived_race": "Derived race",
    "derived_ethnicity": "Derived ethnicity",
    "derived_sex": "Derived sex",
    "applicant_credit_score_type": "Applicant score-model type",
    "denial_reason_1": "Primary denial reason (action 3 only)",
}
REQUIRED_FIELDS = {
    "activity_year", "lei", "state_code", "county_code", "action_taken", "loan_type",
    "loan_purpose", "lien_status", "occupancy_type", "derived_dwelling_category",
    "debt_to_income_ratio", "derived_race", "derived_ethnicity", "derived_sex",
    "applicant_credit_score_type", "denial_reason_1", "loan_amount",
}


def methods():
    return {name: sha256(Path(__file__).with_name(name + ".py"))
            for name in ("hmda_national_views", "workspace")}


def source_folder(root: Path, source_id: str) -> Path:
    if not isinstance(source_id, str) or not SOURCE_PATTERN.fullmatch(source_id):
        raise ValueError("Invalid HMDA national source id")
    return contained(root, "data/private/hmda/" + source_id)


def verify_source(root: Path, source_id: str, *, hash_payloads: bool = True):
    folder = source_folder(root, source_id)
    receipt_path = contained(folder, "acquisition-complete.json")
    receipt = read_json(receipt_path)
    if source_id.startswith("hmda-national-dynamic-"):
        return _verify_dynamic_source(folder, source_id, receipt_path, receipt, hash_payloads)
    if (receipt.get("source_id") != source_id
            or receipt.get("status") != "VERIFIED_HMDA_NATIONAL_SNAPSHOT_2025"
            or receipt.get("publisher") != "FFIEC / Consumer Financial Protection Bureau"
            or receipt.get("source_page") != DATASET_PAGE
            or receipt.get("snapshot_freeze_date") != "2026-06-02"
            or receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False
            or receipt.get("loan_performance_labels") is not False
            or receipt.get("forecast_or_imputation") is not False):
        raise ValueError("HMDA national source receipt contract changed")
    datasets = receipt.get("datasets")
    if not isinstance(datasets, dict) or set(datasets) != {"lar", "ts", "msamd"}:
        raise ValueError("HMDA national source datasets are incomplete")
    expected_url = {"lar": LAR_URL,
        "ts": "https://files.ffiec.cfpb.gov/static-data/snapshot/2025/2025_public_ts_csv.zip",
        "msamd": "https://files.ffiec.cfpb.gov/static-data/snapshot/2025/2025_public_msamd_csv.zip"}
    paths = []
    for key, item in datasets.items():
        archive_path = contained(folder, item["archive"]["file"])
        csv_path = contained(folder, "extracted/" + item["csv"]["member"])
        if (item.get("http", {}).get("url") != expected_url[key]
                or archive_path.stat().st_size != item["archive"]["bytes"]
                or csv_path.stat().st_size != item["csv"]["bytes"]):
            raise ValueError("HMDA national payload identity or size changed")
        if hash_payloads and (sha256(archive_path) != item["archive"]["sha256"]
                or sha256(csv_path) != item["csv"]["sha256"]):
            raise ValueError("HMDA national source payload hash changed")
        paths.extend((archive_path, csv_path))
    profile = datasets["lar"].get("profile", {})
    summary = profile.get("summary", {})
    if (len(profile.get("columns", [])) != 99 or not REQUIRED_FIELDS.issubset(profile.get("columns", []))
            or summary.get("records") != 13_543_606
            or summary.get("distinct_reporting_LEIs") != 4_782
            or summary.get("wrong_year_rows") != 0
            or summary.get("invalid_action_rows") != 0
            or summary.get("invalid_state_rows") != 0
            or summary.get("invalid_loan_type_rows") != 0
            or summary.get("invalid_lei_rows") != 0):
        raise ValueError("HMDA national LAR profile contract changed")
    ts_summary = datasets["ts"].get("profile", {}).get("summary", {})
    if (ts_summary.get("records") != 4_782 or ts_summary.get("distinct_keys") != 4_782
            or ts_summary.get("sum_reported_lar_count") != summary["records"]):
        raise ValueError("HMDA Transmittal Sheet does not reconcile to LAR")
    return folder, receipt, receipt_path, paths


def _verify_dynamic_source(folder, source_id, receipt_path, receipt, hash_payloads):
    source_page = "https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset/2025"
    if (receipt.get("source_id") != source_id
            or receipt.get("status") != "VERIFIED_HMDA_2025_DYNAMIC_AS_OF_2026_10_11"
            or receipt.get("publisher") != "FFIEC / Consumer Financial Protection Bureau"
            or receipt.get("source_page") != source_page
            or receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False
            or receipt.get("loan_performance_labels") is not False
            or receipt.get("forecast_or_imputation") is not False):
        raise ValueError("HMDA dynamic acquisition receipt contract changed")
    datasets = receipt.get("datasets")
    if not isinstance(datasets, dict) or set(datasets) != {"lar", "ts"}:
        raise ValueError("HMDA dynamic source datasets are incomplete")
    expected = {
        "lar": ("https://files.ffiec.cfpb.gov/dynamic-data/2025/2025_lar.zip", "2025_lar.zip", "2025_lar.txt"),
        "ts": ("https://files.ffiec.cfpb.gov/dynamic-data/2025/2025_ts.zip", "2025_ts.zip", "2025_ts.txt"),
    }
    paths = []
    for key, (url, filename, member) in expected.items():
        item = datasets[key]
        archive_path = contained(folder, filename)
        http = item.get("http", {})
        if (http.get("url") != url or http.get("last_modified") != receipt.get("release_as_of_utc", {}).get(key)
                or archive_path.stat().st_size != http.get("bytes")
                or item.get("csv", {}).get("member") != member):
            raise ValueError("HMDA dynamic archive identity or size changed")
        if hash_payloads and sha256(archive_path) != item.get("archive_sha256"):
            raise ValueError("HMDA dynamic source archive hash changed")
        with zipfile.ZipFile(archive_path) as archive:
            members = [entry for entry in archive.infolist() if not entry.is_dir()]
            if len(members) != 1 or members[0].filename != member:
                raise ValueError("HMDA dynamic source archive layout changed")
            if members[0].file_size != item["csv"].get("uncompressed_bytes"):
                raise ValueError("HMDA dynamic member size changed")
            if hash_payloads and archive.testzip() is not None:
                raise ValueError("HMDA dynamic source ZIP CRC failed")
        paths.append(archive_path)
    profile = datasets["lar"].get("profile", {})
    summary = profile.get("summary", {})
    if (len(profile.get("columns", [])) != 99 or not REQUIRED_FIELDS.issubset(profile.get("columns", []))
            or summary.get("records") != 13_558_306 or summary.get("distinct_LEIs") != 4_794
            or any(summary.get(key) != 0 for key in ("wrong_year_rows", "invalid_action_rows", "invalid_state_rows",
                "invalid_loan_type_rows", "invalid_lei_rows", "invalid_loan_amount_rows"))):
        raise ValueError("HMDA dynamic LAR profile contract changed")
    ts_summary = datasets["ts"].get("profile", {}).get("summary", {})
    if (ts_summary.get("records") != 4_794 or ts_summary.get("unique_LEIs") != 4_794
            or ts_summary.get("sum_reported_lar_count") != summary["records"]):
        raise ValueError("HMDA dynamic Transmittal Sheet does not reconcile to LAR")
    return folder, receipt, receipt_path, paths


def _category(field):
    return f"COALESCE(NULLIF({field}, ''), '(SOURCE_BLANK)')"


def aggregate_csv(path: Path, temp_root: Path | None = None, *, delimiter: str = ",") -> dict:
    """Read one frozen LAR and aggregate multiple dimensions in one DuckDB scan."""
    path = path.resolve()
    temp_root = (temp_root or path.parent).resolve()
    temp_dir = temp_root / "duckdb-national-temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    connection.execute("SET memory_limit='3GB'")
    connection.execute("SET threads=4")
    connection.execute("SET temp_directory=?", [str(temp_dir)])
    if delimiter not in {",", "|"}:
        raise ValueError("Unsupported HMDA source delimiter")
    relation = f"read_csv(?, delim='{delimiter}', header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = [row[0] for row in connection.execute(f"DESCRIBE SELECT * FROM {relation}", [str(path)]).fetchall()]
        if len(columns) != 99 or len(set(columns)) != 99 or not REQUIRED_FIELDS.issubset(columns):
            raise ValueError("National HMDA 2025 public LAR schema contract failed")

        groups = [(field,) for field in DIMENSIONS if field != "denial_reason_1"]
        groups.append(("denial_reason_1",))
        cases = []
        value_cases = []
        for field, label in DIMENSIONS.items():
            cases.append(f"WHEN GROUPING({field})=0 THEN '{field}'")
            value_cases.append(f"WHEN GROUPING({field})=0 THEN {_category(field)}")
        grouping_sql = ",".join("(" + ",".join(group) + ")" for group in groups)
        sql = f"""
            SELECT CASE {' '.join(cases)} ELSE 'action_taken' END AS dimension,
                   CASE {' '.join(value_cases)}
                        WHEN GROUPING(action_taken)=0 THEN action_taken ELSE '' END AS bucket,
                   count(*) AS records,
                   count(*) FILTER (WHERE action_taken IN ('1','2','3')) AS decision_denominator,
                   count(*) FILTER (WHERE action_taken='3') AS denied_numerator,
                   sum(try_cast(loan_amount AS DECIMAL(38,2))) AS public_amount_sum_usd,
                   count(*) FILTER (WHERE activity_year <> '2025' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL) AS invalid_action_rows,
                   count(*) FILTER (WHERE try_cast(loan_amount AS DECIMAL(38,2)) IS NULL) AS invalid_amount_rows
            FROM {relation}
            GROUP BY GROUPING SETS ({grouping_sql}, (action_taken))
        """
        rows = connection.execute(sql, [str(path)]).fetchall()
        result = {"columns": columns, "actions": [], "summary": None,
                  "breakdowns": {key: [] for key in DIMENSIONS}, "quality": {}}
        action_counts = {}
        for dimension, bucket, records, denominator, denied, amount, wrong_year, invalid_action, invalid_amount in rows:
            if dimension == "action_taken":
                action_counts[bucket] = records
                continue
            item = {"bucket": bucket, "records": records,
                    "decision_denominator": denominator, "denied_numerator": denied,
                    "descriptive_denial_rate": (str(denied / denominator) if denominator else None),
                    "public_amount_sum_usd": str(amount or 0)}
            if dimension == "denial_reason_1":
                # Report a reason only among action 3 rows; it is not a PD input.
                item["records"] = denied
                item["decision_denominator"] = None
                item["denied_numerator"] = denied
                item["descriptive_denial_rate"] = None
                item["public_amount_sum_usd"] = None
                item["denied_reason_records"] = denied
                item["denominator_kind"] = "action_3_applications"
            result["breakdowns"][dimension].append(item)
        if not action_counts or set(action_counts) - set("12345678"):
            raise ValueError("National HMDA action distribution is incomplete or invalid")
        order = {str(code): name for code, name in enumerate(("ORIGINATED", "APPROVED_NOT_ACCEPTED", "DENIED",
            "WITHDRAWN", "CLOSED_INCOMPLETE", "PURCHASED_LOAN", "PREAPPROVAL_DENIED", "PREAPPROVAL_APPROVED_NOT_ACCEPTED"), 1)}
        result["actions"] = [{"code": code, "name": order[code], "records": action_counts[code]}
                              for code in sorted(action_counts)]
        total = sum(action_counts.values())
        decided = sum(action_counts.get(code, 0) for code in ("1", "2", "3"))
        denied = action_counts.get("3", 0)
        result["summary"] = {"records": total, "reporters": None,
            "decision_denominator": decided, "denied_numerator": denied,
            "descriptive_denial_rate": str(denied / decided) if decided else None,
            "public_amount_sum_usd": str(sum(Decimal(item["public_amount_sum_usd"])
                for item in result["breakdowns"]["state_code"]))}
        result["quality"] = {"wrong_year_rows": max((row[6] for row in rows), default=0),
            "invalid_action_rows": max((row[7] for row in rows), default=0),
            "invalid_amount_rows": max((row[8] for row in rows), default=0)}
        if total <= 0 or result["quality"] != {"wrong_year_rows": 0, "invalid_action_rows": 0, "invalid_amount_rows": 0}:
            raise ValueError("National HMDA row quality checks failed")
        # For denial reasons, denominator is all action-3 records with a value
        # (including source blank as its own reported category); never use all
        # applications as a reason denominator.
        for field, values in result["breakdowns"].items():
            values.sort(key=lambda row: (-row.get("denied_reason_records", row["records"]), row["bucket"]))
        result["breakdowns"]["denial_reason_1"] = [row for row in result["breakdowns"]["denial_reason_1"]
            if row["denied_reason_records"] > 0]
        return result
    finally:
        connection.close()


def build_view(root: Path, source_id: str) -> dict:
    root = root.resolve()
    source, source_receipt, source_receipt_path, pinned_paths = verify_source(root, source_id)
    source_digest = sha256(source_receipt_path)
    dynamic = source_id.startswith("hmda-national-dynamic-")
    identifier_seed = json.dumps({"source_receipt": source_digest, "methods": methods()}, sort_keys=True)
    identifier = "hmda-national-view-" + hashlib.sha256(identifier_seed.encode()).hexdigest()[:12]
    folder = contained(root, "artifacts/private/" + identifier)
    if folder.exists():
        raise ValueError("HMDA national aggregate view already exists; verify/reuse it")
    folder.mkdir(parents=True)
    frozen = methods()
    extract_dir = None
    if dynamic:
        extract_dir = folder / "source-input"
        extract_dir.mkdir()
        archive_path = pinned_paths[0]
        with zipfile.ZipFile(archive_path) as archive:
            member = archive.getinfo("2025_lar.txt")
            source_csv = extract_dir / "2025_lar.txt"
            with archive.open(member) as src, source_csv.open("xb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
        if source_csv.stat().st_size != source_receipt["datasets"]["lar"]["csv"]["uncompressed_bytes"]:
            raise ValueError("HMDA dynamic LAR extraction size differs from acquisition receipt")
        payload = aggregate_csv(source_csv, folder, delimiter="|")
        shutil.rmtree(extract_dir)
    else:
        source_csv = contained(source, "extracted/2025_public_lar_csv.csv")
        payload = aggregate_csv(source_csv, folder)
    profile = source_receipt["datasets"]["lar"]["profile"]["summary"]
    reporter_count = profile["distinct_LEIs"] if dynamic else profile["distinct_reporting_LEIs"]
    payload["summary"]["reporters"] = reporter_count
    action_rows = source_receipt["datasets"]["lar"]["profile"]["actions"]
    expected_actions = ({row["code"]: row["records"] for row in action_rows} if dynamic
                        else {row["value"]: row["records"] for row in action_rows})
    actual_actions = {row["code"]: row["records"] for row in payload["actions"]}
    if (payload["summary"]["records"] != profile["records"]
            or actual_actions != expected_actions
            or payload["summary"]["reporters"] != reporter_count):
        raise ValueError("National HMDA aggregate does not reconcile to acquisition receipt")
    snapshot_date = "2026-10-11" if dynamic else "2026-06-02"
    source_url = ("https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset/2025"
                  if dynamic else DATASET_PAGE)
    payload.update({"view_id": identifier, "source_id": source_id,
        "snapshot_date": snapshot_date, "release_type": "dynamic weekly snapshot" if dynamic else "static snapshot",
        "activity_year": 2025, "source_url": source_url,
        "dimensions": DIMENSIONS,
        "scope": "United States nationwide 2025 public HMDA LAR snapshot; all actions retained",
        "limitations": [
            "This dataset records applications, underwriting actions, and purchased loans; it is not monthly repayment or default performance.",
            "The 22.59% denied share is action 3 divided by actions 1-3; it is not PD, delinquency, or default.",
            "Public values are privacy-modified; no borrower/loan-level performance linkage is established.",
            "Credit-score field indicates score-model type, not the numerical score.",
            "Public loan amounts are published interval midpoints; sums are not exact funded cash.",
            ("Dynamic file captured October 11, 2026; it is a dated copy of a mutable weekly source." if dynamic
             else "Snapshot is frozen June 2, 2026 and may differ from later one-year/dynamic releases after resubmissions."),
            "No forecast, imputation, or model fit was performed.",
        ],
        "denominator_contract": {"codes": ["1", "2", "3"], "numerator": "3",
            "meaning": "Descriptive denied share among originated + approved-not-accepted + denied; not default PD."},
        "visibility": "private", "public_release_approved": False})
    output = folder / "aggregates.json"
    write_new(output, payload)
    if methods() != frozen or sha256(source_receipt_path) != source_digest:
        raise ValueError("HMDA national source or methods changed during aggregate build")
    for path in pinned_paths:
        if not path.is_file():
            raise ValueError("HMDA national source payload disappeared during aggregate build")
    receipt = {"view_id": identifier, "source_id": source_id,
        "status": "VERIFIED_HMDA_NATIONAL_AGGREGATE_VIEW", "completed_at": timestamp(),
        "source_receipt_sha256": source_digest, "aggregate_sha256": sha256(output),
        "methods": frozen, "visibility": "private", "public_release_approved": False}
    write_new(folder / "view-complete.json", receipt)
    return receipt


class HmdaNationalViews:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._source_cache = {}
        self._views = {}
        self._methods = methods()

    def _view(self, identifier):
        if not isinstance(identifier, str) or not VIEW_PATTERN.fullmatch(identifier):
            raise ValueError("Invalid HMDA national view id")
        if methods() != self._methods:
            raise ValueError("HMDA national serving methods changed; restart required")
        folder = contained(self.root, "artifacts/private/" + identifier)
        receipt_path = contained(folder, "view-complete.json")
        receipt = read_json(receipt_path)
        if (receipt.get("view_id") != identifier
                or receipt.get("status") != "VERIFIED_HMDA_NATIONAL_AGGREGATE_VIEW"
                or receipt.get("methods") != self._methods
                or receipt.get("visibility") != "private"
                or receipt.get("public_release_approved") is not False):
            raise ValueError("HMDA national aggregate receipt contract changed")
        source_id = receipt.get("source_id")
        source, source_receipt, source_receipt_path, pinned_paths = verify_source(self.root, source_id, hash_payloads=False)
        if sha256(source_receipt_path) != receipt.get("source_receipt_sha256"):
            raise ValueError("HMDA national acquisition receipt changed")
        stat_key = tuple((str(path), path.stat().st_size, path.stat().st_mtime_ns) for path in pinned_paths)
        if source_id not in self._source_cache:
            verify_source(self.root, source_id, hash_payloads=True)
            self._source_cache[source_id] = stat_key
        elif self._source_cache[source_id] != stat_key:
            raise ValueError("HMDA national source payload metadata changed; restart/re-audit required")
        aggregate_path = contained(folder, "aggregates.json")
        if sha256(aggregate_path) != receipt.get("aggregate_sha256"):
            raise ValueError("HMDA national aggregates changed")
        payload = read_json(aggregate_path)
        if (payload.get("view_id") != identifier or payload.get("source_id") != source_id
                or payload.get("visibility") != "private" or payload.get("public_release_approved") is not False
                or payload.get("summary", {}).get("records") != source_receipt["datasets"]["lar"]["profile"]["summary"]["records"]
                or set(payload.get("breakdowns", {})) != set(DIMENSIONS)):
            raise ValueError("HMDA national aggregate content contract changed")
        return folder, receipt, payload

    def catalog(self):
        rows = []
        for path in sorted((self.root / "artifacts/private").glob("hmda-national-view-*/view-complete.json")):
            try:
                _, receipt, payload = self._view(path.parent.name)
                rows.append({"view_id": payload["view_id"], "source_id": receipt["source_id"],
                    "status": "verified", "records": payload["summary"]["records"],
                    "snapshot_date": payload["snapshot_date"], "release_type": payload.get("release_type", "static snapshot"),
                    "completed_at": receipt["completed_at"]})
            except (OSError, ValueError, KeyError, TypeError):
                rows.append({"view_id": path.parent.name, "status": "unavailable", "records": None})
        return {"views": rows}

    def view(self, identifier):
        _, _, payload = self._view(identifier)
        result = {key: payload[key] for key in ("view_id", "source_id", "snapshot_date", "activity_year",
            "summary", "actions", "dimensions", "scope", "limitations", "denominator_contract",
            "source_url", "visibility", "public_release_approved")}
        result["release_type"] = payload.get("release_type", "static snapshot")
        return result

    def report(self, identifier, query):
        if not isinstance(query, dict) or set(query) - {"view_id", "dimension"} or query.get("view_id", identifier) != identifier:
            raise ValueError("Invalid HMDA national aggregate query")
        dimension = query.get("dimension", "state_code")
        if not isinstance(dimension, str) or dimension not in DIMENSIONS:
            raise ValueError("Unsupported HMDA national breakdown dimension")
        _, _, payload = self._view(identifier)
        return {"view_id": identifier, "source_id": payload["source_id"],
            "snapshot_date": payload["snapshot_date"], "release_type": payload.get("release_type", "static snapshot"), "activity_year": payload["activity_year"],
            "summary": payload["summary"], "actions": payload["actions"],
            "dimension": dimension, "dimension_label": DIMENSIONS[dimension],
            "breakdown": payload["breakdowns"][dimension], "scope": payload["scope"],
            "limitations": payload["limitations"], "denominator_contract": payload["denominator_contract"],
            "visibility": "private", "public_release_approved": False}


def build_national_view(root: Path, source_id: str):
    return build_view(root, source_id)
