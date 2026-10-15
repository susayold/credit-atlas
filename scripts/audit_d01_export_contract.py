"""Independently audit real schema-2 D01 exports across documented scopes."""
from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

import duckdb

from credit_atlas.service import ResearchService
from credit_atlas.workspace import sha256, write_new

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "d01-a24484b21a21"
CASE_RECEIPT = ROOT / "artifacts/private" / CASE_ID / "case-complete.json"
SERVICE = ResearchService(ROOT, review_path=ROOT / "artifacts/private/d01-export-contract-qa.sqlite3")
case = SERVICE.case(CASE_ID)
manifest = case["manifest"]
snapshot = case["snapshot"]
expected_wrapper = {"schema_version", "case_id", "target", "filter_context", "report",
                    "supplemental_evidence", "supplemental_sha256", "lineage", "scope_notes",
                    "visibility", "public_release_approved"}
expected_supplements = {"quality_monitoring", "episode_followup", "period_transitions"}
expected_filters = {"segment", "basis", "horizon", "from", "to", "transition_year"}
unsafe_keys = {"loan_id", "borrower_id", "account_id", "prediction"}


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def validate_package(query, package):
    if set(package) != expected_wrapper:
        raise AssertionError(f"schema-2 wrapper fields differ: {sorted(set(package) ^ expected_wrapper)}")
    if (package["schema_version"] != 2 or package["case_id"] != CASE_ID
            or package["visibility"] != "private" or package["public_release_approved"] is not False
            or package["target"].get("version") != snapshot["target"]["version"]):
        raise AssertionError("Outer export identity/visibility/target mismatch")
    if set(package["filter_context"]) != expected_filters:
        raise AssertionError("Export filter context changed")
    if set(package["supplemental_evidence"]) != expected_supplements:
        raise AssertionError("Supplemental evidence contract changed")
    if set(package["supplemental_sha256"]) != expected_supplements:
        raise AssertionError("Supplement digest contract changed")
    for name, value in package["supplemental_evidence"].items():
        actual = __import__("hashlib").sha256(json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()
        if package["supplemental_sha256"][name] != actual:
            raise AssertionError(f"Supplement digest mismatch: {name}")
        if value.get("case_id") != CASE_ID or value.get("pipeline_run") != snapshot["pipeline_run"]:
            raise AssertionError(f"Supplement lineage mismatch: {name}")

    report = package["report"]
    schema = json.loads((ROOT / "vendor/credit_risk_strategy_lab/contracts/report-data.schema.json").read_text(encoding="utf-8"))
    for field, spec in schema["properties"].items():
        if "const" in spec and report.get(field) != spec["const"]:
            raise AssertionError(f"Embedded schema-1 constant failed: {field}")
    if not set(schema["required"]) <= set(report):
        raise AssertionError("Embedded schema-1 required fields missing")
    if report["pipeline_run"] != snapshot["pipeline_run"]:
        raise AssertionError("Embedded report belongs to another pipeline")
    if set(report["contract_rules"]) != {"null_means", "frontend_recompute", "raw_identifiers_included", "prediction_rows_included"}:
        raise AssertionError("Embedded report contract rules changed")
    if (report["contract_rules"]["raw_identifiers_included"] is not False
            or report["contract_rules"]["prediction_rows_included"] is not False
            or report["contract_rules"]["frontend_recompute"] is not False
            or report["contract_rules"]["null_means"] != "unavailable_not_zero"):
        raise AssertionError("Report enables a prohibited identifier/prediction/recompute behavior")
    for table in report["tables"]:
        if not {"table_id", "grain", "source_stage", "pipeline_run", "rows"} <= set(table):
            raise AssertionError("Aggregate table schema incomplete")
        if table["pipeline_run"] != snapshot["pipeline_run"] or not isinstance(table["rows"], list):
            raise AssertionError("Aggregate table run or row type mismatch")

    lineage = package["lineage"]
    if (lineage["pipeline_run"] != snapshot["pipeline_run"]
            or lineage["case_receipt_sha256"] != case["complete_hash"]
            or lineage["source_output_sha256"] != manifest["outputs_sha256"]
            or lineage["method_source_sha256"] != {name: item["sha256"] for name, item in SERVICE.method_sources.items()}):
        raise AssertionError("Export provenance does not match frozen selected run")
    if set(package["scope_notes"]) != {"monthly_range", "loss", "transitions", "period_transitions", "monitoring", "episode_followup"}:
        raise AssertionError("Scope notes incomplete")
    if unsafe_keys & set(walk_keys(package)):
        raise AssertionError("Private identifier/prediction field present")
    if any(key.lower() in {"pd", "pd12", "ecl", "expected_credit_loss", "cash_flow", "cf"}
           for key in report["metric_registry"]):
        raise AssertionError("Unsupported PD/ECL/cash-flow metric in report registry")

    # Query/API parsers accept a bounded explicit filter list, never a metric-use override.
    for unsupported in ({"metric": "pd12"}, {"use": "ECL"}, {"cash_flow": "expected"}):
        try:
            SERVICE.report(CASE_ID, unsupported)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsupported report parameters were silently accepted: {unsupported}")
    if query.get("run") not in (None, CASE_ID):
        raise AssertionError("Test fixture supplied an inconsistent run id")
    return len(report["tables"]), sum(len(table["rows"]) for table in report["tables"])


scopes = [
    ("all", {"segment": "all", "basis": "count", "horizon": "12"}),
    ("relief", {"segment": "relief", "basis": "balance", "horizon": "6"}),
    ("non_relief_month_range", {"segment": "non_relief", "from": "2020-01", "to": "2020-12"}),
    ("transition_year_2020", {"segment": "all", "transition_year": "2020"}),
    ("transition_year_unavailable", {"segment": "all", "transition_year": "1900"}),
]
checks = []
for name, query in scopes:
    package = SERVICE.report(CASE_ID, query)
    table_count, row_count = validate_package(query, package)
    repeated = SERVICE.report(CASE_ID, query)
    canonical = lambda obj: json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if canonical(package) != canonical(repeated):
        raise AssertionError(f"Repeated export is nondeterministic for {name}")
    period = package["supplemental_evidence"]["period_transitions"]
    if query.get("transition_year") == "1900" and period["rows"]:
        raise AssertionError("Unavailable transition year silently fell back to other years")
    if (query.get("transition_year") == "2020"
            and any(row["reporting_year"] != 2020 for row in period["rows"])):
        raise AssertionError("Reporting-year filter leaked other years")
    checks.append({"scope": name, "table_count": table_count, "aggregate_rows": row_count,
                   "deterministic": True, "supplemental_year_rows": len(period["rows"]),
                   "supplemental_lifetime_rows": len(period["lifetime_rows"])})

# Independently scan the actual all-sample export for any source loan identifier.
with duckdb.connect() as db:
    ids = [row[0] for row in db.read_parquet(str(case["path"] / "loan-index.parquet")).project("loan_id").fetchall()]
identity_pattern = re.compile("|".join(re.escape(value) for value in ids).encode("ascii"))
serialized = canonical(SERVICE.report(CASE_ID, scopes[0][1])).encode("utf-8")
if identity_pattern.search(serialized):
    raise AssertionError("Source loan identifier found in aggregate export bytes")

output = ROOT / "artifacts/private" / f"d01-export-contract-{uuid4().hex[:12]}"
output.mkdir(parents=True, exist_ok=False)
receipt = {
    "status": "PASS", "requirement": "M01-022", "case_id": CASE_ID,
    "pipeline_run": snapshot["pipeline_run"], "schema_version": 2,
    "scopes_checked": checks, "scope_count": len(checks),
    "source_ids_scanned": len(ids), "source_id_matches": 0,
    "unsupported_metric_uses_rejected": ["PD12", "ECL", "cash flow"],
    "lineage_and_supplement_digests_verified": True,
    "no_loan_level_identifier_or_prediction_fields": True,
    "method_sha256": sha256(Path(__file__)),
    "source_receipt_sha256": sha256(CASE_RECEIPT),
}
write_new(output / "audit.json", receipt)
write_new(output / "receipt.json", {key: value for key, value in receipt.items()
                                    if key not in {"scopes_checked"}} | {"scope_names": [row["scope"] for row in checks]})
print(json.dumps({"status": "PASS", "output": str(output), "scopes": len(checks),
                  "source_ids_scanned": len(ids), "source_id_matches": 0,
                  "unsupported_uses_rejected": 3}, indent=2))
