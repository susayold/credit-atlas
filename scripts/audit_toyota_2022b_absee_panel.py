"""Audit longitudinal coverage and reported transitions in the Toyota 2022-B panel."""
from __future__ import annotations

import json
import uuid
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "toyota-2022b-absee-panel-1d111a2e0a47"
MONEY_FIELDS = ["reportingPeriodBeginningLoanBalanceAmount", "reportingPeriodActualEndBalanceAmount",
                "actualPrincipalCollectedAmount", "actualInterestCollectedAmount", "chargedoffPrincipalAmount",
                "recoveredAmount", "repossessedProceedsAmount"]


def money(raw: object) -> Decimal:
    if raw in (None, ""):
        return Decimal(0)
    return Decimal(str(raw))


def state(row: dict) -> str:
    balance = money(row.get("reportingPeriodActualEndBalanceAmount"))
    if balance < 0:
        return "negative_balance"
    if balance == 0:
        return "zero_balance"
    days = row.get("currentDelinquencyStatus_days_past_due")
    if days is None:
        return "positive_dpd_missing"
    if days <= 30:
        return "positive_0_30"
    if days <= 60:
        return "positive_31_60"
    if days <= 90:
        return "positive_61_90"
    if days <= 120:
        return "positive_91_120"
    return "positive_121_plus"


def codes(row: dict) -> list[str]:
    value = row.get("zeroBalanceCode")
    if value in (None, [], ""):
        return ["blank"]
    return [str(x) for x in value if x not in (None, "")] or ["blank"]


