"""Private aggregate view for the official 2021 HMDA One-Year national LAR."""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import duckdb

from .workspace import contained, read_json, sha256, timestamp, write_new

SOURCE_PATTERN = re.compile(r"hmda-national-one-year-2021-[0-9a-f]{12}\Z")
VIEW_PATTERN = re.compile(r"hmda-one-year-2021-view-[0-9a-f]{12}\Z")
SOURCE_PAGE = "https://ffiec.cfpb.gov/data-publication/one-year-national-loan-level-dataset/2021"
API_DOCS = "https://ffiec.cfpb.gov/documentation/api/data-browser/"
CSV_FILE = "2021_public_lar_one_year_csv.csv"
EXPECTED_ACTIONS = {"1": 15_062_966, "2": 634_932, "3": 2_922_414,
    "4": 3_313_356, "5": 1_452_022, "6": 2_691_964, "7": 53_506, "8": 96_204}
VALID_STATE_CODES = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE",
    "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "AS", "GU", "MP", "PR", "VI", "UM", "FM",
    "MH", "PW", "NA"}
DIMENSION_FIELDS = {
    "state_code": ("state_code", "State / territory"),
    "county_code": ("county_code", "County FIPS"),
    "lei": ("lei", "Reporting institution LEI"),
    "loan_type": ("loan_type", "Loan type"),
    "loan_purpose": ("loan_purpose", "Loan purpose"),
    "lien_status": ("lien_status", "Lien status"),
    "occupancy_type": ("occupancy_type", "Occupancy type"),
    "derived_dwelling_category": ("derived_dwelling_category", "Derived dwelling category"),
    "debt_to_income_ratio": ("debt_to_income_ratio", "Public DTI category"),
    "derived_race": ("derived_race", "Derived race"),
    "derived_ethnicity": ("derived_ethnicity", "Derived ethnicity"),
    "derived_sex": ("derived_sex", "Derived sex"),
    "applicant_credit_score_type": ("applicant_credit_score_type", "Applicant score-model type"),
    # HMDA renamed this field between source vintages; preserve the source spelling here.
    "denial_reason_1": ("denial_reason_1", "Primary denial reason (action 3 only)"),
}
DIMENSIONS = {key: value[1] for key, value in DIMENSION_FIELDS.items()}
REQUIRED_FIELDS = {"activity_year", "lei", "state_code", "county_code", "action_taken",
    "loan_type", "loan_purpose", "lien_status", "occupancy_type", "derived_dwelling_category",
    "debt_to_income_ratio", "derived_race", "derived_ethnicity", "derived_sex",
    "applicant_credit_score_type", "denial_reason_1", "loan_amount", "combined_loan_to_value_ratio"}


def methods():
    return {name: sha256(Path(__file__).with_name(name + ".py"))
            for name in ("hmda_one_year_2021_views", "workspace")}


def source_folder(root: Path, source_id: str) -> Path:
    if not isinstance(source_id, str) or not SOURCE_PATTERN.fullmatch(source_id):
        raise ValueError("Invalid 2021 HMDA One-Year source id")
    return contained(root, "data/private/hmda/" + source_id)


