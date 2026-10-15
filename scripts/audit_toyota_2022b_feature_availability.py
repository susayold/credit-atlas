"""Audit feature coverage, within-loan stability and information timing for H12 OOT rows."""
from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "toyota-2022b-absee-panel-1d111a2e0a47"
TEMPORAL_ID = "toyota-2022b-temporal-split-70fdbfa168fc"
HISTORY_ID = "toyota-2022b-absee-history-435918e7209a"
TARGET_AUDIT_ID = "toyota-2022b-target-feasibility-cb7b6624bc3f"
FEATURES = (
    "obligorCreditScore", "paymentToIncomePercentage", "currentDelinquencyStatus_days_past_due",
    "reportingPeriodActualEndBalanceAmount", "originalLoanAmount", "remainingTermToMaturityNumber",
    "vehicleValueAmount", "obligorGeographicLocation",
)
STATIC_CANDIDATES = (
    "obligorCreditScore", "paymentToIncomePercentage", "originalLoanAmount",
    "vehicleValueAmount", "obligorGeographicLocation",
)


def amount(value: object) -> Decimal:
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def code_list(value: object) -> set[str]:
    if value in (None, [], ""):
        return set()
    return {str(x) for x in value if x not in (None, "")}


def present(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def audit() -> Path:
    dataset = contained(ROOT, f"data/private/derived/{DATASET_ID}")
    manifest = read_json(dataset / "dataset-complete.json")
    temporal = read_json(contained(ROOT, f"artifacts/private/{TEMPORAL_ID}/audit.json"))
    target = read_json(contained(ROOT, f"artifacts/private/{TARGET_AUDIT_ID}/audit.json"))
    history_receipt = read_json(contained(ROOT, f"data/private/structured/{HISTORY_ID}/acquisition-complete.json"))
    if (manifest.get("report_count") != 51 or temporal.get("candidate_horizons", {}).get("12", {}).get("status")
            != "TWO_WAY_OUT_OF_TIME_SUPPORT_AUDITED" or target.get("raw_chargeoff_event_assets") != 1122):
        raise ValueError("Toyota data/temporal target evidence changed")
    temporal_h12 = temporal["candidate_horizons"]["12"]
    split_windows = {
        "train": (date.fromisoformat(temporal_h12["train"]["feature_start"]),
                  date.fromisoformat(temporal_h12["train"]["feature_end"])),
        "test": (date.fromisoformat(temporal_h12["test"]["feature_start"]),
                 date.fromisoformat(temporal_h12["test"]["feature_end"])),
    }

    states = {}
    left_censored = set()
    for month, part in enumerate(manifest["parquet_files"]):
        path = contained(dataset, part["file"])
        if path.stat().st_size != part["bytes"] or sha256(path) != part["sha256"]:
            raise ValueError(f"Panel Parquet hash mismatch for {part['report_date']}")
        cols = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount",
                "chargedoffPrincipalAmount", "zeroBalanceCode"]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=cols):
            for row in batch.to_pylist():
                key = (row["assetTypeNumber"], row["assetNumber"])
                state = states.setdefault(key, {"first_seen": month, "event": None, "exit": None})
                chargeoff = amount(row.get("chargedoffPrincipalAmount"))
                codes = code_list(row.get("zeroBalanceCode"))
                if chargeoff > 0 and state["event"] is None:
                    state["event"] = month
                if month == state["first_seen"] and "4" in codes and chargeoff <= 0:
                    left_censored.add(key)
                if (amount(row.get("reportingPeriodActualEndBalanceAmount")) == 0
                        and codes & {"1", "3"} and state["exit"] is None):
                    state["exit"] = month

    first_values = {field: {} for field in STATIC_CANDIDATES}
    changed_observations = Counter()
    changed_assets = {field: set() for field in STATIC_CANDIDATES}
    split_stats = {split: {"row_months": 0, "assets": set(), "features": Counter(),
                           "dpd_zero": 0, "dpd_positive": 0, "pti_gt_1": 0, "pti_gt_1_assets": set()}
                   for split in split_windows}
    for month_index, part in enumerate(manifest["parquet_files"]):
        report_date = date.fromisoformat(part["report_date"])
        path = contained(dataset, part["file"])
        cols = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount", *FEATURES]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=list(dict.fromkeys(cols))):
            for row in batch.to_pylist():
                key = (row["assetTypeNumber"], row["assetNumber"])
                if amount(row.get("reportingPeriodActualEndBalanceAmount")) <= 0:
                    continue
                for field in STATIC_CANDIDATES:
                    value = row.get(field)
                    if not present(value):
                        continue
                    baseline = first_values[field].setdefault(key, str(value).strip())
                    if str(value).strip() != baseline:
                        changed_observations[field] += 1
                        changed_assets[field].add(key)
                split = next((name for name, (lo, hi) in split_windows.items() if lo <= report_date <= hi), None)
                if split is None or key in left_censored:
                    continue
                state = states[key]
                event, exit_month = state["event"], state["exit"]
                first_outcome = min((idx for idx in (event, exit_month) if idx is not None), default=None)
                if first_outcome is not None and first_outcome <= month_index:
                    continue
                stats = split_stats[split]
                stats["row_months"] += 1
                stats["assets"].add(key)
                for field in FEATURES:
                    stats["features"][field + ("_present" if present(row.get(field)) else "_missing")] += 1
                dpd = row.get("currentDelinquencyStatus_days_past_due")
                if dpd == 0:
                    stats["dpd_zero"] += 1
                elif dpd is not None and dpd > 0:
                    stats["dpd_positive"] += 1
                pti = row.get("paymentToIncomePercentage")
                if present(pti) and amount(pti) > 1:
                    stats["pti_gt_1"] += 1
                    stats["pti_gt_1_assets"].add(key)

    filing_by_report = {row["report_date"]: row["filing_date"] for row in history_receipt["reports"]}
    lag_days = []
    for part in manifest["parquet_files"]:
        report = date.fromisoformat(part["report_date"])
        filing = date.fromisoformat(filing_by_report[part["report_date"]])
        lag_days.append((filing - report).days)

    split_output = {}
    for name, stats in split_stats.items():
        split_output[name] = {
            "feature_start": split_windows[name][0].isoformat(),
            "feature_end": split_windows[name][1].isoformat(),
            "at_risk_row_months": stats["row_months"],
            "unique_assets": len(stats["assets"]),
            "feature_coverage": {field: {"present": stats["features"][field + "_present"],
                                          "missing": stats["features"][field + "_missing"]}
                                 for field in FEATURES},
            "current_dpd_zero_row_months": stats["dpd_zero"],
            "current_dpd_positive_row_months": stats["dpd_positive"],
            "pti_gt_1_row_months": stats["pti_gt_1"],
            "pti_gt_1_unique_assets": len(stats["pti_gt_1_assets"]),
        }

    result = {
        "status": "TOYOTA_2022B_FEATURE_AVAILABILITY_AUDITED",
        "dataset_id": DATASET_ID, "dataset_manifest_sha256": sha256(dataset / "dataset-complete.json"),
        "temporal_audit_id": TEMPORAL_ID, "target_audit_id": TARGET_AUDIT_ID,
        "report_count": len(manifest["parquet_files"]), "horizon_months": 12,
        "split_support": split_output,
        "candidate_static_field_stability": {
            field: {"assets_with_observed_value": len(first_values[field]),
                    "assets_with_value_changes_after_first_observation": len(changed_assets[field]),
                    "later_row_month_values_different_from_first": changed_observations[field],
                    "use": "Candidate static/at-origination field; changed values require provenance review before selecting a policy."}
            for field in STATIC_CANDIDATES
        },
        "information_timing": {
            "feature_as_of": "ABS-EE reporting-period end; the data becomes public only when the filing is accepted.",
            "filing_lag_days": {"min": min(lag_days), "median": sorted(lag_days)[len(lag_days)//2],
                                "max": max(lag_days), "periods": len(lag_days)},
            "prediction_clock_recommendation": "Treat the prediction as made at/after the SEC filing availability date, not month-end, unless a separate operational feed proves earlier availability.",
        },
        "limitations": [
            "Coverage and stability do not prove operational availability to a servicer before SEC filing.",
            "Repeated monthly snapshots are dependent observations; no borrower-level independent sample is implied.",
            "Payment-to-income scale and anomalies remain unresolved; do not normalize or band this field from this audit alone.",
            "Feature availability alone does not qualify labels or justify model fitting; temporal/deal validation is still insufficient.",
        ],
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/toyota-2022b-feature-availability-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": result["report_count"], "horizon_months": 12,
                                     "train_rows": split_output["train"]["at_risk_row_months"],
                                     "test_rows": split_output["test"]["at_risk_row_months"],
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "filing_lag_days": result["information_timing"]["filing_lag_days"],
                      "splits": {k: {"rows": v["at_risk_row_months"], "features": v["feature_coverage"]}
                                 for k, v in split_output.items()},
                      "static_stability": result["candidate_static_field_stability"]}, ensure_ascii=False))
    return out


if __name__ == "__main__":
    audit()
