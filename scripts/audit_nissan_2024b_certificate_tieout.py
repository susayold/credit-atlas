"""Reconcile Nissan Auto Receivables 2024-B ABS-EE snapshots to SEC 10-D certificates."""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pyarrow.parquet as pq

from audit_toyota_2022b_certificate_tieout import TableParser

def decimal(value: object) -> Decimal | None:
    """Parse SEC display amounts without discarding a leading minus sign."""
    if value is None:
        return None
    text = str(value).strip().replace("\u00a0", " ")
    if not text:
        return None
    negative = "(" in text or text.startswith(("-", "−"))
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned:
        return None
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -amount if negative else amount
from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new

ROOT = Path(__file__).resolve().parents[1]
HISTORY_ID = "nissan-2024b-validation-panel-7cd3605b4e07"
PANEL_ID = "nissan-2024b-validation-panel-9534e22c34fc"
ZERO = Decimal("0")
BUCKETS = ("31-60 Days Delinquent", "61-90 Days Delinquent",
           "91-120 Days Delinquent", "More than 120 Days")


def cells(row: list[str]) -> list[Decimal]:
    return [number for value in row[1:] if (number := decimal(value)) is not None]


def find_row(rows: list[list[str]], label: str) -> list[str]:
    found = [row for row in rows if row and row[0].strip() == label]
    if len(found) != 1:
        raise ValueError(f"Expected one certificate row {label!r}; found {len(found)}")
    return found[0]


def profile_certificate(path: Path) -> dict:
    parser = TableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    tables = parser.tables
    if len(tables) < 5:
        raise ValueError(f"Unexpected Nissan certificate table layout: {path.name}")
    pool_values = cells(find_row(tables[1], "Pool Balance"))
    if len(pool_values) < 4:
        raise ValueError("Pool Balance row lacks initial/begin/end/factor values")
    pool_balance = pool_values[-2]
    default_row = cells(find_row(tables[3], "Principal on Defaulted Receivables"))
    if len(default_row) < 2:
        raise ValueError("Defaulted receivable amount/count missing")
    recoveries = cells(find_row(tables[1], "Recoveries of Defaulted Receivables"))
    principal_recoveries = cells(find_row(tables[3], "Principal Recoveries of Defaulted Receivables"))
    if not recoveries or not principal_recoveries:
        raise ValueError("Nissan collection recovery rows missing")
    balance_rows = tables[1]
    principal_payment_i = next((i for i, row in enumerate(balance_rows)
                                if row and row[0].strip() == "Total Principal Payment"), None)
    if principal_payment_i is None:
        raise ValueError("Collateral balance table has no principal-payment row")
    ending_row = next((row for row in balance_rows[principal_payment_i + 1:]
                       if (not row[0].strip()) and len(cells(row)) >= 2), None)
    if ending_row is None:
        raise ValueError("Collateral balance table has no ending contract count")
    ending_values = cells(ending_row)
    if ending_values[0] != ending_values[0].to_integral_value():
        raise ValueError("Ending contract count is not an integer")
    buckets = {}
    for name in BUCKETS:
        values = cells(find_row(tables[4], name))
        if len(values) < 2:
            raise ValueError(f"Delinquency amount/count missing: {name}")
        buckets[name] = {"balance": str(values[0]), "contract_count": int(values[1])}
    monthly_net_loss_row = find_row(tables[3], "Monthly Net Losses")
    monthly_net_loss_values = cells(monthly_net_loss_row)
    if not monthly_net_loss_values:
        raise ValueError("Monthly net loss amount missing")
    monthly_net_loss = monthly_net_loss_values[0]
    if any("(" in value for value in monthly_net_loss_row[1:]):
        monthly_net_loss = -abs(monthly_net_loss)

    def first_value(table: list[list[str]], label: str) -> Decimal:
        values = cells(find_row(table, label))
        if not values:
            raise ValueError(f"Certificate numeric value missing: {label}")
        return values[0]

    def answer(table: list[list[str]], label: str) -> str:
        values = [value.strip() for value in find_row(table, label)[1:] if value.strip()]
        if len(values) != 1:
            raise ValueError(f"Certificate answer missing or ambiguous: {label}")
        return values[0]

    performance = {
        "monthly_net_losses": str(monthly_net_loss),
        "current_net_loss_ratio_pct": str(first_value(tables[3], "Net Loss Ratio for Current Collection Period")),
        "four_month_average_net_loss_ratio_pct": str(first_value(tables[3], "Four-Month Average Net Loss Ratio")),
        "cumulative_net_losses": str(first_value(tables[3], "Cumulative Net Losses for all Periods")),
        "delinquency_percentage_pct": str(first_value(tables[4], "Delinquency Percentage")),
        "delinquency_trigger_pct": str(first_value(tables[4], "Delinquency Trigger")),
        "delinquency_trigger_exceeded": answer(tables[4], "Does the Delinquency Percentage exceed the Delinquency Trigger?"),
        "extension_principal_balance": str(first_value(tables[4], "Principal Balance of Extensions")),
        "extension_count": int(first_value(tables[4], "Number of Extensions")),
        "ending_reserve_balance": str(first_value(tables[3], "Ending Reserve Account Balance")),
    }
    return {"pool_balance": str(pool_balance), "contract_count": int(ending_values[0]),
            "gross_defaulted_principal": str(default_row[0]), "defaulted_count": int(default_row[1]),
            "recoveries_of_defaulted_receivables": str(recoveries[0]),
            "principal_recoveries_of_defaulted_receivables": str(principal_recoveries[0]),
            "delinquency_buckets": buckets, "performance_kpis": performance, "table_count": len(tables)}


