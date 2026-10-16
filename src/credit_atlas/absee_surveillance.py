"""Public, contract-aware ABS exception surveillance release."""
from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path


CONTRACTS_FILE = "docs/data/abs-surveillance-contracts-2026-10-17.json"
CSV_FILE = "docs/data/abs-surveillance-exceptions-103-periods.csv"
RECEIPT_FILE = "docs/data/abs-surveillance-exceptions-103-periods-receipt.json"
EXPECTED_RELEASE = "abs-surveillance-2026-10-17"
EXPECTED_PERIODS = 103


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _within(root: Path, relative: str) -> Path:
    base = root.resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError("ABS surveillance release path escaped its public root")
    return path


def report(root: Path, query: dict | None = None) -> dict:
    """Read and integrity-check the public aggregate release; reject filters for now."""
    if query:
        raise ValueError("ABS surveillance release accepts no filters")
    root = Path(root).resolve()
    contracts_path = _within(root, CONTRACTS_FILE)
    csv_path = _within(root, CSV_FILE)
    receipt_path = _within(root, RECEIPT_FILE)
    contracts_doc = _read_json(contracts_path)
    receipt = _read_json(receipt_path)
    if contracts_doc.get("release_id") != EXPECTED_RELEASE or receipt.get("release_id") != EXPECTED_RELEASE:
        raise ValueError("Unexpected ABS surveillance release identifier")
    if receipt.get("status") != "PASS" or receipt.get("contracts_sha256") != _sha256(contracts_path):
        raise ValueError("ABS surveillance contract receipt failed integrity check")
    if receipt.get("csv_sha256") != _sha256(csv_path):
        raise ValueError("ABS surveillance ledger receipt failed integrity check")
    if receipt.get("loan_level_rows_published") is not False or receipt.get("forecast_or_imputation_used") is not False:
        raise ValueError("ABS surveillance release visibility/method controls changed")

    for deal_id, source in receipt.get("source_receipts", {}).items():
        source_path = _within(root, "docs/data/" + source["source_csv"])
        source_receipt_path = _within(root, "docs/data/" + source["source_receipt"])
        if _sha256(source_path) != source.get("source_csv_sha256"):
            raise ValueError(f"ABS surveillance source CSV changed for {deal_id}")
        if _sha256(source_receipt_path) != source.get("source_receipt_sha256"):
            raise ValueError(f"ABS surveillance source receipt changed for {deal_id}")

    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != EXPECTED_PERIODS or receipt.get("period_count") != EXPECTED_PERIODS:
        raise ValueError("ABS surveillance period count changed")
    keys = [(row["contract_id"], row["report_date"]) for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("ABS surveillance ledger contains duplicate contract/report-date keys")
    if any(row["root_cause_resolved"] != "No" for row in rows):
        raise ValueError("ABS surveillance root-cause state changed without review")

    contracts_by_id = {contract["contract_id"]: contract for contract in contracts_doc["contracts"]}
    if set(row["contract_id"] for row in rows) != set(contracts_by_id):
        raise ValueError("ABS surveillance ledger/contract coverage mismatch")

    deal_summaries = []
    safe_contracts = []
    for contract in contracts_doc["contracts"]:
        selected = [row for row in rows if row["contract_id"] == contract["contract_id"]]
        if len(selected) != contract["expected_period_count"]:
            raise ValueError(f"ABS surveillance expected period count changed for {contract['deal_id']}")
        deltas = [Decimal(row["recovery_delta_asset_minus_certificate_usd"]) for row in selected]
        summary = {
            "contract_id": contract["contract_id"],
            "deal_id": contract["deal_id"],
            "trust_name": contract["trust_name"],
            "issuer_family": contract["issuer_family"],
            "period_count": len(selected),
            "report_start": min(row["report_date"] for row in selected),
            "report_end": max(row["report_date"] for row in selected),
            "recovery_comparator_id": contract["certificate_recovery_comparator_id"],
            "recovery_comparator_label": contract["certificate_recovery_comparator_label"],
            "recovery_comparator_definition": contract["certificate_recovery_definition"],
            "native_dpd_definition_id": contract["native_dpd_definition_id"],
            "native_dpd_definition": contract["native_dpd_definition"],
            "recovery_tie_periods": sum(row["recovery_tie_status"] == "TIED" for row in selected),
            "recovery_exception_periods": sum(row["recovery_tie_status"] == "UNRESOLVED" for row in selected),
            "recovery_residual_total_usd_within_contract_only": format(sum(deltas, Decimal("0")), "f"),
            "exception_periods": sum(row["exception_status"] == "UNRESOLVED" for row in selected),
            "exception_category_counts": _category_counts(selected),
        }
        expected_summary = next((x for x in receipt["deal_contract_summaries"] if x["contract_id"] == contract["contract_id"]), None)
        if not expected_summary:
            raise ValueError(f"ABS surveillance summary receipt missing for {contract['deal_id']}")
        for field in ("period_count", "recovery_tie_periods", "recovery_exception_periods", "exception_periods"):
            if summary[field] != expected_summary[field]:
                raise ValueError(f"ABS surveillance summary count changed for {contract['deal_id']}: {field}")
        if summary["recovery_residual_total_usd_within_contract_only"] != expected_summary["recovery_residual_total_usd_within_contract_only"]:
            raise ValueError(f"ABS surveillance residual changed for {contract['deal_id']}")
        deal_summaries.append(summary)
        safe_contracts.append({
            "contract_id": contract["contract_id"],
            "deal_id": contract["deal_id"],
            "trust_name": contract["trust_name"],
            "issuer_family": contract["issuer_family"],
            "certificate_recovery_comparator_id": contract["certificate_recovery_comparator_id"],
            "certificate_recovery_comparator_label": contract["certificate_recovery_comparator_label"],
            "certificate_recovery_definition": contract["certificate_recovery_definition"],
            "native_dpd_definition_id": contract["native_dpd_definition_id"],
            "native_dpd_definition": contract["native_dpd_definition"],
            "evidence_note": contract["evidence_note"],
        })

    exceptions = [row for row in rows if row["exception_status"] == "UNRESOLVED"]
    recovery_exceptions = [row for row in rows if row["recovery_tie_status"] == "UNRESOLVED"]
    return {
        "status": "PASS",
        "release_id": EXPECTED_RELEASE,
        "as_of": contracts_doc["as_of"],
        "row_grain": contracts_doc["row_grain"],
        "period_count": len(rows),
        "deal_count": len(safe_contracts),
        "deal_contracts": safe_contracts,
        "deal_summaries": deal_summaries,
        "exception_period_count": len(exceptions),
        "recovery_exception_period_count": len(recovery_exceptions),
        "cross_deal_recovery_residual_total": None,
        "cross_deal_residual_note": receipt["cross_deal_residual_note"],
        "analyst_finding": contracts_doc["analyst_finding"],
        "exceptions": exceptions,
        "recovery_exceptions": recovery_exceptions,
        "source_receipts": receipt["source_receipts"],
        "csv_sha256": receipt["csv_sha256"],
        "visibility": receipt["visibility"],
        "loan_level_rows_published": False,
        "forecast_or_imputation_used": False,
    }


def _category_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    categories = sorted({category for row in rows for category in row["exception_categories"].split(";") if category})
    return {category: sum(category in row["exception_categories"].split(";") for row in rows) for category in categories}
