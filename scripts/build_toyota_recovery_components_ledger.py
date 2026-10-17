"""Build a public, monthly aggregate recovery-component bridge for two Toyota ABS deals.

Only month-level totals and source filing references are emitted. Asset identifiers and
loan-level rows remain in the private workspace.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import html
import hashlib
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_toyota_2022b_certificate_tieout import TableParser, decimal, profile_certificate  # noqa: E402


DEALS = {
    "2022-B": {
        "audit_id": "toyota-2022b-certificate-tieout-cec933ed357e",
        "source_id": "toyota-2022b-10d-certificates-941fa44791c8",
        "audit_status": "TOYOTA_2022B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED",
        "source_status": "SEC_OFFICIAL_TOYOTA_2022B_10D_CERTIFICATES_ACQUIRED",
        "source_receipt_key": "certificate_receipt",
        "issuer_cik": "1914281",
    },
    "2024-B": {
        "audit_id": "toyota-2024b-certificate-tieout-6223784d25dd",
        "source_id": "toyota-2024b-validation-panel-5286fb3cae94",
        "audit_status": "TOYOTA_2024B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED",
        "source_status": "SEC_OFFICIAL_TOYOTA_2024B_PAIRED_HISTORY_ACQUIRED",
        "source_receipt_key": "history_receipt",
        "issuer_cik": "2012786",
    },
}
ZERO = Decimal("0.00")
CENT = Decimal("0.01")
CSV_NAME = "toyota-recovery-components-80-periods.csv"
RECEIPT_NAME = "toyota-recovery-components-80-periods-receipt.json"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def contained(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("A Toyota audit or source path escaped the selected D: workspace")
    return candidate


def _linear_quantile(values: list[Decimal], probability: Decimal) -> Decimal | None:
    """Return the Type-7 linear-interpolated quantile for exact Decimal inputs."""
    if not values:
        return None
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _percent(numerator: Decimal, denominator: Decimal) -> str | None:
    if denominator == ZERO:
        return None
    return str((numerator / denominator * Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP))


def summarize_reconciliation(rows: list[dict[str, str]]) -> dict:
    """Create aggregate-only diagnostics without interpreting residual causes."""

    def distribution(selected: list[dict[str, str]]) -> dict:
        selected_unresolved = [row for row in selected if row["recovery_reconciliation_status"] == "UNRESOLVED"]
        values = [Decimal(row["asset_minus_certificate_recovery_delta"]) for row in selected_unresolved]
        amount = sum((Decimal(row["asset_recovered_amount_signed"]) for row in selected), ZERO)
        delta = sum((Decimal(row["asset_minus_certificate_recovery_delta"]) for row in selected), ZERO)
        nonzero_denominator_shares = [
            Decimal(row["asset_minus_certificate_recovery_delta"])
            / Decimal(row["asset_recovered_amount_signed"])
            * Decimal("100")
            for row in selected_unresolved
            if Decimal(row["asset_recovered_amount_signed"]) != ZERO
        ]
        def q(probability: Decimal) -> Decimal | None:
            return _linear_quantile(values, probability)
        unresolved_total = sum(values, ZERO)
        top_five_share = (
            _percent(sum(sorted(values, reverse=True)[:5], ZERO), unresolved_total)
            if unresolved_total > ZERO and all(value >= ZERO for value in values)
            else None
        )
        return {
            "periods": len(selected),
            "ties": sum(row["recovery_reconciliation_status"] == "TIED" for row in selected),
            "periods_with_zero_abs_ee_recovered_amount": sum(
                Decimal(row["asset_recovered_amount_signed"]) == ZERO for row in selected
            ),
            "unresolved_periods": len(selected_unresolved),
            "positive_unresolved_periods": sum(value > ZERO for value in values),
            "negative_unresolved_periods": sum(value < ZERO for value in values),
            "unresolved_residual_usd": str(unresolved_total),
            "residual_share_of_abs_ee_recovered_amount_percent": _percent(delta, amount),
            "unresolved_residual_quantiles_usd": {
                "minimum": str(min(values)) if values else None,
                "p25": str(q(Decimal("0.25")).quantize(CENT, rounding=ROUND_HALF_UP)) if values else None,
                "median": str(q(Decimal("0.50")).quantize(CENT, rounding=ROUND_HALF_UP)) if values else None,
                "p75": str(q(Decimal("0.75")).quantize(CENT, rounding=ROUND_HALF_UP)) if values else None,
                "maximum": str(max(values)) if values else None,
            },
            "top_five_unresolved_share_of_unresolved_residual_percent": top_five_share,
            "unresolved_periods_with_zero_abs_ee_recovered_amount": sum(
                Decimal(row["asset_recovered_amount_signed"]) == ZERO for row in selected_unresolved
            ),
            "per_period_unresolved_residual_share_of_abs_ee_amount_percent": {
                "eligible_periods": len(nonzero_denominator_shares),
                "median": str(_linear_quantile(nonzero_denominator_shares, Decimal("0.50")).quantize(CENT, rounding=ROUND_HALF_UP)) if nonzero_denominator_shares else None,
                "p75": str(_linear_quantile(nonzero_denominator_shares, Decimal("0.75")).quantize(CENT, rounding=ROUND_HALF_UP)) if nonzero_denominator_shares else None,
            },
        }

    by_deal = {
        deal: distribution([row for row in rows if row["deal"] == deal])
        for deal in sorted({row["deal"] for row in rows})
    }
    by_report_year = []
    for year in sorted({row["report_month"][:4] for row in rows}):
        selected = [row for row in rows if row["report_month"].startswith(year)]
        by_report_year.append({"report_year": year, **distribution(selected)})

    return {
        "scope_note": "Descriptive reconciliation diagnostics only; a residual ratio is not a recovery rate, LGD, PD, loss estimate, or causal attribution.",
        "quantile_method": "Hyndman-Fan Type 7 linear interpolation: h=1+(n-1)p; interpolated dollar outputs rounded to cents using ROUND_HALF_UP.",
        "overall": distribution(rows),
        "by_deal": by_deal,
        "by_report_year_combined_deals": by_report_year,
    }


def first_numeric_field(path: Path, label_prefix: str) -> tuple[Decimal | None, bool]:
    parser = TableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    wanted = re.sub(r"\s+", "", label_prefix).casefold()
    for table in parser.tables:
        for row in table:
            if not row or not re.sub(r"\s+", "", row[0]).casefold().startswith(wanted):
                continue
            values = [decimal(cell) for cell in row[1:]]
            values = [value for value in values if value is not None]
            return (values[0] if values else None), True
    return None, False


def collection_period(path: Path) -> tuple[str, str, int]:
    text = html.unescape(path.read_text(encoding="utf-8", errors="replace")).replace("\u00a0", " ")
    match = re.search(
        r"Collection Period\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+through\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"Collection-period dates are missing from {path.name}")
    start = datetime.strptime(match.group(1), "%B %d, %Y").date()
    end = datetime.strptime(match.group(2), "%B %d, %Y").date()
    if end < start:
        raise ValueError(f"Collection-period end precedes start in {path.name}")
    return start.isoformat(), end.isoformat(), (end - start).days + 1


def build(workspace_root: Path, output_dir: Path) -> dict:
    workspace_root = workspace_root.resolve()
    output_dir = output_dir.resolve()
    if workspace_root.drive.upper() != "D:" or output_dir.drive.upper() != "D:":
        raise ValueError("Workspace and output must remain on D:")

    rows: list[dict[str, str]] = []
    audit_evidence: dict[str, dict] = {}
    for deal, config in DEALS.items():
        audit_dir = contained(workspace_root, "artifacts", "private", config["audit_id"])
        audit_path = contained(audit_dir, "audit.json")
        audit_receipt_path = contained(audit_dir, "receipt.json")
        audit = read_json(audit_path)
        audit_receipt = read_json(audit_receipt_path)
        if audit.get("status") != config["audit_status"] or audit_receipt.get("periods") != audit.get("period_count"):
            raise ValueError(f"Unexpected certificate tie-out audit for Toyota {deal}")
        if sha256(audit_path) != audit_receipt.get("audit_sha256"):
            raise ValueError(f"Toyota {deal} audit receipt hash does not match audit.json")

        source_dir = contained(workspace_root, "data", "private", "structured", config["source_id"])
        source_receipt_path = contained(source_dir, "acquisition-complete.json")
        source = read_json(source_receipt_path)
        if source.get("status") != config["source_status"]:
            raise ValueError(f"Unexpected acquisition receipt for Toyota {deal}")
        if sha256(source_receipt_path) != audit.get("source_sha256", {}).get(config["source_receipt_key"]):
            raise ValueError(f"Toyota {deal} acquisition receipt differs from certificate tie-out evidence")

        source_by_month = {row["report_date"][:7]: row for row in source["reports"]}
        audit_periods = {row["report_date"][:7]: row for row in audit["periods"]}
        if len(source_by_month) != audit.get("period_count") or set(source_by_month) != set(audit_periods):
            raise ValueError(f"Toyota {deal} source and audit months do not align")

        audit_evidence[deal] = {
            "audit_status": audit["status"],
            "audit_sha256": sha256(audit_path),
            "audit_receipt_sha256": sha256(audit_receipt_path),
            "acquisition_receipt_sha256": sha256(source_receipt_path),
            "periods": len(audit_periods),
        }
        for month in sorted(audit_periods):
            source_report = source_by_month[month]
            audit_period = audit_periods[month]
            if deal == "2022-B":
                certificate_meta = source_report["certificate"]
                abs_ee_accession = audit_period.get("abs_ee_accession", "")
                filing_date = source_report.get("filing_date", "")
            else:
                certificate_meta = source_report["10d"]["ex99_1"]
                abs_ee_accession = source_report["abs_ee"]["accession"]
                filing_date = source_report["10d"].get("filing_date", "")
            certificate_path = contained(source_dir, certificate_meta["file"])
            certificate_sha = sha256(certificate_path)
            if certificate_sha != certificate_meta.get("sha256"):
                raise ValueError(f"Toyota {deal} {month} certificate hash mismatch")

            certificate = profile_certificate(certificate_path)
            period_start, period_end, calendar_days = collection_period(certificate_path)
            repurchased_prev, repurchase_row_present = first_numeric_field(
                certificate_path, "Principal of Repurchased Contracts, previously charged-off"
            )
            if not repurchase_row_present or repurchased_prev is None:
                raise ValueError(f"Toyota {deal} {month} certificate lacks a parseable repurchase field")

            asset_recovered = Decimal(audit_period["asset_recovered_amount_signed"])
            audited_aggregate = Decimal(audit_period["certificate_aggregate_net_liquidation_proceeds"])
            gross = Decimal(certificate["Gross Principal of Liquidated Receivables"])
            net_liquidation = Decimal(certificate["Net Liquidation Proceeds Received During the Collection Period"])
            prior_recoveries = Decimal(certificate["Recoveries on Previously Liquidated Contracts"])
            aggregate = Decimal(certificate["Aggregate Net Liquidation Proceeds"])
            net_credit_losses = Decimal(certificate["Net Credit Losses"])
            if aggregate != audited_aggregate:
                raise ValueError(f"Toyota {deal} {month} parsed certificate value differs from audit")

            component_identity_delta = aggregate - (-(net_liquidation + prior_recoveries))
            net_loss_identity_delta = net_credit_losses - (gross + repurchased_prev + net_liquidation + prior_recoveries)
            recovery_delta = asset_recovered - aggregate
            row = {
                "exception_id": f"TOYOTA-{deal}-{month}",
                "deal": deal,
                "report_month": month,
                "report_date": audit_period["report_date"],
                "collection_period_start": period_start,
                "collection_period_end": period_end,
                "calendar_days_in_collection_period": str(calendar_days),
                "filing_date": filing_date or audit_period.get("filing_date", ""),
                "abs_ee_accession": abs_ee_accession,
                "ten_d_accession": source_report.get("10d", {}).get("accession", source_report.get("accession", "")),
                "certificate_url": certificate_meta.get("url", ""),
                "certificate_sha256": certificate_sha,
                "asset_recovered_amount_signed": str(asset_recovered),
                "certificate_net_liquidation_proceeds_signed": str(net_liquidation),
                "certificate_recoveries_previously_liquidated_signed": str(prior_recoveries),
                "certificate_aggregate_net_liquidation_proceeds": str(aggregate),
                "certificate_gross_principal_liquidated": str(gross),
                "certificate_repurchased_previously_charged_off_signed": str(repurchased_prev),
                "certificate_net_credit_losses": str(net_credit_losses),
                "certificate_aggregate_formula_delta": str(component_identity_delta),
                "certificate_net_loss_formula_delta": str(net_loss_identity_delta),
                "asset_minus_certificate_recovery_delta": str(recovery_delta),
                "certificate_component_identity_status": "PASS" if component_identity_delta == ZERO else "FAIL",
                "certificate_net_loss_identity_status": "PASS" if net_loss_identity_delta == ZERO else "FAIL",
                "recovery_reconciliation_status": "TIED" if recovery_delta == ZERO else "UNRESOLVED",
                "exception_note": "Residual retained; public certificate sources do not attribute this ABS-EE aggregate delta to a timing, population, correction, or classification component.",
                "loan_level_rows_published": "No",
                "forecast_or_imputation_used": "No",
            }
            rows.append(row)

    rows.sort(key=lambda row: (row["deal"], row["report_date"]))
    if len(rows) != 80:
        raise ValueError(f"Expected 80 paired Toyota reporting periods; found {len(rows)}")
    if any(row["certificate_component_identity_status"] != "PASS" for row in rows):
        raise ValueError("A certificate aggregate-proceeds identity failed")
    if any(row["certificate_net_loss_identity_status"] != "PASS" for row in rows):
        raise ValueError("A certificate net-loss component identity failed")

    summary = {}
    for deal in DEALS:
        selected = [row for row in rows if row["deal"] == deal]
        delta = sum((Decimal(row["asset_minus_certificate_recovery_delta"]) for row in selected), ZERO)
        summary[deal] = {
            "periods": len(selected),
            "recovery_ties": sum(row["recovery_reconciliation_status"] == "TIED" for row in selected),
            "unresolved_periods": sum(row["recovery_reconciliation_status"] == "UNRESOLVED" for row in selected),
            "asset_recovered_amount_signed_total": str(sum((Decimal(row["asset_recovered_amount_signed"]) for row in selected), ZERO)),
            "certificate_aggregate_proceeds_total": str(sum((Decimal(row["certificate_aggregate_net_liquidation_proceeds"]) for row in selected), ZERO)),
            "signed_residual_total": str(delta),
            "all_unresolved_residuals_nonnegative": all(Decimal(row["asset_minus_certificate_recovery_delta"]) > ZERO for row in selected if row["recovery_reconciliation_status"] == "UNRESOLVED"),
            "maximum_unresolved_monthly_residual": str(max((Decimal(row["asset_minus_certificate_recovery_delta"]) for row in selected), default=ZERO)),
            "certificate_component_identity_passes": len(selected),
            "certificate_net_loss_identity_passes": len(selected),
        }

    reconciliation_diagnostics = summarize_reconciliation(rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / CSV_NAME
    fields = list(rows[0])
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    receipt = {
        "status": "PASS",
        "dataset": "Toyota ABS-EE to SEC 10-D recovery component exception ledger",
        "period_count": len(rows),
        "deal_summary": summary,
        "aggregate_summary": {
            "periods": len(rows),
            "recovery_ties": sum(row["recovery_reconciliation_status"] == "TIED" for row in rows),
            "unresolved_periods": sum(row["recovery_reconciliation_status"] == "UNRESOLVED" for row in rows),
            "signed_residual_total": str(sum((Decimal(row["asset_minus_certificate_recovery_delta"]) for row in rows), ZERO)),
            "component_formula_passes": sum(row["certificate_component_identity_status"] == "PASS" for row in rows),
            "net_loss_formula_passes": sum(row["certificate_net_loss_identity_status"] == "PASS" for row in rows),
        },
        "reconciliation_diagnostics": reconciliation_diagnostics,
        "field_definitions": {
            "asset_recovered_amount_signed": "Monthly sum of ABS-EE EX-102 recoveredAmount from the receipt-bound existing audit; EX-103 says it covers amounts recovered on a Defaulted Receivable during the reporting period and includes repossession proceeds.",
            "certificate_net_liquidation_proceeds_signed": "Current-period signed row from the SEC Servicer's Certificate; proceeds appear negative in its liquidations table.",
            "certificate_recoveries_previously_liquidated_signed": "Current-period signed row for recoveries on previously liquidated contracts.",
            "certificate_aggregate_net_liquidation_proceeds": "Positive collection amount. Exact identity checked as the negated sum of the two signed liquidation rows.",
            "asset_minus_certificate_recovery_delta": "ABS-EE recoveredAmount sum less certificate Aggregate Net Liquidation Proceeds; no residual is allocated or forced to zero.",
        },
        "method": "Exact Decimal arithmetic on source values. Certificate component identities are checked independently from the ABS-EE-to-certificate recovery residual. Missing values are not filled; no recovery rate, LGD, PD or forecast is computed.",
        "limitations": [
            "The two Toyota trusts share issuer/servicer family and are not two independent issuers.",
            "All month-level ABS-EE versus certificate recovery residuals remain unresolved unless tied exactly; this ledger does not infer the cause.",
            "The 2024-B certificate row and current-period recoveries are not assigned to asset-level certificate buckets without transaction-level evidence.",
            "No asset identifiers or loan-level records are included in the output.",
        ],
        "deal_evidence": audit_evidence,
        "csv_file": CSV_NAME,
        "csv_sha256": sha256(csv_path),
        "visibility": "public aggregate only",
        "forecast_or_imputation_used": False,
        "loan_level_rows_published": False,
    }
    receipt_path = output_dir / RECEIPT_NAME
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs" / "data")
    args = parser.parse_args()
    result = build(args.workspace_root, args.output_dir)
    print(json.dumps({"status": result["status"], "periods": result["period_count"], "summary": result["aggregate_summary"], "csv_sha256": result["csv_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
