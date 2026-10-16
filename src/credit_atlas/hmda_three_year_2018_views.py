"""Private, audited aggregate view for HMDA 2018 Three-Year national LAR."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .workspace import contained, read_json, sha256, timestamp, write_new

SOURCE_ID = "hmda-2018-browser-acq-ca2faffa1029"
AUDIT_ID = "hmda-2018-browser-audit-f2f5185955d7"
CSV_NAME = "hmda-2018-three-year-national.csv"
AGGREGATE_INPUT = "artifacts/private/hmda-2018-work/aggregates.json"
SOURCE_PAGE = "https://ffiec.cfpb.gov/data-publication/three-year-national-loan-level-dataset/2018"
API_DOCS = "https://ffiec.cfpb.gov/documentation/api/data-browser/"
EXPECTED_SHA256 = "6b6678ce3c3dc0c640b867b77a10cce3e8ec05e91965e77c44ef0bce4c28c924"
EXPECTED_ACTIONS = {"1": 7_732_289, "2": 338_822, "3": 2_552_640, "4": 1_771_582,
    "5": 554_481, "6": 2_012_221, "7": 101_772, "8": 74_703}
SOURCE_RELATIVE = "data/private/hmda/hmda-browser-three-year-2018"
VIEW_PATTERN = re.compile(r"hmda-three-year-2018-view-[0-9a-f]{12}\Z")
DIMENSIONS = {
    "applicant_credit_score_type": "Applicant score-model type",
    "county_code": "County FIPS code",
    "debt_to_income_ratio": "Public DTI category",
    "derived_dwelling_category": "Derived dwelling category",
    "derived_ethnicity": "Derived ethnicity",
    "derived_race": "Derived race",
    "derived_sex": "Derived sex",
    "denial_reason-1": "Denial reason 1 · action 3 only",
    "denial_reason-2": "Denial reason 2 · action 3 only",
    "denial_reason-3": "Denial reason 3 · action 3 only",
    "denial_reason-4": "Denial reason 4 · action 3 only",
    "lien_status": "Lien status",
    "loan_purpose": "Loan purpose",
    "loan_type": "Loan type",
    "ltv_band": "LTV band · analyst grouped",
    "occupancy_type": "Occupancy type",
    "preapproval": "Preapproval",
    "purchaser_type": "Purchaser type",
    "rate_band": "Interest-rate band · analyst grouped",
    "state_code": "State / territory",
}


def methods() -> dict[str, str]:
    return {name: sha256(Path(__file__).with_name(name + ".py")) for name in ("hmda_three_year_2018_views", "workspace")}


def source_folder(root: Path) -> Path:
    return contained(root.resolve(), SOURCE_RELATIVE)


def _load_source(root: Path, *, hash_source: bool):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("Private HMDA 2018 source and aggregates must remain on D:")
    folder = source_folder(root)
    acquisition_path = contained(folder, "acquisition-receipt.json")
    audit_path = contained(folder, "audit-receipt.json")
    csv_path = contained(folder, CSV_NAME)
    acquisition, audit = read_json(acquisition_path), read_json(audit_path)
    profile = audit.get("profile", {})
    summary = profile.get("summary", {})
    if (acquisition.get("receipt_id") != SOURCE_ID
            or acquisition.get("status") != "DOWNLOADED_PENDING_ROW_AUDIT"
            or acquisition.get("sha256") != EXPECTED_SHA256
            or acquisition.get("bytes") != 5_879_026_670
            or acquisition.get("dataset_vintage") != "2018 Three-Year National Loan-Level Dataset"
            or acquisition.get("freeze_date") != "2021-12-31"
            or audit.get("audit_id") != AUDIT_ID
            or audit.get("acquisition_receipt_id") != SOURCE_ID
            or audit.get("status") != "PASS_WITH_QUARANTINED_SOURCE_ROWS"
            or audit.get("sha256") != EXPECTED_SHA256
            or len(profile.get("columns", [])) != 99
            or summary.get("records") != 15_140_471
            or summary.get("invalid_action_rows") != 1_961
            or summary.get("blank_lei_rows") != 1_961
            or summary.get("malformed_state_rows") != 1_961
            or profile.get("recognized_action_counts") != EXPECTED_ACTIONS
            or not csv_path.is_file()
            or csv_path.stat().st_size != acquisition.get("bytes")):
        raise ValueError("HMDA 2018 source receipt, schema, or quarantine contract changed")
    if hash_source and sha256(csv_path) != EXPECTED_SHA256:
        raise ValueError("HMDA 2018 source CSV hash does not match the audited source")
    return folder, acquisition_path, audit_path, csv_path, acquisition, audit


def build_view(root: Path) -> dict:
    root = root.resolve()
    folder, acquisition_path, audit_path, csv_path, acquisition, audit = _load_source(root, hash_source=True)
    aggregate_input = contained(root, AGGREGATE_INPUT)
    source_aggregate = read_json(aggregate_input)
    if (source_aggregate.get("status") != "PASS"
            or source_aggregate.get("source_sha256") != EXPECTED_SHA256
            or source_aggregate.get("audit_id") != AUDIT_ID
            or source_aggregate.get("source_rows") != 15_140_471
            or source_aggregate.get("in_domain_rows") != 15_138_510
            or source_aggregate.get("quarantined_rows") != 1_961
            or source_aggregate.get("actions") != EXPECTED_ACTIONS
            or source_aggregate.get("decision_denominator") != 10_623_751
            or source_aggregate.get("denied_numerator") != 2_552_640
            or set(DIMENSIONS) != {row.get("dimension") for row in source_aggregate.get("breakdowns", [])}):
        raise ValueError("HMDA 2018 aggregate output failed source/count/dimension gates")
    counts: dict[str, int] = {}
    for row in source_aggregate["breakdowns"]:
        counts[row["dimension"]] = counts.get(row["dimension"], 0) + row["records"]
    for dimension, count in counts.items():
        expected = 2_552_640 if dimension.startswith("denial_reason-") else 15_138_510
        if count != expected:
            raise ValueError(f"HMDA 2018 {dimension} aggregate does not reconcile: {count} != {expected}")
    frozen_methods = methods()
    aggregate_sha = sha256(aggregate_input)
    method_fingerprint = hashlib.sha256(json.dumps(frozen_methods, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    view_id = "hmda-three-year-2018-view-" + hashlib.sha256(
        f"{SOURCE_ID}:{aggregate_sha}:{method_fingerprint}".encode("utf-8")).hexdigest()[:12]
    view_folder = contained(root, "artifacts/private/" + view_id)
    if view_folder.exists():
        raise ValueError("HMDA 2018 aggregate view already exists; verify or reuse it")
    view_folder.mkdir(parents=True)
    payload = dict(source_aggregate)
    action_counts = dict(source_aggregate["actions"])
    payload["actions"] = [{"code": code, "records": action_counts[code]} for code in sorted(action_counts)]
    payload["summary"] = {"records": source_aggregate["in_domain_rows"], "reporters": 5_730,
        "decision_denominator": source_aggregate["decision_denominator"],
        "denied_numerator": source_aggregate["denied_numerator"],
        "descriptive_denial_rate": str(source_aggregate["descriptive_denied_share"])}
    for row in payload["breakdowns"]:
        row["bucket"] = row["category"]
        row["descriptive_denial_rate"] = (str(row["descriptive_denied_share"])
            if row["descriptive_denied_share"] is not None else None)
        if row["dimension"].startswith("denial_reason-"):
            row["denied_reason_records"] = row["records"]
    payload.update({"view_id": view_id, "source_id": SOURCE_ID, "activity_year": 2018,
        "release_type": "Three-Year National Dataset", "freeze_date": "2021-12-31",
        "source_url": SOURCE_PAGE, "api_docs_url": API_DOCS, "dimensions": DIMENSIONS,
        "scope": "Official 2018 Three-Year national HMDA public LAR, frozen 2021-12-31. Application/underwriting records only.",
        "limitations": [
            "This is a Three-Year freeze and is not comparable as an equivalent release window to the adjacent 2019–2024 One-Year files.",
            "The source CSV has 1,961 action_taken=-1 rows with blank LEI/state. They are retained in the raw file and quarantined; aggregate KPIs include only official action codes 1–8.",
            "Action 3 divided by actions 1–3 is a descriptive application denial share, not PD, delinquency, default, or repayment performance.",
            "HMDA does not provide monthly repayment, loss, recovery, or borrower-linked outcomes. Do not join this file to Freddie, Fannie, or Ginnie panels.",
            "LTV and interest-rate bands are analyst-created display groups; NA and Exempt are preserved, and they are not publisher categories.",
            "No forecast, imputation, synthetic values, or model fit was used.",
        ],
        "denominator_contract": {"codes": ["1", "2", "3"], "numerator": "3",
            "meaning": "Action 3 divided by actions 1+2+3; application decision share, not default PD."},
        "visibility": "private", "public_release_approved": False})
    output = contained(view_folder, "aggregates.json")
    write_new(output, payload)
    source_stat = csv_path.stat()
    receipt = {"view_id": view_id, "source_id": SOURCE_ID,
        "status": "VERIFIED_HMDA_2018_THREE_YEAR_AGGREGATE_VIEW", "completed_at": timestamp(),
        "source_sha256": EXPECTED_SHA256, "source_bytes": source_stat.st_size,
        "source_mtime_ns": source_stat.st_mtime_ns,
        "acquisition_receipt_sha256": sha256(acquisition_path), "audit_receipt_sha256": sha256(audit_path),
        "aggregate_sha256": sha256(output), "aggregate_input_sha256": aggregate_sha,
        "methods": frozen_methods, "visibility": "private", "public_release_approved": False,
        "quarantined_rows": 1_961, "official_rows": 15_138_510}
    write_new(view_folder / "view-complete.json", receipt)
    return receipt


class HmdaThreeYear2018Views:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._methods = methods()

    def _view(self, identifier: str):
        if not isinstance(identifier, str) or not VIEW_PATTERN.fullmatch(identifier):
            raise ValueError("Invalid HMDA 2018 Three-Year view id")
        if methods() != self._methods:
            raise ValueError("HMDA 2018 serving methods changed; restart required")
        folder = contained(self.root, "artifacts/private/" + identifier)
        receipt = read_json(contained(folder, "view-complete.json"))
        source, acquisition_path, audit_path, csv_path, _, _ = _load_source(self.root, hash_source=False)
        stat = csv_path.stat()
        if (receipt.get("view_id") != identifier
                or receipt.get("source_id") != SOURCE_ID
                or receipt.get("status") != "VERIFIED_HMDA_2018_THREE_YEAR_AGGREGATE_VIEW"
                or receipt.get("methods") != self._methods
                or receipt.get("visibility") != "private"
                or receipt.get("public_release_approved") is not False
                or receipt.get("source_bytes") != stat.st_size
                or receipt.get("source_mtime_ns") != stat.st_mtime_ns
                or sha256(acquisition_path) != receipt.get("acquisition_receipt_sha256")
                or sha256(audit_path) != receipt.get("audit_receipt_sha256")):
            raise ValueError("HMDA 2018 aggregate view receipt or source metadata changed")
        aggregate_path = contained(folder, "aggregates.json")
        if sha256(aggregate_path) != receipt.get("aggregate_sha256"):
            raise ValueError("HMDA 2018 aggregate artifact changed")
        payload = read_json(aggregate_path)
        if (payload.get("view_id") != identifier or payload.get("source_id") != SOURCE_ID
                or payload.get("activity_year") != 2018
                or payload.get("summary", {}).get("records") != 15_138_510
                or payload.get("quarantined_rows") != 1_961
                or set(payload.get("dimensions", {})) != set(DIMENSIONS)):
            raise ValueError("HMDA 2018 aggregate content contract changed")
        return folder, receipt, payload

    def catalog(self) -> dict:
        rows = []
        for path in sorted((self.root / "artifacts/private").glob("hmda-three-year-2018-view-*/view-complete.json")):
            try:
                _, receipt, payload = self._view(path.parent.name)
                rows.append({"view_id": payload["view_id"], "source_id": receipt["source_id"],
                    "status": "verified", "records": payload["summary"]["records"],
                    "quarantined_rows": payload["quarantined_rows"], "activity_year": 2018,
                    "release_type": payload["release_type"], "freeze_date": payload["freeze_date"]})
            except (OSError, ValueError, KeyError, TypeError):
                rows.append({"view_id": path.parent.name, "status": "unavailable", "records": None})
        return {"views": rows}

    def view(self, identifier: str) -> dict:
        _, _, payload = self._view(identifier)
        keys = ("view_id", "source_id", "activity_year", "release_type", "freeze_date", "source_rows",
            "in_domain_rows", "quarantined_rows", "decision_denominator", "denied_numerator",
            "descriptive_denied_share", "summary", "actions", "dimensions", "scope", "limitations",
            "denominator_contract", "source_url", "api_docs_url", "visibility", "public_release_approved")
        return {key: payload[key] for key in keys}

    def report(self, identifier: str, query: dict) -> dict:
        if not isinstance(query, dict) or set(query) - {"view_id", "dimension"} or query.get("view_id", identifier) != identifier:
            raise ValueError("Invalid HMDA 2018 aggregate query")
        dimension = query.get("dimension", "state_code")
        if not isinstance(dimension, str) or dimension not in DIMENSIONS:
            raise ValueError("Unsupported HMDA 2018 breakdown dimension")
        _, _, payload = self._view(identifier)
        rows = [row for row in payload["breakdowns"] if row["dimension"] == dimension]
        rows.sort(key=lambda row: (-row["records"], row.get("category", row.get("bucket", ""))))
        return {"view_id": identifier, "source_id": SOURCE_ID, "activity_year": 2018,
            "release_type": payload["release_type"], "freeze_date": payload["freeze_date"],
            "summary": payload["summary"], "dimension": dimension,
            "dimension_label": DIMENSIONS[dimension], "breakdown": rows,
            "visibility": "private", "public_release_approved": False}