def verify_source(root: Path, source_id: str, *, hash_payload: bool = True):
    folder = source_folder(root, source_id)
    receipt_path = contained(folder, "acquisition-complete.json")
    receipt = read_json(receipt_path)
    csv = contained(folder, CSV_FILE)
    profile = receipt.get("profile", {})
    summary = profile.get("summary", {})
    csv_meta = receipt.get("csv", {})
    archive = contained(folder, "2021_public_lar_one_year_csv.zip")
    if (receipt.get("source_id") != source_id
            or receipt.get("status") != "VERIFIED_HMDA_2021_ONE_YEAR_NATIONAL"
            or receipt.get("publisher") != "FFIEC / Consumer Financial Protection Bureau"
            or receipt.get("data_page") != SOURCE_PAGE
            or receipt.get("requested_activity_year") != 2021
            or receipt.get("dataset_type") != "One-Year National Loan-Level Dataset; static 12-month post-deadline resubmission vintage"
            or receipt.get("freeze_date") != "2023-05-01"
            or receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False
            or receipt.get("loan_performance_labels") is not False
            or receipt.get("forecast_or_imputation") is not False
            or not REQUIRED_FIELDS.issubset(profile.get("columns", []))
            or len(profile.get("columns", [])) != 99
            or summary.get("records") != sum(EXPECTED_ACTIONS.values())
            or summary.get("distinct_leis") != 4_368
            or any(summary.get(key) != 0 for key in ("wrong_year_rows", "invalid_action_rows", "invalid_state_rows",
                "invalid_loan_type_rows", "invalid_lei_rows", "invalid_amount_rows"))
            or csv_meta.get("file") != CSV_FILE
            or csv_meta.get("sha256", "")[:12] != source_id[-12:]
            or not csv.is_file()
            or csv.stat().st_size != 10_212_571_276
            or not archive.is_file()
            or archive.stat().st_size != 1_518_888_317
            or archive.stat().st_size != receipt.get("archive", {}).get("bytes")
            or sha256(archive) != receipt.get("archive", {}).get("sha256")
            ):
        raise ValueError("HMDA 2021 One-Year source receipt contract changed")
    raw_actions = profile.get("actions", {})
    action_counts = ({str(code): count for code, count in raw_actions.items()}
        if isinstance(raw_actions, dict) else
        {row["value"]: row["records"] for row in raw_actions})
    if action_counts != EXPECTED_ACTIONS:
        raise ValueError("HMDA 2021 One-Year source action profile changed")
    if hash_payload and sha256(csv) != csv_meta.get("sha256"):
        raise ValueError("HMDA 2021 One-Year source CSV hash changed")
    return folder, receipt, receipt_path, csv


def _quoted(field: str) -> str:
    return '"' + field.replace('"', '""') + '"'


