"""Build a public aggregate Nissan 2024-B event/DPD/recovery exception ledger.

Input audit artifacts remain in the private CreditAtlas workspace. This script
publishes only month-level totals, SEC filing references and audit hashes.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ZERO = Decimal("0.00")
CSV_NAME = "nissan-2024b-exception-ledger-23-periods.csv"
RECEIPT_NAME = "nissan-2024b-exception-ledger-23-periods-receipt.json"
STRUCTURED_ID = "nissan-2024b-validation-panel-7cd3605b4e07"
AUDITS = {
    "certificate_tieout": ("nissan-2024b-certificate-tieout-d7a71f85c77c", "NISSAN_2024B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED"),
    "event_exceptions": ("nissan-2024b-event-exceptions-90406964d980", "NISSAN_2024B_EVENT_EXCEPTIONS_DRILLED"),
    "dpd_boundary": ("nissan-2024b-dpd-boundary-audit-014f95c3b7eb", "NISSAN_2024B_DPD_BOUNDARY_RULES_COMPARED"),
    "recovery_dpd": ("nissan-2024b-recovery-dpd-exceptions-e148ce023a55", "NISSAN_2024B_RECOVERY_AND_DPD_EXCEPTIONS_ANALYZED"),
    "panel": ("nissan-2024b-absee-panel-audit-8b5590abd3d5", "NISSAN_2024B_LONGITUDINAL_PANEL_AUDITED"),
}
DPD_LABELS = {
    "31-60 Days Delinquent": "31_60",
    "61-90 Days Delinquent": "61_90",
    "91-120 Days Delinquent": "91_120",
    "More than 120 Days": "over_120",
}


class CertificateCellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r"\s+", " ", " ".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def contained(root: Path, *parts: str) -> Path:
    resolved_root = root.resolve()
    candidate = root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError("An input escaped the selected private CreditAtlas workspace")
    return candidate


def parse_period(html_path: Path) -> tuple[str, str]:
    parser = CertificateCellParser()
    parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    found: dict[str, date] = {}
    for row in parser.rows:
        normalized = [re.sub(r"\s+", " ", cell).strip().casefold() for cell in row]
        for label in ("collection period start", "collection period end"):
            if label not in normalized:
                continue
            position = normalized.index(label)
            value = next((cell for cell in row[position + 1 :] if cell), None)
            if value is None:
                raise ValueError(f"Missing {label} date in {html_path.name}")
            found[label] = datetime.strptime(value, "%d-%b-%y").date()
    if set(found) != {"collection period start", "collection period end"}:
        raise ValueError(f"Collection-period start/end not found in {html_path.name}")
    start = found["collection period start"]
    end = found["collection period end"]
    if start > end:
        raise ValueError(f"Reversed collection period in {html_path.name}")
    return start.isoformat(), end.isoformat()


def sec_document_url(workspace: Path, month: str, suffix: str) -> str:
    index_path = contained(workspace, "data", "private", "structured", STRUCTURED_ID, f"{month}-{suffix}-index.json")
    directory = read_json(index_path)["directory"]
    archive_path = directory["name"].rstrip("/")
    if not archive_path.startswith("/Archives/edgar/data/"):
        raise ValueError(f"Unexpected SEC archive path in {index_path.name}")
    base = "https://www.sec.gov" + archive_path
    if suffix == "absee":
        accession = archive_path.rsplit("/", 1)[-1]
        return f"{base}/{accession}-index.html"
    document = next((item["name"] for item in directory["item"] if item["name"].casefold().endswith("ex991.htm")), None)
    if not document:
        raise ValueError(f"SEC 10-D EX-99.1 missing from {index_path.name}")
    return f"{base}/{document}"


def load_inputs(workspace: Path) -> tuple[dict, dict]:
    audits: dict[str, dict] = {}
    evidence: dict[str, dict] = {}
    audit_root = contained(workspace, "artifacts", "private")
    for key, (artifact_id, expected_status) in AUDITS.items():
        directory = contained(audit_root, artifact_id)
        audit_path = contained(directory, "audit.json")
        receipt_path = contained(directory, "receipt.json")
        audit = read_json(audit_path)
        receipt = read_json(receipt_path)
        audit_hash = sha256(audit_path)
        if audit.get("status") != expected_status or receipt.get("status") != expected_status:
            raise ValueError(f"Unexpected audit status for {artifact_id}")
        if receipt.get("audit_sha256") != audit_hash:
            raise ValueError(f"Receipt hash mismatch for {artifact_id}")
        if audit.get("public_release_approved") is not False or receipt.get("public_release_approved") is not False:
            raise ValueError(f"Private input visibility changed for {artifact_id}; review before export")
        audits[key] = audit
        evidence[key] = {
            "artifact_id": artifact_id,
            "status": expected_status,
            "audit_sha256": audit_hash,
            "receipt_sha256": sha256(receipt_path),
            "source_receipt_sha256": audit.get("source_receipt_sha256"),
            "panel_manifest_sha256": audit.get("panel_manifest_sha256"),
        }
    return audits, evidence


def build(workspace: Path, output_dir: Path) -> dict:
    workspace = workspace.resolve()
    audits, evidence = load_inputs(workspace)
    cert = audits["certificate_tieout"]
    event = audits["event_exceptions"]
    dpd = audits["dpd_boundary"]
    recovery = audits["recovery_dpd"]
    panel = audits["panel"]

    if cert.get("issuer") != "Nissan Auto Receivables 2024-B Owner Trust" or cert.get("period_count") != 23:
        raise ValueError("Certificate audit issuer or period count changed")
    if panel.get("row_month_observations") != 1_154_259 or panel.get("period_count") != 23:
        raise ValueError("Pinned Nissan panel audit scope changed")

    dpd_by_date = {row["report_date"]: row for row in dpd["periods"]}
    recovery_by_date = {row["report_date"]: row for row in recovery["recovery_periods"]}
    event_by_month = event["periods"]
    if len(dpd_by_date) != 23 or len(recovery_by_date) != 6 or len(event_by_month) != 4:
        raise ValueError("Nissan exception audit coverage changed")

    rows: list[dict] = []
    for source in sorted(cert["periods"], key=lambda row: row["report_date"]):
        report_date = date.fromisoformat(source["report_date"])
        month = report_date.strftime("%Y-%m")
        dpd_row = dpd_by_date[source["report_date"]]
        collection_start, collection_end = parse_period(
            contained(workspace, "data", "private", "structured", STRUCTURED_ID, f"{month}-certificate.html")
        )
        if collection_end != report_date.isoformat():
            raise ValueError(f"Certificate collection-period end disagrees for {month}")

        row = {
            "report_date": source["report_date"],
            "report_month": month,
            "collection_period_start": collection_start,
            "collection_period_end": collection_end,
            "collection_period_calendar_days": (date.fromisoformat(collection_end) - date.fromisoformat(collection_start)).days + 1,
            "abs_ee_accession": source["abs_ee_accession"],
            "ten_d_accession": source["10d_accession"],
            "abs_ee_filing_url": sec_document_url(workspace, month, "absee"),
            "certificate_ex991_url": sec_document_url(workspace, month, "10d"),
            "asset_pool_balance_usd": source["asset_pool_balance"],
            "certificate_pool_balance_usd": source["certificate_pool_balance"],
            "pool_balance_delta_usd": str(Decimal(source["asset_pool_balance"]) - Decimal(source["certificate_pool_balance"])),
            "pool_balance_tie": source["ties"]["pool_balance_exact"],
            "asset_positive_balance_count": source["positive_balance_count"],
            "certificate_contract_count": source["certificate_contract_count"],
            "positive_balance_count_tie": source["ties"]["positive_balance_count_matches"],
            "asset_chargeoff_event_count": source["asset_chargeoff_events"],
            "certificate_defaulted_receivables_count": source["certificate_defaulted_receivables"],
            "asset_chargeoff_amount_positive_usd": source["asset_chargeoff_amount"],
            "certificate_gross_defaulted_principal_signed_usd": source["certificate_gross_defaulted_principal"],
            "chargeoff_count_tie": source["ties"]["chargeoff_event_count_matches"],
            "chargeoff_amount_tie": source["ties"]["chargeoff_amount_matches_gross_defaulted_principal"],
            "first_code4_event_count": source["asset_first_code4_events"],
            "first_code4_positive_chargeoff_count": source["asset_first_code4_positive_chargeoff_events"],
            "first_code4_chargeoff_amount_usd": source["asset_first_code4_chargeoff_amount"],
            "first_code4_count_tie": source["ties"]["first_code4_event_count_matches_certificate"],
            "first_code4_amount_tie": source["ties"]["first_code4_chargeoff_amount_matches_certificate"],
            "asset_recovered_amount_usd": source["asset_recovered_amount_signed"],
            "certificate_recoveries_of_defaulted_receivables_usd": source["certificate_recoveries_of_defaulted_receivables"],
            "certificate_principal_recoveries_usd": source["certificate_principal_recoveries_of_defaulted_receivables"],
            "asset_minus_certificate_recovery_usd": str(
                Decimal(source["asset_recovered_amount_signed"])
                - Decimal(source["certificate_recoveries_of_defaulted_receivables"])
            ),
            "recovery_current_amount_tie": source["ties"]["recovered_amount_matches_current_total_recoveries"],
            "recovery_principal_amount_tie": source["ties"]["recovered_amount_matches_principal_recoveries"],
            "certificate_monthly_net_losses_usd": source["certificate_performance_kpis"]["monthly_net_losses"],
            "certificate_current_net_loss_ratio_pct": source["certificate_performance_kpis"]["current_net_loss_ratio_pct"],
            "certificate_cumulative_net_losses_usd": source["certificate_performance_kpis"]["cumulative_net_losses"],
            "monthly_net_loss_identity_exact": source["monthly_net_loss_identity_exact"],
            "cumulative_net_loss_identity_exact": source["cumulative_net_loss_identity_exact"],
            "dpd_literal_exact_fields": dpd_row["tieouts"]["literal"]["exact_field_checks"],
            "dpd_total_field_checks": dpd_row["tieouts"]["literal"]["total_checks"],
            "dpd_shifted_exact_fields_diagnostic_only": dpd_row["tieouts"]["shifted"]["exact_field_checks"],
        }
        for label, suffix in DPD_LABELS.items():
            bucket = source["delinquency_buckets"][label]
            row[f"dpd_{suffix}_count_delta"] = bucket["count_delta"]
            row[f"dpd_{suffix}_balance_delta_usd"] = bucket["balance_delta"]
            row[f"dpd_{suffix}_count_exact"] = bucket["count_exact"]
            row[f"dpd_{suffix}_balance_exact"] = bucket["balance_exact"]

        event_detail = event_by_month.get(month)
        if event_detail:
            if event_detail["report_date"] != source["report_date"]:
                raise ValueError(f"Event audit report date mismatch for {month}")
            if int(event_detail["first_code4_count"]) != int(source["asset_first_code4_events"]):
                raise ValueError(f"First-code-4 count cross-audit mismatch for {month}")
            row.update({
                "focus_event_audit_present": True,
                "asset_positive_chargeoff_row_count_focus": event_detail["asset_positive_chargeoff_count"],
                "first_code4_repeated_count_focus": event_detail["repeated_code4_count"],
                "first_code4_repeated_amount_usd_focus": event_detail["repeated_code4_chargeoff_amount"],
                "first_code4_zero_amount_count_focus": event_detail["first_code4_zero_chargeoff_count"],
                "positive_chargeoff_without_code4_count_focus": event_detail["positive_chargeoff_without_code4_count"],
            })
        else:
            row.update({
                "focus_event_audit_present": False,
                "asset_positive_chargeoff_row_count_focus": "",
                "first_code4_repeated_count_focus": "",
                "first_code4_repeated_amount_usd_focus": "",
                "first_code4_zero_amount_count_focus": "",
                "positive_chargeoff_without_code4_count_focus": "",
            })

        recovery_detail = recovery_by_date.get(source["report_date"])
        if recovery_detail:
            if Decimal(recovery_detail["asset_recovered_signed"]) != Decimal(source["asset_recovered_amount_signed"]):
                raise ValueError(f"Recovery audit amount mismatch for {month}")
            if Decimal(recovery_detail["certificate_recoveries"]) != Decimal(source["certificate_recoveries_of_defaulted_receivables"]):
                raise ValueError(f"Recovery audit certificate mismatch for {month}")
            row["positive_recovery_row_months_with_prior_code4"] = recovery_detail["positive_recovery_row_months"]["code4_elsewhere_in_panel"]
            row["positive_recovery_amount_on_prior_code4_assets_usd"] = recovery_detail["positive_recovery_amount_by_code4_history"]["code4_elsewhere_in_panel"]
            row["negative_recovery_rows_focus"] = recovery_detail["negative_recovery_rows"]
        else:
            row["positive_recovery_row_months_with_prior_code4"] = ""
            row["positive_recovery_amount_on_prior_code4_assets_usd"] = ""
            row["negative_recovery_rows_focus"] = ""

        rows.append(row)

    if len(rows) != 23 or len({row["report_date"] for row in rows}) != 23:
        raise ValueError("Expected 23 unique Nissan reporting periods")
    july = next(row for row in rows if row["report_date"] == "2025-07-31")
    june = next(row for row in rows if row["report_date"] == "2025-06-30")
    august = next(row for row in rows if row["report_date"] == "2025-08-31")
    if (july["asset_chargeoff_event_count"], july["certificate_defaulted_receivables_count"], july["asset_chargeoff_amount_positive_usd"], july["certificate_gross_defaulted_principal_signed_usd"]) != (36, 1, "655185.56000000", "-59000.49"):
        raise ValueError("July 2025 charge-off exception no longer matches the pinned audit")
    if june["dpd_literal_exact_fields"] != 2 or june["dpd_shifted_exact_fields_diagnostic_only"] != 8:
        raise ValueError("June 2025 DPD diagnostic no longer matches the pinned audit")
    if (august["asset_chargeoff_event_count"], august["certificate_defaulted_receivables_count"], august["first_code4_event_count"]) != (54, 54, 24):
        raise ValueError("August 2025 counterexample no longer matches the pinned audit")

    recovery_exceptions = [row for row in rows if Decimal(row["asset_minus_certificate_recovery_usd"]) != ZERO]
    recovery_delta = sum((Decimal(row["asset_minus_certificate_recovery_usd"]) for row in rows), ZERO)
    dpd_literal = int(dpd["aggregate_exact_checks"]["literal"])
    dpd_shifted = int(dpd["aggregate_exact_checks"]["shifted"])
    if len(recovery_exceptions) != 6 or recovery_delta != Decimal("8859.23"):
        raise ValueError("Six-period recovery exception bridge changed")
    if (dpd_literal, dpd_shifted) != (178, 86):
        raise ValueError("Full-panel DPD comparison changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / CSV_NAME
    fields = list(rows[0])
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    july_event = next(item for item in event["periods"].values() if item["report_date"] == "2025-07-31")
    june_bucket_deltas = june
    receipt = {
        "status": "PASS",
        "dataset": "Nissan Auto Receivables 2024-B monthly ABS-EE / 10-D exception ledger",
        "period_count": 23,
        "source_scope": {"asset_month_observations": panel["row_month_observations"], "asset_keys_seen": panel["unique_asset_keys_seen"], "report_start": cert["report_start"], "report_end": cert["report_end"]},
        "summary": {
            "pool_balance_exact_periods": cert["check_counts"]["pool_balance_exact"],
            "positive_balance_count_exact_periods": cert["check_counts"]["positive_balance_count_matches"],
            "chargeoff_event_count_exact_periods": cert["check_counts"]["chargeoff_event_count_matches"],
            "chargeoff_amount_exact_periods": cert["check_counts"]["chargeoff_amount_matches_gross_defaulted_principal"],
            "first_code4_count_exact_periods": cert["check_counts"]["first_code4_event_count_matches_certificate"],
            "first_code4_amount_exact_periods": cert["check_counts"]["first_code4_chargeoff_amount_matches_certificate"],
            "recovery_exact_periods": cert["check_counts"]["recovered_amount_matches_current_total_recoveries"],
            "recovery_exception_periods": len(recovery_exceptions),
            "recovery_signed_residual_total_usd": str(recovery_delta),
            "dpd_literal_exact_fields": dpd_literal,
            "dpd_total_fields": 184,
            "dpd_shifted_exact_fields_diagnostic_only": dpd_shifted,
            "june_2025_dpd_literal_checks": june["dpd_literal_exact_fields"],
            "june_2025_dpd_shifted_checks_diagnostic_only": june["dpd_shifted_exact_fields_diagnostic_only"],
            "july_2025_asset_chargeoff_event_count": july["asset_chargeoff_event_count"],
            "july_2025_certificate_defaulted_receivables": july["certificate_defaulted_receivables_count"],
            "july_2025_asset_chargeoff_amount_usd": july["asset_chargeoff_amount_positive_usd"],
            "july_2025_certificate_gross_defaulted_principal_signed_usd": july["certificate_gross_defaulted_principal_signed_usd"],
            "july_2025_first_code4_count": july_event["first_code4_count"],
            "july_2025_repeated_code4_count": july_event["repeated_code4_count"],
            "july_2025_repeated_code4_chargeoff_amount_usd": july_event["repeated_code4_chargeoff_amount"],
            "july_2025_certificate_monthly_net_losses_usd": july_event["certificate_monthly_net_losses"],
            "july_2025_certificate_current_net_loss_ratio_pct": july_event["certificate_current_net_loss_ratio_pct"],
            "august_2025_positive_chargeoff_count_matches_certificate": august["asset_chargeoff_event_count"] == august["certificate_defaulted_receivables_count"],
            "august_2025_first_code4_count": august["first_code4_event_count"],
            "june_2025_dpd_bucket_deltas": {name: {"count": june[f"dpd_{suffix}_count_delta"], "balance_usd": june[f"dpd_{suffix}_balance_delta_usd"]} for name, suffix in DPD_LABELS.items()},
        },
        "method": "Use audited month-level aggregate inputs; preserve source signs. Reconcile each candidate event definition separately. DPD shifted-boundary results are diagnostic only and never replace literal bucket deltas. Recovery delta = ABS-EE recoveredAmount aggregate minus certificate Recoveries of Defaulted Receivables. Exact Decimal sums; no labels or residuals are imputed.",
        "current_sec_submissions_check": {
            "checked_on": "2026-10-17",
            "endpoint": "https://data.sec.gov/submissions/CIK0002035264.json",
            "latest_filing_date": "2026-09-25",
            "recent_submission_rows": 57,
            "july_2025_report_date_amendments": 0,
            "july_pair": [
                {"form": "ABS-EE", "accession": "0000950131-25-003344", "filing_date": "2025-08-20", "report_date": "2025-07-31"},
                {"form": "10-D", "accession": "0001193125-25-187356", "filing_date": "2025-08-25", "report_date": "2025-07-31"},
            ],
            "limitation": "No 10-D/A or ABS-EE/A for report date 2025-07-31 was present in the current submissions response; this does not prove that no servicer-side adjustment or undocumented classification exists.",
        },
        "private_audit_evidence": evidence,
        "csv_file": CSV_NAME,
        "csv_sha256": sha256(csv_path),
        "visibility": "public aggregate only; no asset identifiers or borrower rows",
        "loan_level_rows_published": False,
        "forecast_or_imputation_used": False,
        "root_cause_resolved": False,
    }
    (output_dir / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True, help="Private CreditAtlas workspace on D:")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs" / "data")
    args = parser.parse_args()
    receipt = build(args.workspace_root, args.output_dir)
    print(json.dumps({"status": receipt["status"], "summary": receipt["summary"], "csv_sha256": receipt["csv_sha256"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
