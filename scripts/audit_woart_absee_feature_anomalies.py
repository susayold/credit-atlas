"""Describe PTI and recovery observations that need qualification before modeling."""
from __future__ import annotations

import json
import sys
import uuid
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "woart-absee-panel-91efe12963d6"


def dec(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def bucket(row: dict) -> str:
    bal = dec(row.get("reportingPeriodActualEndBalanceAmount")) or Decimal(0)
    if bal < 0:
        return "negative_balance"
    if bal == 0:
        return "zero_balance"
    days = row.get("currentDelinquencyStatus_days_past_due")
    if days is None:
        return "positive_balance_dpd_missing"
    if days <= 30:
        return "current_0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    if days <= 120:
        return "91_120"
    return "121_plus"


def code_values(value: object) -> list[str]:
    if value in (None, "", []):
        return ["blank"]
    if isinstance(value, list):
        return [str(v) for v in value] or ["blank"]
    return [str(value)]


def audit() -> Path:
    dataset = contained(ROOT, "data/private/derived/" + DATASET_ID)
    manifest = read_json(dataset / "dataset-complete.json")
    if manifest.get("status") != "OFFICIAL_ABSEE_RAW_PANEL_PARQUET_BUILT" or manifest.get("report_count") != 20:
        raise ValueError("Expected verified official SEC ABS-EE 20-period panel")

    periods = []
    pti_bucket = Counter()
    recovery_bucket = Counter()
    all_pti_keys = set()
    all_recovery_keys = set()
    pti_values = Counter()
    recovery_values = Counter()
    pti_observation_months = Counter()
    recovery_observation_months = Counter()
    recovery_zero_code = Counter()
    pti_zero_code = Counter()
    pti_chargeoff = Counter()
    recovery_chargeoff = Counter()

    for item in manifest["parquet_files"]:
        path = contained(dataset, item["file"])
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError("Panel Parquet hash/size mismatch")
        pti_count = recovery_count = 0
        pti_sum = Decimal(0)
        recovery_sum = Decimal(0)
        pti_thresholds = Counter()
        recovery_negative = Counter()
        recovery_negative_sum = Decimal(0)
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=[
            "assetTypeNumber", "assetNumber", "paymentToIncomePercentage", "recoveredAmount",
            "reportingPeriodActualEndBalanceAmount", "currentDelinquencyStatus_days_past_due",
            "zeroBalanceCode", "chargedoffPrincipalAmount",
        ]):
            for row in batch.to_pylist():
                key = (row["assetTypeNumber"], row["assetNumber"])
                state = bucket(row)
                codes = code_values(row.get("zeroBalanceCode"))
                chargeoff = dec(row.get("chargedoffPrincipalAmount")) or Decimal(0)
                pti = dec(row.get("paymentToIncomePercentage"))
                if pti is not None:
                    pti_count += 1
                    pti_sum += pti
                    pti_thresholds["gt_1"] += pti > 1
                    if pti > 1:
                        all_pti_keys.add(key)
                        pti_values[str(pti)] += 1
                        pti_observation_months[key] += 1
                        pti_bucket[state] += 1
                        pti_zero_code.update(codes)
                        pti_chargeoff["chargeoff_amount_present"] += chargeoff != 0
                        pti_chargeoff["chargeoff_amount_blank_or_zero"] += chargeoff == 0
                recovered = dec(row.get("recoveredAmount"))
                if recovered is not None:
                    recovery_count += 1
                    recovery_sum += recovered
                    if recovered < 0:
                        recovery_negative["rows"] += 1
                        recovery_negative["sum_signed"] += recovered
                        recovery_negative_sum += recovered
                        all_recovery_keys.add(key)
                        recovery_values[str(recovered)] += 1
                        recovery_observation_months[key] += 1
                        recovery_bucket[state] += 1
                        recovery_zero_code.update(codes)
                        recovery_chargeoff["chargeoff_amount_present"] += chargeoff != 0
                        recovery_chargeoff["chargeoff_amount_blank_or_zero"] += chargeoff == 0
        periods.append({
            "report_date": item["report_date"],
            "row_months": item["rows"],
            "pti_present_rows": pti_count,
            "pti_sum_raw_units": str(pti_sum),
            "pti_gt_1_rows": pti_thresholds["gt_1"],
            "pti_gt_1_value_rate": str(Decimal(pti_thresholds["gt_1"]) / Decimal(pti_count)) if pti_count else None,
            "recovered_amount_present_rows": recovery_count,
            "recovered_amount_sum_signed_raw_units": str(recovery_sum),
            "recovered_amount_negative_rows": recovery_negative["rows"],
            "recovered_amount_negative_sum_raw_units": str(recovery_negative_sum),
        })

    # The counts above deduplicate within delinquency-state buckets. Also count union keys explicitly.
    output = {
        "status": "OFFICIAL_ABSEE_FEATURE_ANOMALY_AUDIT_BUILT",
        "dataset_id": DATASET_ID,
        "dataset_receipt_sha256": sha256(dataset / "dataset-complete.json"),
        "period_count": len(periods),
        "row_month_observations": sum(p["row_months"] for p in periods),
        "periods": periods,
        "payment_to_income_gt_1": {
            "row_month_observations": sum(pti_bucket.values()),
            "unique_assets_observed": len(all_pti_keys),
            "unique_assets_with_observation_in_multiple_months": sum(n > 1 for n in pti_observation_months.values()),
            "observation_months_per_asset_max": max(pti_observation_months.values(), default=0),
            "by_delinquency_state": dict(sorted(pti_bucket.items())),
            "by_zero_balance_code": dict(sorted(pti_zero_code.items())),
            "chargeoff_amount_presence": dict(pti_chargeoff),
            "raw_value_frequency_top_20": [{"value": v, "row_months": n} for v, n in pti_values.most_common(20)],
            "interpretation": "XSD-valid decimal values, not proven to be an intentional >100% payment-to-income ratio. Verify the scale and source calculation before defining user-facing percentage bands or model features.",
        },
        "negative_recovered_amount": {
            "row_month_observations": sum(recovery_bucket.values()),
            "unique_assets_observed": len(all_recovery_keys),
            "unique_assets_with_negative_values_in_multiple_months": sum(n > 1 for n in recovery_observation_months.values()),
            "negative_observation_months_per_asset_max": max(recovery_observation_months.values(), default=0),
            "signed_sum_raw_units": str(sum((Decimal(p["recovered_amount_negative_sum_raw_units"]) for p in periods), Decimal(0))),
            "by_delinquency_state": dict(sorted(recovery_bucket.items())),
            "by_zero_balance_code": dict(sorted(recovery_zero_code.items())),
            "chargeoff_amount_presence": dict(recovery_chargeoff),
            "raw_value_frequency_top_20": [{"value": v, "row_months": n} for v, n in recovery_values.most_common(20)],
            "interpretation": "Negative signed recovery observations are retained as reported. Their distribution alone cannot distinguish correction, reversal, servicing adjustment, or economic loss; keep them out of recovery-rate/LGD calculations until source-period semantics are confirmed.",
        },
        "limitations": [
            "Counts are row-month observations unless explicitly labeled unique assets; one loan can recur across monthly filings.",
            "Amounts retain source units and signs; the audit does not reassign negative values or infer causation.",
            "PTI scale is not normalized; values above 1 are flagged, not automatically converted from fraction to percent.",
            "This is one issuer/deal and twenty periods, not a representative training sample.",
        ],
        "created_at": timestamp(),
        "visibility": "private",
        "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/woart-absee-feature-anomaly-audit-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", output)
    write_new(out / "receipt.json", {
        "status": output["status"], "audit_sha256": sha256(out / "audit.json"),
        "periods": output["period_count"], "rows": output["row_month_observations"],
        "pti_gt_1_row_months": output["payment_to_income_gt_1"]["row_month_observations"],
        "pti_gt_1_unique_assets": output["payment_to_income_gt_1"]["unique_assets_observed"],
        "negative_recovery_row_months": output["negative_recovered_amount"]["row_month_observations"],
        "negative_recovery_unique_assets": output["negative_recovered_amount"]["unique_assets_observed"],
        "visibility": "private", "public_release_approved": False,
    })
    print(out)
    print(json.dumps({"status": output["status"], "periods": output["period_count"],
                      "rows": output["row_month_observations"],
                      "pti_gt_1": output["payment_to_income_gt_1"]["row_month_observations"],
                      "pti_assets": output["payment_to_income_gt_1"]["unique_assets_observed"],
                      "negative_recovery": output["negative_recovered_amount"]["row_month_observations"],
                      "recovery_assets": output["negative_recovered_amount"]["unique_assets_observed"]}))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("Usage: audit_woart_absee_feature_anomalies.py")
    audit()