def aggregate_csv(path: Path, temp_root: Path | None = None) -> dict:
    path = path.resolve()
    temp_root = (temp_root or path.parent).resolve()
    temp_dir = temp_root / "duckdb-hmda-one-year-temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    connection.execute("SET memory_limit='3GB'")
    connection.execute("SET threads=4")
    connection.execute("SET temp_directory=?", [str(temp_dir)])
    relation = "read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = [row[0] for row in connection.execute(f"DESCRIBE SELECT * FROM {relation}", [str(path)]).fetchall()]
        if len(columns) != 99 or len(set(columns)) != 99 or not REQUIRED_FIELDS.issubset(columns):
            raise ValueError("HMDA 2021 One-Year public LAR schema contract failed")
        source_fields = {key: value[0] for key, value in DIMENSION_FIELDS.items()}
        group_fields = [(source_fields[key], key) for key in DIMENSIONS if key != "denial_reason_1"]
        groups = [field for field, _ in group_fields] + [source_fields["denial_reason_1"]]
        cases = " ".join(f"WHEN GROUPING({_quoted(field)})=0 THEN '{key}'" for field, key in group_fields)
        cases += f" WHEN GROUPING({_quoted(source_fields['denial_reason_1'])})=0 THEN 'denial_reason_1'"
        value_cases = " ".join(f"WHEN GROUPING({_quoted(field)})=0 THEN COALESCE(NULLIF({_quoted(field)}, ''), '(SOURCE_BLANK)')"
            for field, _ in group_fields)
        value_cases += f" WHEN GROUPING({_quoted(source_fields['denial_reason_1'])})=0 THEN COALESCE(NULLIF({_quoted(source_fields['denial_reason_1'])}, ''), '(SOURCE_BLANK)')"
        grouping_sets = ",".join("(" + _quoted(field) + ")" for field in groups)
        sql = f"""
            SELECT CASE {cases} ELSE 'action_taken' END AS dimension,
                   CASE {value_cases} WHEN GROUPING(action_taken)=0 THEN action_taken ELSE '' END AS bucket,
                   count(*) AS records,
                   count(*) FILTER (WHERE action_taken IN ('1','2','3')) AS decision_denominator,
                   count(*) FILTER (WHERE action_taken='3') AS denied_numerator,
                   sum(try_cast(loan_amount AS DECIMAL(38,2))) AS public_amount_sum_usd,
                   count(*) FILTER (WHERE activity_year <> '2021' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL) AS invalid_action_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR state_code NOT IN ({','.join(repr(code) for code in sorted(VALID_STATE_CODES))})) AS invalid_state_rows,
                   count(*) FILTER (WHERE loan_type NOT IN ('1','2','3','4') OR loan_type IS NULL) AS invalid_loan_type_rows,
                   count(*) FILTER (WHERE lei IS NULL OR lei = '' OR NOT regexp_matches(lei, '^[A-Z0-9]{{20}}$')) AS invalid_lei_rows,
                   count(*) FILTER (WHERE try_cast(loan_amount AS DECIMAL(38,2)) IS NULL) AS invalid_amount_rows
            FROM {relation}
            GROUP BY GROUPING SETS ({grouping_sets}, (action_taken))
        """
        rows = connection.execute(sql, [str(path)]).fetchall()
        result = {"columns": columns, "actions": [], "summary": None,
            "breakdowns": {key: [] for key in DIMENSIONS}, "quality": {}}
        action_counts = {}
        for dimension, bucket, records, denominator, denied, amount, wrong_year, invalid_action, invalid_state, invalid_loan_type, invalid_lei, invalid_amount in rows:
            if dimension == "action_taken":
                action_counts[bucket] = records
                continue
            item = {"bucket": bucket, "records": records, "decision_denominator": denominator,
                "denied_numerator": denied,
                "descriptive_denial_rate": str(denied / denominator) if denominator else None,
                "public_amount_sum_usd": str(amount or 0)}
            if dimension == "denial_reason_1":
                item.update({"records": denied, "decision_denominator": None,
                    "denied_numerator": denied, "descriptive_denial_rate": None,
                    "public_amount_sum_usd": None, "denied_reason_records": denied,
                    "denominator_kind": "action_3_applications"})
            result["breakdowns"][dimension].append(item)
        if action_counts != EXPECTED_ACTIONS:
            raise ValueError("HMDA 2021 One-Year action distribution does not reconcile to official API")
        total = sum(action_counts.values())
        decided = sum(action_counts.get(code, 0) for code in ("1", "2", "3"))
        denied = action_counts.get("3", 0)
        result["actions"] = [{"code": code, "records": action_counts[code]} for code in sorted(action_counts)]
        result["summary"] = {"records": total, "reporters": None, "decision_denominator": decided,
            "denied_numerator": denied, "descriptive_denial_rate": str(denied / decided),
            "public_amount_sum_usd": str(sum(Decimal(row["public_amount_sum_usd"])
                for row in result["breakdowns"]["state_code"]))}
        result["quality"] = {"wrong_year_rows": max((row[6] for row in rows), default=0),
            "invalid_action_rows": max((row[7] for row in rows), default=0),
            "invalid_state_rows": max((row[8] for row in rows), default=0),
            "invalid_loan_type_rows": max((row[9] for row in rows), default=0),
            "invalid_lei_rows": max((row[10] for row in rows), default=0),
            "invalid_amount_rows": max((row[11] for row in rows), default=0)}
        if result["quality"] != {"wrong_year_rows": 0, "invalid_action_rows": 0, "invalid_state_rows": 0,
                "invalid_loan_type_rows": 0, "invalid_lei_rows": 0, "invalid_amount_rows": 0}:
            raise ValueError("HMDA 2021 One-Year aggregate row quality checks failed")
        for values in result["breakdowns"].values():
            values.sort(key=lambda row: (-row.get("denied_reason_records", row["records"]), row["bucket"]))
        result["breakdowns"]["denial_reason_1"] = [row for row in result["breakdowns"]["denial_reason_1"]
            if row["denied_reason_records"] > 0]
        return result
    finally:
        connection.close()


