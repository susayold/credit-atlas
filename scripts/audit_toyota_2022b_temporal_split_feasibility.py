"""Audit honest time-ordered train/test support for Toyota 2022-B servicing labels."""
from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "toyota-2022b-absee-panel-1d111a2e0a47"
PANEL_AUDIT_ID = "toyota-2022b-absee-panel-audit-c9fbf983fa4e"
TARGET_AUDIT_ID = "toyota-2022b-target-feasibility-cb7b6624bc3f"
HORIZONS = (6, 12, 24)


def amount(value: object) -> float:
    try:
        return float(value) if value not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def codes(value: object) -> set[str]:
    if value in (None, [], ""):
        return set()
    return {str(x) for x in value if x not in (None, "")}


def audit() -> Path:
    dataset = contained(ROOT, "data/private/derived/" + DATASET_ID)
    manifest = read_json(dataset / "dataset-complete.json")
    panel_audit = read_json(contained(ROOT, f"artifacts/private/{PANEL_AUDIT_ID}/audit.json"))
    target_audit = read_json(contained(ROOT, f"artifacts/private/{TARGET_AUDIT_ID}/audit.json"))
    if (manifest.get("report_count") != 51 or panel_audit.get("period_count") != 51
            or panel_audit.get("unique_asset_keys_seen") != 77626
            or any(x.get("labels_qualified_for_training") is not False
                   for x in target_audit.get("candidate_horizons", {}).values())):
        raise ValueError("Toyota panel or target feasibility audit changed")
    periods = manifest["parquet_files"]

    assets: dict[tuple[object, object], dict[str, int | None]] = {}
    for month, part in enumerate(periods):
        path = contained(dataset, part["file"])
        if path.stat().st_size != part["bytes"] or sha256(path) != part["sha256"]:
            raise ValueError(f"Panel Parquet hash mismatch for {part['report_date']}")
        cols = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount",
                "chargedoffPrincipalAmount", "zeroBalanceCode"]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=cols):
            for row in batch.to_pylist():
                key = (row["assetTypeNumber"], row["assetNumber"])
                state = assets.setdefault(key, {"event": None, "exit": None})
                if amount(row.get("chargedoffPrincipalAmount")) > 0 and state["event"] is None:
                    state["event"] = month
                if (amount(row.get("reportingPeriodActualEndBalanceAmount")) == 0
                        and codes(row.get("zeroBalanceCode")) & {"1", "3"}
                        and state["exit"] is None):
                    state["exit"] = month

    horizon_results = {}
    for horizon in HORIZONS:
        # Hold out the latest 12 feature months with a full forward horizon.
        test_start = len(periods) - horizon - 12
        test_end = test_start + 11
        train_end = test_start - horizon - 1
        if train_end < 0:
            horizon_results[str(horizon)] = {
                "status": "NO_HONEST_TRAIN_TEST_SPLIT",
                "reason": "A 12-feature-month OOT window plus the required horizon embargo leaves no training feature month.",
                "candidate_test_feature_start": periods[test_start]["report_date"],
                "candidate_test_feature_end": periods[test_end]["report_date"],
                "trainable": False,
            }
            continue

        windows = {
            "train": (0, train_end),
            "embargo": (train_end + 1, test_start - 1),
            "test": (test_start, test_end),
        }
        labels = {name: Counter() for name in ("train", "test")}
        unique = {name: defaultdict(set) for name in ("train", "test")}
        asset_support = {name: set() for name in ("train", "test")}
        at_risk_rows = Counter()
        for month, part in enumerate(periods):
            selected_window = next((name for name, (lo, hi) in windows.items()
                                    if name in labels and lo <= month <= hi), None)
            if selected_window is None:
                continue
            path = contained(dataset, part["file"])
            cols = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount"]
            for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=cols):
                for row in batch.to_pylist():
                    if amount(row.get("reportingPeriodActualEndBalanceAmount")) <= 0:
                        continue
                    key = (row["assetTypeNumber"], row["assetNumber"])
                    state = assets[key]
                    event, exit_month = state["event"], state["exit"]
                    first_outcome = min((x for x in (event, exit_month) if x is not None), default=None)
                    if first_outcome is not None and first_outcome <= month:
                        continue
                    at_risk_rows[selected_window] += 1
                    asset_support[selected_window].add(key)
                    last_outcome_month = month + horizon
                    if event is not None and month < event <= last_outcome_month and (
                            exit_month is None or event < exit_month):
                        label = "chargeoff"
                    elif exit_month is not None and month < exit_month <= last_outcome_month and (
                            event is None or exit_month < event):
                        label = "competing_exit"
                    else:
                        label = "no_event_full_horizon"
                    labels[selected_window][label] += 1
                    unique[selected_window][label].add(key)

        support = {}
        for split in ("train", "test"):
            counts = dict(sorted(labels[split].items()))
            support[split] = {
                "feature_start": periods[windows[split][0]]["report_date"],
                "feature_end": periods[windows[split][1]]["report_date"],
                "at_risk_row_months": at_risk_rows[split],
                "unique_assets": len(asset_support[split]),
                "row_months_by_class": counts,
                "unique_assets_by_class": {k: len(v) for k, v in sorted(unique[split].items())},
            }
        overlap = asset_support["train"] & asset_support["test"]
        horizon_results[str(horizon)] = {
            "status": "TWO_WAY_OUT_OF_TIME_SUPPORT_AUDITED",
            "horizon_months": horizon,
            "train": support["train"],
            "embargo": {
                "feature_start": periods[windows["embargo"][0]]["report_date"],
                "feature_end": periods[windows["embargo"][1]]["report_date"],
                "periods": windows["embargo"][1] - windows["embargo"][0] + 1,
                "purpose": "Separate train label outcome time from test feature time; rows in this band are not used in either split.",
            },
            "test": support["test"],
            "train_test_asset_overlap": len(overlap),
            "overlap_treatment": "The same trust-level asset may appear across periods; uncertainty must cluster by asset. This split does not validate transfer to another trust.",
            "three_way_train_validation_test_available": False,
            "trainable": False,
        }

    result = {
        "status": "TOYOTA_2022B_TEMPORAL_SPLIT_FEASIBILITY_AUDITED",
        "dataset_id": DATASET_ID,
        "dataset_manifest_sha256": sha256(dataset / "dataset-complete.json"),
        "panel_audit_id": PANEL_AUDIT_ID,
        "target_audit_id": TARGET_AUDIT_ID,
        "report_count": len(periods),
        "report_start": periods[0]["report_date"],
        "report_end": periods[-1]["report_date"],
        "split_design": "Latest 12 feature months with complete forward horizon as OOT test; train feature months end one full horizon before test feature start; an embargo period is excluded between them.",
        "candidate_horizons": horizon_results,
        "limitations": [
            "This is split-support accounting only; no model was fitted and no discrimination/calibration result is implied.",
            "No separate validation/calibration window fits inside this history with a clean horizon embargo and a 12-month test window.",
            "Twenty-four-month target has too little history for a useful honest OOT training/test split under this design.",
            "Repeated monthly rows from one loan are dependent; group uncertainty by asset and add another trust for external validation.",
        ],
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/toyota-2022b-temporal-split-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {
        "status": result["status"], "audit_sha256": sha256(out / "audit.json"),
        "report_count": len(periods), "horizon_count": len(horizon_results),
        "horizons_with_two_way_oot_support": sum(x.get("status") == "TWO_WAY_OUT_OF_TIME_SUPPORT_AUDITED"
                                                   for x in horizon_results.values()),
        "three_way_split_available": False, "model_fitted": False,
        "visibility": "private", "public_release_approved": False,
    })
    print(out)
    print(json.dumps({h: {"status": v["status"], "train": v.get("train", {}).get("row_months_by_class"),
                          "test": v.get("test", {}).get("row_months_by_class"),
                          "train_test_asset_overlap": v.get("train_test_asset_overlap")}
                      for h, v in horizon_results.items()}))
    return out


if __name__ == "__main__":
    audit()