def audit() -> Path:
    dataset = contained(ROOT, "data/private/derived/" + DATASET_ID)
    receipt = read_json(dataset / "dataset-complete.json")
    if (receipt.get("status") != "OFFICIAL_TOYOTA_2022B_ABSEE_PANEL_PARQUET_BUILT"
            or receipt.get("report_count") != 51 or receipt.get("row_count") != 2508991):
        raise ValueError("Toyota 2022-B panel receipt mismatch")

    periods = []
    transitions = []
    all_asset_stats = {}
    all_zero_balance_codes = Counter()
    chargeoff_crosscheck = Counter()
    recovery_crosscheck = Counter()
    chargeoff_code4_sum = Decimal(0)
    previous = None
    total_rows = 0
    total_hashes = 0
    for item in receipt["parquet_files"]:
        path = contained(dataset, item["file"])
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError(f"Parquet hash/size mismatch for {item['report_date']}")
        total_hashes += 1
        current = {}
        counts = Counter()
        sums = Counter()
        balance_sums_by_state = Counter()
        present = Counter()
        code_counts = Counter()
        nonzero_events = Counter()
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192):
            for row in batch.to_pylist():
                key = (row["assetTypeNumber"], row["assetNumber"])
                if not all(key) or key in current:
                    raise ValueError(f"Missing or duplicate Toyota asset key for {item['report_date']}")
                row_state = state(row)
                row_codes = codes(row)
                ending_balance = money(row.get("reportingPeriodActualEndBalanceAmount"))
                current[key] = {"state": row_state, "balance": ending_balance, "zero_codes": row_codes}
                counts[current[key]["state"]] += 1
                balance_sums_by_state[current[key]["state"]] += current[key]["balance"]
                for field in MONEY_FIELDS:
                    raw = row.get(field)
                    if raw not in (None, ""):
                        present[field] += 1
                        value = money(raw)
                        sums[field] += value
                        if value > 0:
                            nonzero_events[field + "_positive_rows"] += 1
                        elif value < 0:
                            nonzero_events[field + "_negative_rows"] += 1
                code_counts.update(row_codes)
                all_zero_balance_codes.update(row_codes)
                chargeoff = money(row.get("chargedoffPrincipalAmount"))
                has_code4 = "4" in row_codes
                if has_code4:
                    chargeoff_crosscheck["code4_row_months"] += 1
                    chargeoff_crosscheck["code4_with_zero_ending_balance"] += row_state == "zero_balance"
                    chargeoff_crosscheck["code4_with_positive_chargeoff_amount"] += chargeoff > 0
                    chargeoff_crosscheck["code4_without_positive_chargeoff_amount"] += chargeoff <= 0
                    chargeoff_code4_sum += chargeoff
                if chargeoff > 0 and not has_code4:
                    chargeoff_crosscheck["positive_chargeoff_without_code4"] += 1
                stat = all_asset_stats.setdefault(key, {"observed_months": 0, "first_seen": item["report_date"],
                                                        "last_seen": item["report_date"], "zero_months": 0,
                                                        "chargeoff_positive_months": 0,
                                                        "recovery_positive_months": 0,
                                                        "recovery_negative_months": 0})
                stat["observed_months"] += 1
                stat["last_seen"] = item["report_date"]
                stat["zero_months"] += current[key]["state"] == "zero_balance"
                recovery = money(row.get("recoveredAmount"))
                if recovery > 0:
                    recovery_crosscheck["positive_recovery_row_months"] += 1
                    recovery_crosscheck["positive_recovery_with_code4"] += has_code4
                    recovery_crosscheck["positive_recovery_without_code4"] += not has_code4
                elif recovery < 0:
                    recovery_crosscheck["negative_recovery_row_months"] += 1
                    recovery_crosscheck["negative_recovery_with_code4"] += has_code4
                stat["chargeoff_positive_months"] += chargeoff > 0
                stat["code4_months"] = stat.get("code4_months", 0) + has_code4
                if has_code4 and not stat.get("first_code4_date"):
                    stat["first_code4_date"] = item["report_date"]
                if chargeoff > 0:
                    stat["first_chargeoff_date"] = item["report_date"]
                stat["recovery_positive_months"] += recovery > 0
                stat["recovery_negative_months"] += recovery < 0
        if len(current) != item["rows"] or len(current) != item["unique_asset_keys"]:
            raise ValueError(f"Panel row/key mismatch in {item['report_date']}")
        total_rows += len(current)
        positive_pool = sum((value for bucket, value in balance_sums_by_state.items()
                             if bucket.startswith("positive_")), Decimal(0))
        d31_balance = sum((value for bucket, value in balance_sums_by_state.items()
                           if bucket in {"positive_31_60", "positive_61_90", "positive_91_120", "positive_121_plus"}), Decimal(0))
        d61_balance = sum((value for bucket, value in balance_sums_by_state.items()
                           if bucket in {"positive_61_90", "positive_91_120", "positive_121_plus"}), Decimal(0))
        reported_amount_sums = {k: str(v) for k, v in sorted(sums.items())}
        reported_nonzero_counts = dict(sorted(nonzero_events.items()))
        period = {"report_date": item["report_date"], "rows": len(current),
                  "ending_balance_state_counts": dict(sorted(counts.items())),
                  "ending_balance_state_sums_raw_units": {k: str(v) for k, v in sorted(balance_sums_by_state.items())},
                  "reported_amount_sums_raw_units": reported_amount_sums,
                  "reported_amount_present_rows": dict(sorted(present.items())),
                  "reported_nonzero_amount_rows": reported_nonzero_counts,
                  "zero_balance_code_values": dict(sorted(code_counts.items())),
                  "asset_xml_kpis": {
                      "positive_ending_pool_balance_raw_units": str(positive_pool),
                      "31plus_ending_balance_raw_units": str(d31_balance),
                      "31plus_rate_vs_positive_ending_balance": str(d31_balance / positive_pool) if positive_pool else None,
                      "61plus_ending_balance_raw_units": str(d61_balance),
                      "61plus_rate_vs_positive_ending_balance": str(d61_balance / positive_pool) if positive_pool else None,
                      "current_period_chargedoff_principal_raw_units": reported_amount_sums.get("chargedoffPrincipalAmount", "0"),
                      "chargeoff_positive_row_months": reported_nonzero_counts.get("chargedoffPrincipalAmount_positive_rows", 0),
                      "current_period_recovered_amount_raw_units": reported_amount_sums.get("recoveredAmount", "0"),
                      "recovery_positive_row_months": reported_nonzero_counts.get("recoveredAmount_positive_rows", 0),
                      "recovery_negative_row_months": reported_nonzero_counts.get("recoveredAmount_negative_rows", 0),
                  }}
        periods.append(period)
        if previous is not None:
            previous_date, previous_rows = previous
            overlap = set(previous_rows) & set(current)
            previous_only = set(previous_rows) - set(current)
            current_only = set(current) - set(previous_rows)
            matrix = Counter((previous_rows[k]["state"], current[k]["state"]) for k in overlap)
            previous_only_states = Counter(previous_rows[k]["state"] for k in previous_only)
            previous_only_codes = Counter(code for k in previous_only for code in previous_rows[k]["zero_codes"])
            transitions.append({"from": previous_date, "to": item["report_date"],
                                "matched_keys": len(overlap), "previous_only_keys": len(previous_only),
                                "current_only_keys": len(current_only),
                                "matched_state_transitions": {f"{a} -> {b}": n for (a, b), n in sorted(matrix.items())},
                                "previous_only_state_counts": dict(sorted(previous_only_states.items())),
                                "previous_only_zero_balance_codes": dict(sorted(previous_only_codes.items())),
                                "exit_cause_qualified": False, "default_labels_qualified": False})
        previous = (item["report_date"], current)

    observed_months = Counter(stat["observed_months"] for stat in all_asset_stats.values())
    unique_chargeoff_assets = sum(stat["chargeoff_positive_months"] > 0 for stat in all_asset_stats.values())
    unique_positive_recovery_assets = sum(stat["recovery_positive_months"] > 0 for stat in all_asset_stats.values())
    unique_negative_recovery_assets = sum(stat["recovery_negative_months"] > 0 for stat in all_asset_stats.values())
    unique_zero_assets = sum(stat["zero_months"] > 0 for stat in all_asset_stats.values())
    unique_code4_assets = sum(stat.get("code4_months", 0) > 0 for stat in all_asset_stats.values())
    event_code4_date_matches = sum(stat.get("chargeoff_positive_months", 0) == 1
                                   and stat.get("first_chargeoff_date") == stat.get("first_code4_date")
                                   for stat in all_asset_stats.values()
                                   if stat.get("chargeoff_positive_months", 0) > 0)
    result = {
        "status": "TOYOTA_2022B_LONGITUDINAL_PANEL_AUDITED",
        "dataset_id": DATASET_ID, "dataset_manifest_sha256": sha256(dataset / "dataset-complete.json"),
        "period_count": len(periods), "transition_pairs": len(transitions),
        "row_month_observations": total_rows, "unique_asset_keys_seen": len(all_asset_stats),
        "verified_parquet_hashes": total_hashes,
        "unique_asset_observation_month_distribution": {str(k): v for k, v in sorted(observed_months.items())},
        "unique_assets_with_zero_balance_observed": unique_zero_assets,
        "unique_assets_with_positive_chargeoff_amount": unique_chargeoff_assets,
        "unique_assets_with_positive_recovery_amount": unique_positive_recovery_assets,
        "unique_assets_with_negative_recovery_amount": unique_negative_recovery_assets,
        "zero_balance_code_row_month_counts": dict(sorted(all_zero_balance_codes.items())),
        "chargeoff_code4_crosscheck": {**dict(chargeoff_crosscheck),
                                         "code4_chargeoff_amount_sum_raw_units": str(chargeoff_code4_sum),
                                         "unique_code4_assets": unique_code4_assets,
                                         "unique_positive_chargeoff_events": unique_chargeoff_assets,
                                         "positive_chargeoff_events_with_one_event_month": sum(
                                             stat.get("chargeoff_positive_months", 0) == 1
                                             for stat in all_asset_stats.values()),
                                         "positive_chargeoff_event_and_first_code4_month_match": event_code4_date_matches},
        "recovery_code4_crosscheck": dict(recovery_crosscheck),
        "periods": periods, "adjacent_month_transitions": transitions,
        "interpretation": [
            "All counts and sums are SEC-reported asset row/month observations unless labeled unique assets.",
            "Matched-key state changes are descriptive; source data does not alone distinguish payment, modification, correction, or servicing exit.",
            "A positive charged-off principal amount is an observed source field, not automatically a clean default date or lifetime PD label.",
            "Recovery/repossessed proceeds remain signed source amounts; no LGD or recovery rate is calculated in this audit.",
        ],
        "limitations": ["Single Toyota trust; not a representative borrower population.",
                        "No servicing certificate/EX-103 tie-out is made in this panel audit.",
                        "No application-time features, decision outcomes, or borrower identity resolution.",
                        "Zero-balance code and missing-key reason are not inferred."],
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/toyota-2022b-absee-panel-audit-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": result["period_count"], "transition_pairs": result["transition_pairs"],
                                     "rows": total_rows, "unique_assets": len(all_asset_stats),
                                     "hash_verified_files": total_hashes,
                                     "default_or_exit_labels_qualified": False,
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "periods": result["period_count"],
                      "rows": total_rows, "unique_assets": len(all_asset_stats),
                      "transitions": result["transition_pairs"],
                      "chargeoff_assets": unique_chargeoff_assets,
                      "positive_recovery_assets": unique_positive_recovery_assets,
                      "negative_recovery_assets": unique_negative_recovery_assets}))
    return out


if __name__ == "__main__":
    audit()
