"""Assess future charge-off target support and censoring for the Toyota 2022-B servicing panel."""
from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "toyota-2022b-absee-panel-1d111a2e0a47"
AUDIT_ID = "toyota-2022b-absee-panel-audit-c9fbf983fa4e"
HORIZONS = (6, 12, 24)
FEATURE_FIELDS = ("obligorCreditScore", "paymentToIncomePercentage", "currentDelinquencyStatus_days_past_due",
                  "reportingPeriodActualEndBalanceAmount", "originalLoanAmount", "remainingTermToMaturityNumber",
                  "vehicleValueAmount", "obligorGeographicLocation")


def decimal(value: object) -> Decimal:
    return Decimal(str(value)) if value not in (None, "") else Decimal(0)


def code_list(value: object) -> list[str]:
    if value in (None, [], ""):
        return []
    return [str(x) for x in value if x not in (None, "")]


def audit() -> Path:
    dataset = contained(ROOT, "data/private/derived/" + DATASET_ID)
    manifest = read_json(dataset / "dataset-complete.json")
    outcome_audit = read_json(contained(ROOT, "artifacts/private/" + AUDIT_ID + "/audit.json"))
    if (manifest.get("status") != "OFFICIAL_TOYOTA_2022B_ABSEE_PANEL_PARQUET_BUILT"
            or manifest.get("report_count") != 51 or outcome_audit.get("period_count") != 51
            or outcome_audit.get("chargeoff_code4_crosscheck", {}).get("unique_positive_chargeoff_events") != 1122
            or outcome_audit.get("chargeoff_code4_crosscheck", {}).get("positive_chargeoff_event_and_first_code4_month_match") != 1122):
        raise ValueError("Toyota 2022-B panel/event audit qualification failed")
    periods = manifest["parquet_files"]

    asset = {}
    left_censored_code4 = set()
    for month_index, item in enumerate(periods):
        path = contained(dataset, item["file"])
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError(f"Panel Parquet hash mismatch for {item['report_date']}")
        cols = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount",
                "chargedoffPrincipalAmount", "zeroBalanceCode"]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=cols):
            for row in batch.to_pylist():
                key = (row["assetTypeNumber"], row["assetNumber"])
                record = asset.setdefault(key, {"first_seen": month_index, "event": None, "competing_exit": None,
                                                "code4_seen": False})
                if decimal(row.get("chargedoffPrincipalAmount")) > 0 and record["event"] is None:
                    record["event"] = month_index
                codes = code_list(row.get("zeroBalanceCode"))
                if "4" in codes:
                    record["code4_seen"] = True
                    if month_index == record["first_seen"] and decimal(row.get("chargedoffPrincipalAmount")) <= 0:
                        left_censored_code4.add(key)
                if (decimal(row.get("reportingPeriodActualEndBalanceAmount")) == 0
                        and any(code in codes for code in ("1", "3"))
                        and record["competing_exit"] is None):
                    record["competing_exit"] = month_index

    target_counts = {str(h): Counter() for h in HORIZONS}
    unique_by_class = {str(h): defaultdict(set) for h in HORIZONS}
    feature_presence = {str(h): Counter() for h in HORIZONS}
    risk_rows = 0
    risk_assets = set()
    ambiguous_simultaneous = set()
    event_assets = set()
    competing_assets = set()
    event_index_by_key = {k: v["event"] for k, v in asset.items()}
    exit_index_by_key = {k: v["competing_exit"] for k, v in asset.items()}
    for key, record in asset.items():
        event_idx, exit_idx = record["event"], record["competing_exit"]
        if event_idx is not None and (exit_idx is None or event_idx < exit_idx):
            event_assets.add(key)
        elif exit_idx is not None and (event_idx is None or exit_idx < event_idx):
            competing_assets.add(key)
        elif event_idx is not None and event_idx == exit_idx:
            ambiguous_simultaneous.add(key)

    for month_index, item in enumerate(periods):
        path = contained(dataset, item["file"])
        cols = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount",
                "chargedoffPrincipalAmount", "zeroBalanceCode", *FEATURE_FIELDS]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=list(dict.fromkeys(cols))):
            for row in batch.to_pylist():
                key = (row["assetTypeNumber"], row["assetNumber"])
                record = asset[key]
                if (decimal(row.get("reportingPeriodActualEndBalanceAmount")) <= 0
                        or key in left_censored_code4 or key in ambiguous_simultaneous):
                    continue
                event_idx = event_index_by_key[key]
                exit_idx = exit_index_by_key[key]
                first_outcome = min((x for x in (event_idx, exit_idx) if x is not None), default=None)
                if first_outcome is not None and first_outcome <= month_index:
                    continue
                risk_rows += 1
                risk_assets.add(key)
                for h in HORIZONS:
                    name = str(h)
                    outcome_idx = month_index + h
                    complete_window = outcome_idx < len(periods)
                    if event_idx is not None and month_index < event_idx <= outcome_idx and (
                            exit_idx is None or event_idx < exit_idx):
                        label = "chargeoff"
                    elif exit_idx is not None and month_index < exit_idx <= outcome_idx and (
                            event_idx is None or exit_idx < event_idx):
                        label = "competing_exit"
                    elif complete_window:
                        label = "no_event_full_horizon"
                    else:
                        label = "right_censored_before_horizon"
                    target_counts[name][label] += 1
                    unique_by_class[name][label].add(key)
                    if complete_window:
                        for field in FEATURE_FIELDS:
                            feature_presence[name][field + ("_present" if row.get(field) not in (None, "") else "_missing")] += 1

    horizons = {}
    for h in HORIZONS:
        name = str(h)
        horizons[name] = {
            "estimand": f"First source-reported charge-off in next {h} monthly reporting periods before code 1/3 zero-balance exit",
            "at_risk_feature_row_months_by_class": dict(sorted(target_counts[name].items())),
            "unique_assets_by_class": {label: len(keys) for label, keys in sorted(unique_by_class[name].items())},
            "feature_missingness_on_full_horizon_rows": dict(sorted(feature_presence[name].items())),
            "labels_qualified_for_training": False,
        }
    result = {
        "status": "TOYOTA_2022B_SERVICING_TARGET_FEASIBILITY_AUDITED",
        "dataset_id": DATASET_ID, "dataset_manifest_sha256": sha256(dataset / "dataset-complete.json"),
        "event_audit_id": AUDIT_ID,
        "period_count": len(periods), "report_start": periods[0]["report_date"],
        "report_end": periods[-1]["report_date"], "unique_asset_keys": len(asset),
        "raw_chargeoff_event_assets": len(event_assets), "competing_exit_assets_before_chargeoff": len(competing_assets),
        "left_censored_code4_assets_at_panel_start": len(left_censored_code4),
        "simultaneous_chargeoff_and_competing_exit_assets": len(ambiguous_simultaneous),
        "positive_balance_at_risk_row_months": risk_rows, "unique_assets_with_at_risk_observations": len(risk_assets),
        "candidate_horizons": horizons,
        "feature_fields_reviewed": list(FEATURE_FIELDS),
        "target_definition": {
            "event": "chargedoffPrincipalAmount > 0; Toyota EX-103 says this is principal balance immediately before a receivable becomes Defaulted during the current reporting period.",
            "competing_exit": "zero ending balance with XSD zeroBalanceCode 1 (prepaid/matured) or 3 (repurchased/replaced).",
            "feature_cutoff": "Feature values from a positive-ending-balance snapshot at month t; future outcomes start at t+1.",
            "not_origination_pd": True,
        },
        "limitations": [
            "This supports a servicing-period risk target, not application/origination PD; features are measured after origination.",
            "One trust is a development sample; split by time and validate on other deals/issuers before performance claims.",
            "ZeroBalanceCode 1 combines prepaid and matured loans; code 3 is a separate competing exit.",
            "Recovery/LGD requires a separate post-chargeoff observation window and maturity/censoring treatment.",
            "Target row counts are not independent borrower counts; asset keys are trust-level loan identifiers.",
        ],
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/toyota-2022b-target-feasibility-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": result["period_count"], "assets": result["unique_asset_keys"],
                                     "chargeoff_events": result["raw_chargeoff_event_assets"],
                                     "at_risk_row_months": risk_rows,
                                     "horizons": list(horizons), "labels_qualified_for_training": False,
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "assets": len(asset), "chargeoff_events": len(event_assets),
                      "competing_exits": len(competing_assets), "at_risk_rows": risk_rows,
                      "horizon_counts": {h: v["at_risk_feature_row_months_by_class"] for h, v in horizons.items()}}))
    return out


if __name__ == "__main__":
    audit()