def build_view(root: Path, source_id: str) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("Private HMDA aggregates must remain on D:")
    source, source_receipt, source_receipt_path, csv = verify_source(root, source_id)
    source_digest = sha256(source_receipt_path)
    identifier = "hmda-one-year-2021-view-" + source_id[-12:]
    folder = contained(root, "artifacts/private/" + identifier)
    if folder.exists():
        raise ValueError("HMDA 2021 aggregate view already exists; verify/reuse it")
    folder.mkdir(parents=True)
    frozen = methods()
    payload = aggregate_csv(csv, folder)
    profile = source_receipt["profile"]["summary"]
    payload["summary"]["reporters"] = profile["distinct_leis"]
    if (payload["summary"]["records"] != profile["records"]
            or {row["code"]: row["records"] for row in payload["actions"]} != EXPECTED_ACTIONS
            or payload["summary"]["reporters"] != profile["distinct_leis"]):
        raise ValueError("HMDA 2021 aggregate does not reconcile to acquisition receipt")
    payload.update({"view_id": identifier, "source_id": source_id,
        "activity_year": 2021, "release_type": "One-Year National Dataset",
        "freeze_date": "2023-05-01", "source_url": SOURCE_PAGE, "api_docs_url": API_DOCS,
        "dimensions": DIMENSIONS,
        "scope": "United States nationwide 2021 HMDA LAR; official One-Year post-deadline resubmission release; all actions retained.",
        "limitations": [
            "This release records applications, underwriting actions, and purchased loans; it has no monthly repayment, delinquency, default, loss, or recovery outcomes.",
            "The denied share is action 3 divided by actions 1â€“3; it is an application-decision statistic, not PD, delinquency, or default.",
            "The public file is privacy-modified and does not establish a borrower/loan-level link to Freddie, Fannie, or Ginnie performance panels.",
            "This 2021 One-Year release is distinct from the 2025 Snapshot release; differences may reflect release design and resubmissions as well as year-to-year change.",
            "Credit-score fields describe score-model type, not the applicant's numerical score.",
            "No forecast, imputation, or model fit was performed.",
        ],
        "denominator_contract": {"codes": ["1", "2", "3"], "numerator": "3",
            "meaning": "Descriptive denied share among originated + approved-not-accepted + denied; not default PD."},
        "visibility": "private", "public_release_approved": False})
    output = contained(folder, "aggregates.json")
    write_new(output, payload)
    if methods() != frozen or sha256(source_receipt_path) != source_digest or not csv.is_file():
        raise ValueError("HMDA 2021 source or aggregate methods changed during build")
    receipt = {"view_id": identifier, "source_id": source_id,
        "status": "VERIFIED_HMDA_2021_ONE_YEAR_AGGREGATE_VIEW", "completed_at": timestamp(),
        "source_receipt_sha256": source_digest, "source_csv_sha256": source_receipt["csv"]["sha256"],
        "aggregate_sha256": sha256(output), "methods": frozen,
        "visibility": "private", "public_release_approved": False}
    write_new(folder / "view-complete.json", receipt)
    return receipt


