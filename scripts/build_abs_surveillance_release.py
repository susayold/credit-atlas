"""Build an aggregate-only, contract-aware ABS surveillance release."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "data" / "abs-surveillance-contracts-2026-10-17.json"
OUTPUT_CSV = "abs-surveillance-exceptions-103-periods.csv"
OUTPUT_RECEIPT = "abs-surveillance-exceptions-103-periods-receipt.json"
HEADERS = [
    "contract_id", "deal_id", "issuer_family", "report_month", "report_date",
    "collection_period_start", "collection_period_end", "collection_period_days",
    "filing_date", "abs_ee_accession", "abs_ee_source_url", "certificate_accession",
    "certificate_source_url", "asset_pool_balance_usd", "certificate_pool_balance_usd",
    "pool_balance_delta_usd", "pool_balance_tie", "asset_positive_balance_count",
    "certificate_positive_balance_count", "positive_balance_count_tie",
    "asset_positive_chargeoff_event_count", "certificate_chargeoff_event_count",
    "chargeoff_count_tie", "asset_chargeoff_amount_source_signed_usd",
    "certificate_chargeoff_amount_source_signed_usd", "chargeoff_amount_tie",
    "first_code4_event_count", "first_code4_chargeoff_amount_usd",
    "first_code4_count_tie", "first_code4_amount_tie", "asset_recovered_amount_usd",
    "certificate_recovery_comparator_id", "certificate_recovery_amount_usd",
    "recovery_delta_asset_minus_certificate_usd", "recovery_tie_status",
    "toyota_certificate_component_identity_status", "toyota_certificate_net_loss_identity_status",
    "nissan_monthly_net_loss_identity_status", "nissan_cumulative_net_loss_identity_status",
    "native_dpd_definition_id", "dpd_literal_exact_fields", "dpd_total_field_checks",
    "exception_categories", "exception_status", "root_cause_resolved", "exception_note",
]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def value(row: dict[str, str], key: str | None) -> str:
    return "" if not key else (row.get(key) or "")


def amount(row: dict[str, str], key: str | None) -> Decimal | None:
    raw = value(row, key)
    return Decimal(raw) if raw else None


def as_text(number: Decimal | None) -> str:
    return "" if number is None else format(number, "f")


def tie_flag(row: dict[str, str], key: str | None) -> str:
    if not key or value(row, key) == "":
        return ""
    return "TIED" if value(row, key).casefold() in {"true", "pass", "tied"} else "MISMATCH"


def sec_index_url(cik: str, accession: str) -> str:
    compact = accession.replace("-", "")
    if len(compact) != 18 or not compact.isdigit():
        raise ValueError(f"Unexpected SEC accession: {accession}")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{compact}/{accession}-index.html"


def exception_categories(row: dict[str, str], contract: dict) -> list[str]:
    categories: list[str] = []
    if row["recovery_tie_status"] != "TIED":
        categories.append("recovery_comparator_delta")
    if row["pool_balance_tie"] == "MISMATCH":
        categories.append("pool_balance")
    if row["positive_balance_count_tie"] == "MISMATCH":
        categories.append("positive_balance_count")
    if row["chargeoff_count_tie"] == "MISMATCH":
        categories.append("chargeoff_event_count")
    if row["chargeoff_amount_tie"] == "MISMATCH":
        categories.append("chargeoff_amount")
    if row["first_code4_count_tie"] == "MISMATCH":
        categories.append("first_code4_event_count")
    if row["first_code4_amount_tie"] == "MISMATCH":
        categories.append("first_code4_amount")
    if row["dpd_total_field_checks"]:
        if int(row["dpd_literal_exact_fields"]) != int(row["dpd_total_field_checks"]):
            categories.append("literal_dpd_bucket")
    return categories


def normalize_row(contract: dict, source: dict[str, str]) -> dict[str, str]:
    field_map = contract["fields"]
    report_date = value(source, field_map["report_date"])
    start = value(source, field_map["collection_period_start"])
    end = value(source, field_map["collection_period_end"])
    if not report_date or not start or not end or end != report_date or start > end:
        raise ValueError(f"Invalid period dates for {contract['deal_id']}: {report_date}/{start}/{end}")

    asset_recovery = amount(source, field_map["asset_recovery"])
    certificate_recovery = amount(source, field_map["certificate_recovery"])
    if asset_recovery is None or certificate_recovery is None:
        raise ValueError(f"Missing recovery comparator input for {contract['deal_id']} {report_date}")
    recovery_delta = asset_recovery - certificate_recovery
    recovery_status = "TIED" if recovery_delta == 0 else "UNRESOLVED"
    asset_accession = value(source, field_map["abs_ee_accession"])
    abs_ee_url = value(source, field_map.get("abs_ee_url")) or sec_index_url(contract["cik"], asset_accession)
    cert_accession = value(source, field_map["certificate_accession"])
    cert_url = value(source, field_map["certificate_url"])

    row = {header: "" for header in HEADERS}
    row.update({
        "contract_id": contract["contract_id"],
        "deal_id": contract["deal_id"],
        "issuer_family": contract["issuer_family"],
        "report_month": value(source, field_map.get("report_month")) or report_date[:7],
        "report_date": report_date,
        "collection_period_start": start,
        "collection_period_end": end,
        "collection_period_days": value(source, field_map["collection_period_days"]),
        "filing_date": value(source, field_map.get("filing_date")),
        "abs_ee_accession": asset_accession,
        "abs_ee_source_url": abs_ee_url,
        "certificate_accession": cert_accession,
        "certificate_source_url": cert_url,
        "asset_pool_balance_usd": value(source, field_map.get("asset_pool_balance")),
        "certificate_pool_balance_usd": value(source, field_map.get("certificate_pool_balance")),
        "pool_balance_delta_usd": value(source, field_map.get("pool_balance_delta")),
        "pool_balance_tie": tie_flag(source, field_map.get("pool_balance_tie")),
        "asset_positive_balance_count": value(source, field_map.get("asset_positive_balance_count")),
        "certificate_positive_balance_count": value(source, field_map.get("certificate_positive_balance_count")),
        "positive_balance_count_tie": tie_flag(source, field_map.get("positive_balance_count_tie")),
        "asset_positive_chargeoff_event_count": value(source, field_map.get("asset_chargeoff_count")),
        "certificate_chargeoff_event_count": value(source, field_map.get("certificate_chargeoff_count")),
        "chargeoff_count_tie": tie_flag(source, field_map.get("chargeoff_count_tie")),
        "asset_chargeoff_amount_source_signed_usd": value(source, field_map.get("asset_chargeoff_amount")),
        "certificate_chargeoff_amount_source_signed_usd": value(source, field_map.get("certificate_chargeoff_amount")),
        "chargeoff_amount_tie": tie_flag(source, field_map.get("chargeoff_amount_tie")),
        "first_code4_event_count": value(source, field_map.get("first_code4_count")),
        "first_code4_chargeoff_amount_usd": value(source, field_map.get("first_code4_amount")),
        "first_code4_count_tie": tie_flag(source, field_map.get("first_code4_count_tie")),
        "first_code4_amount_tie": tie_flag(source, field_map.get("first_code4_amount_tie")),
        "asset_recovered_amount_usd": as_text(asset_recovery),
        "certificate_recovery_comparator_id": contract["certificate_recovery_comparator_id"],
        "certificate_recovery_amount_usd": as_text(certificate_recovery),
        "recovery_delta_asset_minus_certificate_usd": as_text(recovery_delta),
        "recovery_tie_status": recovery_status,
        "toyota_certificate_component_identity_status": tie_flag(source, field_map.get("toyota_certificate_component_identity")),
        "toyota_certificate_net_loss_identity_status": tie_flag(source, field_map.get("toyota_certificate_net_loss_identity")),
        "nissan_monthly_net_loss_identity_status": tie_flag(source, field_map.get("nissan_monthly_net_loss_identity")),
        "nissan_cumulative_net_loss_identity_status": tie_flag(source, field_map.get("nissan_cumulative_net_loss_identity")),
        "native_dpd_definition_id": contract["native_dpd_definition_id"],
        "dpd_literal_exact_fields": value(source, field_map.get("dpd_literal_exact_fields")),
        "dpd_total_field_checks": value(source, field_map.get("dpd_total_field_checks")),
        "root_cause_resolved": "No",
    })
    categories = exception_categories(row, contract)
    row["exception_categories"] = ";".join(categories)
    row["exception_status"] = "UNRESOLVED" if categories else "NO_EXCEPTION_IN_RELEASE_SCOPE"
    row["exception_note"] = value(source, field_map.get("exception_note")) if categories else ""
    if not row["exception_note"] and categories:
        readable = ", ".join(category.replace("_", " ") for category in categories)
        row["exception_note"] = f"Unresolved deal-specific exception(s): {readable}. See the contract-specific definition and filed sources; no cause is assigned."
    return row


def summarize(contract: dict, rows: list[dict[str, str]]) -> dict:
    deal_rows = [row for row in rows if row["contract_id"] == contract["contract_id"]]
    deltas = [Decimal(row["recovery_delta_asset_minus_certificate_usd"]) for row in deal_rows]
    return {
        "contract_id": contract["contract_id"],
        "deal_id": contract["deal_id"],
        "period_count": len(deal_rows),
        "report_start": min(row["report_date"] for row in deal_rows),
        "report_end": max(row["report_date"] for row in deal_rows),
        "recovery_comparator_id": contract["certificate_recovery_comparator_id"],
        "recovery_tie_periods": sum(delta == 0 for delta in deltas),
        "recovery_exception_periods": sum(delta != 0 for delta in deltas),
        "recovery_residual_total_usd_within_contract_only": as_text(sum(deltas, Decimal("0"))),
        "exception_periods": sum(row["exception_status"] == "UNRESOLVED" for row in deal_rows),
        "exception_category_counts": {
            category: sum(category in row["exception_categories"].split(";") for row in deal_rows)
            for category in sorted({cat for row in deal_rows for cat in row["exception_categories"].split(";") if cat})
        },
    }


def build(root: Path, output_dir: Path) -> dict:
    root = root.resolve()
    contract_path = CONTRACTS
    contracts_doc = read_json(contract_path)
    release = contracts_doc["release_id"]
    rows: list[dict[str, str]] = []
    source_receipts: dict[str, dict] = {}
    contract_by_deal: set[str] = set()
    contract_summaries: list[dict] = []

    for contract in contracts_doc["contracts"]:
        if contract["contract_id"] in contract_by_deal:
            raise ValueError(f"Duplicate contract ID: {contract['contract_id']}")
        contract_by_deal.add(contract["contract_id"])
        source_csv = root / "docs" / "data" / contract["source_csv"]
        source_receipt_path = root / "docs" / "data" / contract["source_receipt"]
        source_receipt = read_json(source_receipt_path)
        source_hash = sha256(source_csv)
        if source_receipt.get("csv_sha256") != source_hash:
            raise ValueError(f"Source CSV receipt hash mismatch: {contract['source_csv']}")
        if source_receipt.get("loan_level_rows_published") is not False:
            raise ValueError(f"Source receipt is not approved for aggregate-only release: {contract['source_csv']}")
        source_receipts[contract["deal_id"]] = {
            "source_csv": contract["source_csv"],
            "source_csv_sha256": source_hash,
            "source_receipt": contract["source_receipt"],
            "source_receipt_sha256": sha256(source_receipt_path),
            "period_count_expected": contract["expected_period_count"],
        }
        source_rows = rows_from_csv(source_csv)
        field_map = contract["fields"]
        matched = [row for row in source_rows if value(row, field_map.get("deal")) == contract["source_deal_value"]]
        if len(matched) != contract["expected_period_count"]:
            raise ValueError(f"Unexpected source period count for {contract['deal_id']}: {len(matched)}")
        deal_rows = [normalize_row(contract, row) for row in matched]
        if len({row["report_date"] for row in deal_rows}) != len(deal_rows):
            raise ValueError(f"Duplicate deal/report-date key in {contract['deal_id']}")
        if min(row["report_date"] for row in deal_rows) != contract["expected_report_start"]:
            raise ValueError(f"Unexpected start period for {contract['deal_id']}")
        if max(row["report_date"] for row in deal_rows) != contract["expected_report_end"]:
            raise ValueError(f"Unexpected end period for {contract['deal_id']}")
        rows.extend(deal_rows)
    contract_order = {contract["contract_id"]: index for index, contract in enumerate(contracts_doc["contracts"])}
    rows.sort(key=lambda row: (contract_order[row["contract_id"]], row["report_date"]))
    if len(rows) != 103 or len({(row["contract_id"], row["report_date"]) for row in rows}) != 103:
        raise ValueError("Expected 103 unique deal-contract/report-date rows")
    # Recompute summaries after the final row set is assembled.
    contract_summaries = [summarize(contract, rows) for contract in contracts_doc["contracts"]]
    expected = {
        "TOYOTA-2022-B": (2, 49, Decimal("2058647.06")),
        "TOYOTA-2024-B": (1, 28, Decimal("1764558.08")),
        "NISSAN-2024-B": (17, 6, Decimal("8859.23")),
    }
    for summary in contract_summaries:
        ties, exceptions, delta = expected[summary["deal_id"]]
        if (summary["recovery_tie_periods"], summary["recovery_exception_periods"], Decimal(summary["recovery_residual_total_usd_within_contract_only"])) != (ties, exceptions, delta):
            raise ValueError(f"Contract recovery reconciliation changed for {summary['deal_id']}")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / OUTPUT_CSV
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADERS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)

    receipt = {
        "status": "PASS",
        "release_id": release,
        "row_grain": "one deal contract × public report date",
        "period_count": len(rows),
        "deal_count": len(contract_summaries),
        "deal_contract_summaries": contract_summaries,
        "cross_deal_recovery_residual_total": None,
        "cross_deal_residual_note": "Not calculated: certificate recovery comparator semantics differ by contract; aggregate only within each contract.",
        "exception_period_count": sum(row["exception_status"] == "UNRESOLVED" for row in rows),
        "recovery_exception_period_count": sum(row["recovery_tie_status"] == "UNRESOLVED" for row in rows),
        "source_receipts": source_receipts,
        "contracts_sha256": sha256(contract_path),
        "csv_sha256": sha256(csv_path),
        "visibility": "public filing aggregates, accession links and contract metadata only",
        "loan_level_rows_published": False,
        "forecast_or_imputation_used": False,
        "root_cause_resolved": False,
    }
    (output_dir / OUTPUT_RECEIPT).write_text(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=ROOT, help="Public CreditAtlas checkout containing audited aggregate ledgers")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs" / "data")
    args = parser.parse_args()
    receipt = build(args.workspace_root, args.output_dir)
    print(json.dumps({"status": receipt["status"], "period_count": receipt["period_count"], "exception_period_count": receipt["exception_period_count"], "deal_contract_summaries": receipt["deal_contract_summaries"], "csv_sha256": receipt["csv_sha256"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
