"""Build a private, source-tied monthly ABS-EE collateral KPI report."""
from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
PANEL = "data/private/derived/woart-absee-panel-91efe12963d6"
PANEL_AUDIT = "artifacts/private/woart-absee-panel-audit-f689e9c70199/audit.json"
DELINQUENCY_AUDIT = "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/audit.json"
CASE = "artifacts/private/abs-case-fcbaa9573ac3"


def as_decimal(value: str | None, *, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"Required reported metric is unavailable: {label}")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError(f"Non-finite metric: {label}")
    return result


def rate(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    return None if denominator == 0 else numerator / denominator


def audit() -> Path:
    panel_dir = contained(ROOT, PANEL)
    manifest_path = contained(panel_dir, "dataset-complete.json")
    manifest = read_json(manifest_path)
    panel_audit = read_json(contained(ROOT, PANEL_AUDIT))
    delinquency = read_json(contained(ROOT, DELINQUENCY_AUDIT))
    case_dir = contained(ROOT, CASE)
    case_receipt_path = contained(case_dir, "case-complete.json")
    case = read_json(case_receipt_path)
    if (manifest.get("status") != "OFFICIAL_ABSEE_RAW_PANEL_PARQUET_BUILT"
            or manifest.get("report_count") != 20 or manifest.get("row_count") != 880773
            or panel_audit.get("status") != "OFFICIAL_PARQUET_PANEL_AND_ADJACENT_STATE_AUDIT_PASS"
            or panel_audit.get("hash_verified_files") != 20
            or delinquency.get("status") != "XSD_DAY_DELINQUENCY_MAPPED_AND_CERTIFICATE_RECONCILED"
            or sum(x["certificate_checks_passed"] for x in delinquency["periods"]) != 200
            or case.get("status") != "ABS_REPORTED_CANONICAL_COMPLETE"
            or case.get("case_id") != "abs-case-fcbaa9573ac3"):
        raise ValueError("Required official panel / certificate audit prerequisite failed")
    for item in case["files"]:
        path = contained(case_dir, item["file"])
        if sha256(path) != item["sha256"]:
            raise ValueError("Canonical certificate case file hash mismatch")

    certificate = {}
    metrics_path = contained(case_dir, "reported_metrics.parquet")
    for row in pq.read_table(metrics_path).to_pylist():
        if row["status"] == "VALUE":
            certificate.setdefault(row["collection_end"], {})[row["metric"]] = row["value"]
    delinquency_by_date = {x["report_date"]: x for x in delinquency["periods"]}
    output_periods = []
    flow_recovery_mismatches = 0
    total_rows = 0

    for item in manifest["parquet_files"]:
        report_date = item["report_date"]
        source_path = contained(panel_dir, item["file"])
        if sha256(source_path) != item["sha256"]:
            raise ValueError(f"Parquet partition hash mismatch: {report_date}")
        metrics = certificate.get(report_date)
        delinquency_period = delinquency_by_date.get(report_date)
        if metrics is None or delinquency_period is None:
            raise ValueError(f"Missing matched certificate or delinquency audit period: {report_date}")
        counts = Counter()
        sums = defaultdict(Decimal)
        fields = ["reportingPeriodActualEndBalanceAmount", "chargedoffPrincipalAmount", "recoveredAmount",
                  "repossessedIndicator", "repossessedProceedsAmount"]
        for batch in pq.ParquetFile(source_path).iter_batches(batch_size=8192, columns=fields):
            for row in batch.to_pylist():
                counts["rows"] += 1
                for field in ["reportingPeriodActualEndBalanceAmount", "chargedoffPrincipalAmount",
                              "recoveredAmount", "repossessedProceedsAmount"]:
                    value = row.get(field)
                    if value is not None:
                        sums[field] += Decimal(value)
                balance = Decimal(row["reportingPeriodActualEndBalanceAmount"])
                counts["positive_balance_assets"] += balance > 0
                counts["zero_balance_assets"] += balance == 0
                counts["negative_balance_assets"] += balance < 0
                counts["chargedoff_amount_observations"] += row["chargedoffPrincipalAmount"] is not None
                counts["negative_recovery_amount_observations"] += (row["recoveredAmount"] is not None
                                                                      and Decimal(row["recoveredAmount"]) < 0)
                counts["repossessed_true_assets"] += row["repossessedIndicator"] == "true"
        total_rows += counts["rows"]

        ending_pool = as_decimal(metrics.get("ending_pool"), label=f"{report_date} ending_pool")
        ending_ysoa = as_decimal(metrics.get("ending_ysoa"), label=f"{report_date} ending_ysoa")
        ending_pool_accounts = as_decimal(metrics.get("ending_pool_accounts"), label=f"{report_date} ending_pool_accounts")
        defaulted = as_decimal(metrics.get("defaulted_receivables"), label=f"{report_date} defaulted_receivables")
        certificate_recoveries = as_decimal(metrics.get("recoveries"), label=f"{report_date} recoveries")
        reported_net_loss = as_decimal(metrics.get("net_losses"), label=f"{report_date} net_losses")
        xml_balance = sums["reportingPeriodActualEndBalanceAmount"]
        chargeoff = sums["chargedoffPrincipalAmount"]
        recovery = sums["recoveredAmount"]
        repo_proceeds = sums["repossessedProceedsAmount"]
        pool_receivables = ending_pool + ending_ysoa
        balance_delta = xml_balance - pool_receivables
        chargeoff_delta = chargeoff - defaulted
        recovery_delta = recovery - certificate_recoveries
        if balance_delta != 0 or chargeoff_delta != 0:
            raise ValueError(f"Critical balance/charge-off tie-out failed for {report_date}")
        flow_recovery_mismatches += recovery_delta != 0

        buckets = delinquency_period["buckets"]
        delinquent_accounts = sum(buckets[key]["accounts"] for key in ("31_60", "61_90", "91_120", "121_plus"))
        delinquent_balance = sum((Decimal(buckets[key]["ending_balance"]) for key in ("31_60", "61_90", "91_120", "121_plus")), Decimal(0))
        delinquent_61_accounts = sum(buckets[key]["accounts"] for key in ("61_90", "91_120", "121_plus"))
        delinquent_61_balance = sum((Decimal(buckets[key]["ending_balance"]) for key in ("61_90", "91_120", "121_plus")), Decimal(0))
        current_pool_31_rate = as_decimal(metrics["delinquent_31_plus_ratio"], label=f"{report_date} 31+ ratio")
        current_pool_61_rate = as_decimal(metrics["delinquent_61_plus_ratio"], label=f"{report_date} 61+ ratio")
        ratio_31_amount = rate(delinquent_balance, pool_receivables)
        ratio_61_amount = rate(delinquent_61_balance, pool_receivables)
        if ratio_31_amount is None or ratio_61_amount is None:
            raise ValueError("Ending pool balance is zero; delinquency denominator unavailable")
        # Certificate ratios are published to 4 decimal places (fraction), so compare within half a displayed unit.
        if abs(ratio_31_amount - current_pool_31_rate) > Decimal("0.00005"):
            raise ValueError(f"31+ bucket ratio exceeds certificate rounding tolerance for {report_date}")
        if abs(ratio_61_amount - current_pool_61_rate) > Decimal("0.00005"):
            raise ValueError(f"61+ bucket ratio exceeds certificate rounding tolerance for {report_date}")

        output_periods.append({
            "report_date": report_date, "accession": item["accession"], "filing_url":
                f"https://www.sec.gov/Archives/edgar/data/2046523/{item['accession']}/index.json",
            "row_month_observations": counts["rows"],
            "ending_pool_balance_usd": str(ending_pool), "ending_ysoa_usd": str(ending_ysoa),
            "certificate_pool_receivables_plus_ysoa_usd": str(pool_receivables),
            "xml_ending_balance_usd": str(xml_balance), "xml_balance_delta_usd": str(balance_delta),
            "certificate_pool_accounts": str(ending_pool_accounts),
            "xml_nonzero_balance_asset_count": counts["positive_balance_assets"] + counts["negative_balance_assets"],
            "xml_account_count_delta": str(Decimal(counts["positive_balance_assets"] + counts["negative_balance_assets"]) - ending_pool_accounts),
            "positive_balance_asset_count": counts["positive_balance_assets"],
            "negative_balance_asset_count": counts["negative_balance_assets"],
            "zero_balance_asset_count": counts["zero_balance_assets"],
            "delinquency": {
                "buckets": buckets,
                "31_plus_accounts": delinquent_accounts, "31_plus_balance_usd": str(delinquent_balance),
                "31_plus_account_rate_vs_certificate_pool_accounts": str(rate(Decimal(delinquent_accounts), ending_pool_accounts)),
                "31_plus_balance_rate_vs_certificate_pool_receivables_plus_ysoa": str(ratio_31_amount),
                "61_plus_accounts": delinquent_61_accounts, "61_plus_balance_usd": str(delinquent_61_balance),
                "61_plus_account_rate_vs_certificate_pool_accounts": str(rate(Decimal(delinquent_61_accounts), ending_pool_accounts)),
                "61_plus_balance_rate_vs_certificate_pool_receivables_plus_ysoa": str(ratio_61_amount),
                "reported_trigger": metrics.get("delinquency_trigger"),
                "certificate_reconciliation_checks_passed": delinquency_period["certificate_checks_passed"],
                "certificate_reconciliation_checks_total": delinquency_period["certificate_checks_total"],
            },
            "performance": {
                "asset_reported_chargeoff_amount_usd": str(chargeoff),
                "certificate_defaulted_receivables_usd": str(defaulted),
                "chargeoff_to_defaulted_receivable_delta_usd": str(chargeoff_delta),
                "asset_reported_recovery_amount_signed_usd": str(recovery),
                "certificate_recoveries_signed_usd": str(certificate_recoveries),
                "recovery_delta_asset_minus_certificate_usd": str(recovery_delta),
                "certificate_net_losses_signed_usd": str(reported_net_loss),
                "asset_reported_repossessed_proceeds_usd": str(repo_proceeds),
                "repossessed_true_assets_at_snapshot": counts["repossessed_true_assets"],
                "chargedoff_amount_observations": counts["chargedoff_amount_observations"],
                "negative_recovery_amount_observations": counts["negative_recovery_amount_observations"],
                "cumulative_net_loss_ratio_to_original_principal": metrics.get("cumulative_net_loss_ratio"),
            },
            "source_checks": {"xml_balance_equals_pool_plus_ysoa": balance_delta == 0,
                "asset_chargeoff_equals_certificate_defaulted_receivables": chargeoff_delta == 0,
                "recovery_tie_out_exact": recovery_delta == 0,
                "recovery_tie_out_note": "Asset-level signed recovery sum is shown beside certificate recovery; no exact tie-out is claimed when delta is non-zero."},
        })

    if total_rows != manifest["row_count"]:
        raise ValueError("Panel row total changed during KPI build")
    out = contained(ROOT, "artifacts/private/woart-absee-official-kpi-report-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    result = {"status": "OFFICIAL_ABSEE_MONTHLY_KPI_REPORT_BUILT", "dataset_id": manifest["dataset_id"],
        "panel_manifest_sha256": sha256(manifest_path), "panel_audit_sha256": sha256(contained(ROOT, PANEL_AUDIT)),
        "delinquency_audit_sha256": sha256(contained(ROOT, DELINQUENCY_AUDIT)),
        "certificate_case_receipt_sha256": sha256(case_receipt_path),
        "certificate_metrics_sha256": sha256(metrics_path), "period_count": len(output_periods),
        "row_month_observations": total_rows, "ending_balance_checks_passed": sum(x["source_checks"]["xml_balance_equals_pool_plus_ysoa"] for x in output_periods),
        "chargeoff_checks_passed": sum(x["source_checks"]["asset_chargeoff_equals_certificate_defaulted_receivables"] for x in output_periods),
        "recovery_exact_tieout_periods": sum(x["source_checks"]["recovery_tie_out_exact"] for x in output_periods),
        "recovery_nonzero_delta_periods": flow_recovery_mismatches, "periods": output_periods,
        "metric_definitions": {"ending_pool_balance_usd": "Certificate reported ending pool balance; exclude YSOA.",
            "certificate_pool_receivables_plus_ysoa_usd": "Pool balance plus yield supplement overcollateralization; XML ending-balance reconciliation basis.",
            "31_plus_balance_rate_vs_certificate_pool_receivables_plus_ysoa": "Sum of certificate-reconciled 31–60, 61–90, 91–120 and 121+ balance divided by ending Pool Balance plus YSOA.",
            "31_plus_account_rate_vs_certificate_pool_accounts": "Sum of 31+ delinquency bucket accounts divided by certificate ending pool accounts.",
            "asset_reported_chargeoff_amount_usd": "Sum of the source field chargedoffPrincipalAmount; exact-ties certificate Defaulted Receivables in this 20-period panel.",
            "asset_reported_recovery_amount_signed_usd": "Signed sum of source field recoveredAmount; displayed beside certificate recovery because it does not exactly tie out in all periods.",
            "row_month_observations": "Repeated monthly asset records; not unique lifetime loans when summed across periods."},
        "limitations": ["Descriptive monitoring of one securitization; not a representative consumer portfolio or application-level PD model.",
            "Certificate trigger is a reported field, not independent confirmation that a legal trigger regime was satisfied.",
            "The 20-period monthly sample is short and vintage/censoring limits must be assessed before forecasting.",
            "Asset recovery and repossession sums do not replace the certificate series; recovery differences remain visible and unexplained.",
            "No causal exit/default labels or future cash-flow forecasts are created."],
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False}
    write_new(out / "kpis.json", result)
    receipt = {"status": result["status"], "kpi_sha256": sha256(out / "kpis.json"),
        "periods": len(output_periods), "rows": total_rows, "balance_checks_passed": result["ending_balance_checks_passed"],
        "chargeoff_checks_passed": result["chargeoff_checks_passed"],
        "recovery_exact_tieout_periods": result["recovery_exact_tieout_periods"],
        "recovery_nonzero_delta_periods": flow_recovery_mismatches,
        "visibility": "private", "public_release_approved": False}
    write_new(out / "receipt.json", receipt)
    print(out)
    print(json.dumps(receipt))
    return out


if __name__ == "__main__":
    audit()