class HmdaOneYear2021Views:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._methods = methods()
        self._source_cache = {}

    def _view(self, identifier):
        if not isinstance(identifier, str) or not VIEW_PATTERN.fullmatch(identifier):
            raise ValueError("Invalid 2021 HMDA One-Year view id")
        if methods() != self._methods:
            raise ValueError("HMDA 2021 serving methods changed; restart required")
        folder = contained(self.root, "artifacts/private/" + identifier)
        receipt = read_json(contained(folder, "view-complete.json"))
        if (receipt.get("view_id") != identifier
                or receipt.get("status") != "VERIFIED_HMDA_2021_ONE_YEAR_AGGREGATE_VIEW"
                or receipt.get("methods") != self._methods
                or receipt.get("visibility") != "private"
                or receipt.get("public_release_approved") is not False):
            raise ValueError("HMDA 2021 aggregate receipt contract changed")
        source_id = receipt.get("source_id")
        _, _, source_receipt_path, csv = verify_source(self.root, source_id, hash_payload=False)
        stat_key = (str(csv), csv.stat().st_size, csv.stat().st_mtime_ns)
        if sha256(source_receipt_path) != receipt.get("source_receipt_sha256"):
            raise ValueError("HMDA 2021 acquisition receipt or source digest changed")
        if source_id not in self._source_cache:
            if sha256(csv) != receipt.get("source_csv_sha256"):
                raise ValueError("HMDA 2021 source CSV hash changed")
            self._source_cache[source_id] = stat_key
        elif self._source_cache[source_id] != stat_key:
            raise ValueError("HMDA 2021 source CSV metadata changed; restart/re-audit required")
        aggregate_path = contained(folder, "aggregates.json")
        if sha256(aggregate_path) != receipt.get("aggregate_sha256"):
            raise ValueError("HMDA 2021 aggregates changed")
        payload = read_json(aggregate_path)
        if (payload.get("view_id") != identifier or payload.get("source_id") != source_id
                or payload.get("activity_year") != 2021 or payload.get("visibility") != "private"
                or payload.get("public_release_approved") is not False
                or payload.get("summary", {}).get("records") != sum(EXPECTED_ACTIONS.values())
                or set(payload.get("breakdowns", {})) != set(DIMENSIONS)):
            raise ValueError("HMDA 2021 aggregate content contract changed")
        return folder, receipt, payload

    def catalog(self):
        rows = []
        for path in sorted((self.root / "artifacts/private").glob("hmda-one-year-2021-view-*/view-complete.json")):
            try:
                _, receipt, payload = self._view(path.parent.name)
                rows.append({"view_id": payload["view_id"], "source_id": receipt["source_id"],
                    "status": "verified", "records": payload["summary"]["records"],
                    "activity_year": 2021, "release_type": payload["release_type"],
                    "freeze_date": payload["freeze_date"]})
            except (OSError, ValueError, KeyError, TypeError):
                rows.append({"view_id": path.parent.name, "status": "unavailable", "records": None})
        return {"views": rows}

    def view(self, identifier):
        _, _, payload = self._view(identifier)
        return {key: payload[key] for key in ("view_id", "source_id", "activity_year", "release_type",
            "freeze_date", "summary", "actions", "dimensions", "scope", "limitations",
            "denominator_contract", "source_url", "api_docs_url", "visibility", "public_release_approved")}

    def report(self, identifier, query):
        if not isinstance(query, dict) or set(query) - {"view_id", "dimension"} or query.get("view_id", identifier) != identifier:
            raise ValueError("Invalid HMDA 2021 aggregate query")
        dimension = query.get("dimension", "state_code")
        if not isinstance(dimension, str) or dimension not in DIMENSIONS:
            raise ValueError("Unsupported HMDA 2021 breakdown dimension")
        _, _, payload = self._view(identifier)
        return {"view_id": payload["view_id"], "source_id": payload["source_id"],
            "activity_year": 2021, "release_type": payload["release_type"], "freeze_date": payload["freeze_date"],
            "summary": payload["summary"], "actions": payload["actions"],
            "dimension": dimension, "dimension_label": DIMENSIONS[dimension],
            "breakdown": payload["breakdowns"][dimension], "scope": payload["scope"],
            "limitations": payload["limitations"], "denominator_contract": payload["denominator_contract"],
            "visibility": "private", "public_release_approved": False}


def build_national_view(root: Path, source_id: str):
    return build_view(root, source_id)