def audit() -> Path:
    source = contained(ROOT, f"data/private/structured/{HISTORY_ID}")
    panel = contained(ROOT, f"data/private/derived/{PANEL_ID}")
    source_receipt = read_json(source / "acquisition-complete.json")
    panel_manifest = read_json(panel / "dataset-complete.json")
    if (source_receipt.get("status") != "SEC_OFFICIAL_NISSAN_2024B_PAIRED_HISTORY_ACQUIRED"
            or source_receipt.get("period_count") != 23 or panel_manifest.get("report_count") != 23):
        raise ValueError("Nissan 2024-B source receipts do not meet expected 23-period scope")
    source_by_month = {row["report_date"][:7]: row for row in source_receipt["reports"]}
    panel_by_month = {row["report_date"][:7]: row for row in panel_manifest["parquet_files"]}
    if set(source_by_month) != set(panel_by_month) or len(source_by_month) != 23:
        raise ValueError("Nissan ABS-EE and 10-D periods do not align")

    results, checks, delta_sums, seen_code4_keys = [], Counter(), Counter(), set()
    cumulative_net_loss = ZERO
    for month in sorted(source_by_month):
        src, part = source_by_month[month], panel_by_month[month]
        cert_meta = src["10d"]["ex99_1"]
        cert_path, panel_path = contained(source, cert_meta["file"]), contained(panel, part["file"])
        if sha256(cert_path) != cert_meta["sha256"]:
            raise ValueError(f"Certificate source hash mismatch: {month}")
        if panel_path.stat().st_size != part["bytes"] or sha256(panel_path) != part["sha256"]:
            raise ValueError(f"ABS-EE panel hash/size mismatch: {month}")
        cert = profile_certificate(cert_path)
        perf = cert["performance_kpis"]
        monthly_net_loss = Decimal(perf["monthly_net_losses"])
        monthly_net_loss_identity = (Decimal(cert["gross_defaulted_principal"])
                                     - Decimal(cert["principal_recoveries_of_defaulted_receivables"]))
        cumulative_net_loss += monthly_net_loss
        cumulative_net_loss_identity = cumulative_net_loss == Decimal(perf["cumulative_net_losses"])
        checks["monthly_net_loss_equals_defaulted_principal_less_recoveries"] += int(monthly_net_loss == monthly_net_loss_identity)
        checks["cumulative_net_loss_equals_sum_of_monthly_net_loss"] += int(cumulative_net_loss_identity)
        agg = {"rows": 0, "positive_count": 0, "pool": ZERO, "chargeoff": ZERO,
               "chargeoff_events": 0, "recovered": ZERO,
               "first_code4_events": 0, "first_code4_positive_chargeoff_events": 0,
               "first_code4_chargeoff": ZERO,
               "dpd": {name: {"count": 0, "balance": ZERO} for name in BUCKETS}}
        columns = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount",
                   "chargedoffPrincipalAmount", "recoveredAmount", "zeroBalanceCode",
                   "currentDelinquencyStatus_days_past_due"]
        for batch in pq.ParquetFile(panel_path).iter_batches(batch_size=8192, columns=columns):
            for row in batch.to_pylist():
                agg["rows"] += 1
                balance = decimal(row.get("reportingPeriodActualEndBalanceAmount")) or ZERO
                chargeoff = decimal(row.get("chargedoffPrincipalAmount")) or ZERO
                recovered = decimal(row.get("recoveredAmount")) or ZERO
                key = (row.get("assetTypeNumber"), row.get("assetNumber"))
                codes = {str(value).strip() for value in (row.get("zeroBalanceCode") or [])
                         if value not in (None, "")}
                if "4" in codes and key not in seen_code4_keys:
                    seen_code4_keys.add(key)
                    agg["first_code4_events"] += 1
                    agg["first_code4_positive_chargeoff_events"] += chargeoff > ZERO
                    agg["first_code4_chargeoff"] += chargeoff
                if balance > ZERO:
                    agg["positive_count"] += 1
                    agg["pool"] += balance
                if chargeoff > ZERO:
                    agg["chargeoff_events"] += 1
                    agg["chargeoff"] += chargeoff
                agg["recovered"] += recovered
                dpd = row.get("currentDelinquencyStatus_days_past_due")
                if balance > ZERO and dpd is not None:
                    bucket = (BUCKETS[0] if 31 <= dpd <= 60 else BUCKETS[1] if 61 <= dpd <= 90
                              else BUCKETS[2] if 91 <= dpd <= 120 else BUCKETS[3] if dpd > 120 else None)
                    if bucket:
                        agg["dpd"][bucket]["count"] += 1
                        agg["dpd"][bucket]["balance"] += balance
        if agg["rows"] != part["rows"] or agg["rows"] != part["unique_asset_keys"]:
            raise ValueError(f"ABS-EE row/key count mismatch: {month}")
        ties = {"pool_balance_exact": agg["pool"] == Decimal(cert["pool_balance"]),
                "positive_balance_count_matches": agg["positive_count"] == cert["contract_count"],
                "chargeoff_event_count_matches": agg["chargeoff_events"] == cert["defaulted_count"],
                "chargeoff_amount_matches_gross_defaulted_principal":
                    agg["chargeoff"] == Decimal(cert["gross_defaulted_principal"]),
                "first_code4_event_count_matches_certificate":
                    agg["first_code4_events"] == cert["defaulted_count"],
                "first_code4_chargeoff_amount_matches_certificate":
                    agg["first_code4_chargeoff"] == Decimal(cert["gross_defaulted_principal"]),
                "recovered_amount_matches_current_total_recoveries":
                    agg["recovered"] == Decimal(cert["recoveries_of_defaulted_receivables"]),
                "recovered_amount_matches_principal_recoveries":
                    agg["recovered"] == Decimal(cert["principal_recoveries_of_defaulted_receivables"])}
        checks.update({k: int(v) for k, v in ties.items()})
        delta_sums["pool_balance"] += agg["pool"] - Decimal(cert["pool_balance"])
        delta_sums["chargeoff_amount"] += agg["chargeoff"] - Decimal(cert["gross_defaulted_principal"])
        delta_sums["first_code4_chargeoff_amount"] += agg["first_code4_chargeoff"] - Decimal(cert["gross_defaulted_principal"])
        delta_sums["recovered_vs_total_recoveries"] += agg["recovered"] - Decimal(cert["recoveries_of_defaulted_receivables"])
        delta_sums["recovered_vs_principal_recoveries"] += agg["recovered"] - Decimal(cert["principal_recoveries_of_defaulted_receivables"])
        bucket_results = {}
        for name in BUCKETS:
            reported = cert["delinquency_buckets"][name]
            count_delta = agg["dpd"][name]["count"] - reported["contract_count"]
            amount_delta = agg["dpd"][name]["balance"] - Decimal(reported["balance"])
            bucket_results[name] = {"asset_count": agg["dpd"][name]["count"],
                                    "certificate_count": reported["contract_count"], "count_delta": count_delta,
                                    "asset_balance": str(agg["dpd"][name]["balance"]),
                                    "certificate_balance": reported["balance"], "balance_delta": str(amount_delta),
                                    "count_exact": count_delta == 0, "balance_exact": amount_delta == ZERO}
            checks[f"bucket_{name}_count_exact"] += int(count_delta == 0)
            checks[f"bucket_{name}_balance_exact"] += int(amount_delta == ZERO)
        results.append({"report_date": src["report_date"], "abs_ee_accession": src["abs_ee"]["accession"],
                        "10d_accession": src["10d"]["accession"], "asset_rows": agg["rows"],
                        "positive_balance_count": agg["positive_count"], "certificate_contract_count": cert["contract_count"],
                        "asset_pool_balance": str(agg["pool"]), "certificate_pool_balance": cert["pool_balance"],
                        "asset_chargeoff_events": agg["chargeoff_events"], "certificate_defaulted_receivables": cert["defaulted_count"],
                        "asset_chargeoff_amount": str(agg["chargeoff"]),
                        "certificate_gross_defaulted_principal": cert["gross_defaulted_principal"],
                        "asset_first_code4_events": agg["first_code4_events"],
                        "asset_first_code4_positive_chargeoff_events": agg["first_code4_positive_chargeoff_events"],
                        "asset_first_code4_chargeoff_amount": str(agg["first_code4_chargeoff"]),
                        "asset_recovered_amount_signed": str(agg["recovered"]),
                        "certificate_recoveries_of_defaulted_receivables": cert["recoveries_of_defaulted_receivables"],
                        "certificate_principal_recoveries_of_defaulted_receivables": cert["principal_recoveries_of_defaulted_receivables"],
                        "certificate_performance_kpis": perf,
                        "monthly_net_loss_identity_exact": monthly_net_loss == monthly_net_loss_identity,
                        "cumulative_net_loss_identity_exact": cumulative_net_loss_identity,
                        "ties": ties, "delinquency_buckets": bucket_results})

    result = {"status": "NISSAN_2024B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED",
              "issuer": source_receipt["issuer"], "period_count": len(results),
              "report_start": results[0]["report_date"], "report_end": results[-1]["report_date"],
              "source_ids": {"history": HISTORY_ID, "panel": PANEL_ID},
              "source_sha256": {"history_receipt": sha256(source / "acquisition-complete.json"),
                                "panel_manifest": sha256(panel / "dataset-complete.json")},
              "check_counts": dict(sorted(checks.items())),
              "aggregate_delta_sums": {k: str(v) for k, v in sorted(delta_sums.items())},
              "periods": results,
              "limitations": ["Nissan is a separate issuer/servicer family from Toyota; this is still one Nissan trust and not a representative market sample.",
                              "Certificate maps defaulted principal and observed recovery flows; these do not create origination-time PD/LGD labels.",
                              "`recoveredAmount` is compared separately with total and principal certificate recovery rows; no mapping is assumed if they differ.",
                              "DPD follows Nissan's certificate groups 31-60/61-90/91-120/>120; 0-30 is not a delinquency bucket."],
              "created_at": timestamp(), "visibility": "private", "public_release_approved": False}
    out = contained(ROOT, "artifacts/private/nissan-2024b-certificate-tieout-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": len(results), "check_counts": result["check_counts"],
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "checks": result["check_counts"],
                      "aggregate_delta_sums": result["aggregate_delta_sums"]}))
    return out


if __name__ == "__main__":
    audit()
