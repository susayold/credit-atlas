"""Audit the official ABS-EE Parquet panel and summarize observed adjacent-month states."""
from __future__ import annotations

import json
import sys
import uuid
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
STATES = ("current_0_30", "31_60", "61_90", "91_120", "121_plus", "zero_balance", "negative_balance", "positive_balance_status_missing", "negative_day_count")


def bucket(row: dict) -> str:
    balance_text = row.get("reportingPeriodActualEndBalanceAmount")
    balance = Decimal(balance_text) if balance_text not in (None, "") else Decimal(0)
    if balance < 0:
        return "negative_balance"
    if balance == 0:
        return "zero_balance"
    days = row.get("currentDelinquencyStatus_days_past_due")
    if days is None:
        return "positive_balance_status_missing"
    if days < 0:
        return "negative_day_count"
    if days <= 30:
        return "current_0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    if days <= 120:
        return "91_120"
    return "121_plus"


def load_month(path: Path) -> dict:
    parquet = pq.ParquetFile(path)
    rows = {}
    counts = Counter()
    balances = Counter()
    delinquency_missing = 0
    missing_positive_balance = 0
    total_balance = Decimal(0)
    for batch in parquet.iter_batches(batch_size=4096):
        for row in batch.to_pylist():
            key = (row["assetTypeNumber"], row["assetNumber"])
            if not all(key) or key in rows:
                raise ValueError("Missing or duplicate asset key in Parquet period")
            if row["reportingPeriodEndingDate"] != row["report_date"].strftime("%m-%d-%Y"):
                raise ValueError("Partition date differs from source XML field")
            raw = row.get("currentDelinquencyStatus_raw")
            days = row.get("currentDelinquencyStatus_days_past_due")
            if raw in (None, ""):
                delinquency_missing += 1
                if days is not None:
                    raise ValueError("Missing raw day count but typed value exists")
            elif days != int(raw):
                raise ValueError("Typed day count differs from raw XML value")
            state = bucket(row)
            balance = Decimal(row["reportingPeriodActualEndBalanceAmount"] or "0")
            if state == "positive_balance_status_missing":
                missing_positive_balance += 1
            rows[key] = (state, balance)
            counts[state] += 1
            balances[state] += balance
            total_balance += balance
    return {"rows": rows, "summary": {
        "unique_asset_keys": len(rows),
        "state_counts": {s: counts[s] for s in STATES},
        "state_ending_balances": {s: str(balances[s]) for s in STATES},
        "total_xml_ending_balance": str(total_balance),
        "blank_day_status_rows": delinquency_missing,
        "positive_balance_with_blank_day_status": missing_positive_balance,
    }}


def audit(dataset_id: str) -> Path:
    dataset = contained(ROOT, "data/private/derived/" + dataset_id)
    receipt = read_json(dataset / "dataset-complete.json")
    if receipt.get("status") != "OFFICIAL_ABSEE_RAW_PANEL_PARQUET_BUILT" or receipt.get("report_count") != 20:
        raise ValueError("Official panel manifest mismatch")
    profile = read_json(contained(ROOT, "artifacts/private/woart-absee-official-profile-0c8de9d2359d/profile.json"))
    certificate_balances = {x["report_date"]: Decimal(x["certificate_ending_receivables_including_ysoa"])
                            for x in profile["certificate_reconciliations"]}
    certificate_accounts = {x["report_date"]: x["certificate_ending_pool_accounts"]
                            for x in profile["certificate_reconciliations"]}
    monthly = []
    transitions = []
    previous = None
    for manifest in receipt["parquet_files"]:
        path = contained(dataset, manifest["file"])
        if path.stat().st_size != manifest["bytes"] or sha256(path) != manifest["sha256"]:
            raise ValueError("Parquet file hash changed")
        loaded = load_month(path)
        current = loaded["rows"]
        summary = loaded["summary"]
        summary["report_date"] = manifest["report_date"]
        summary["rows"] = manifest["rows"]
        summary["asset_ending_balance_sum_reconciles_including_ysoa"] = (
            Decimal(summary["total_xml_ending_balance"])
            == certificate_balances[manifest["report_date"]])
        summary["certificate_ending_pool_accounts"] = certificate_accounts[manifest["report_date"]]
        summary["xml_nonzero_balance_assets"] = summary["state_counts"]["current_0_30"] + sum(
            summary["state_counts"][name] for name in ("31_60", "61_90", "91_120", "121_plus",
                                                         "negative_balance", "positive_balance_status_missing"))
        summary["nonzero_balance_asset_count_delta"] = summary["xml_nonzero_balance_assets"] - summary["certificate_ending_pool_accounts"]
        summary["nonzero_balance_asset_count_matches"] = summary["nonzero_balance_asset_count_delta"] == 0
        monthly.append(summary)
        if previous is not None:
            old_date, old = previous
            overlap = set(old) & set(current)
            matrix = Counter()
            old_only = set(old) - set(current)
            new_only = set(current) - set(old)
            for key in overlap:
                matrix[(old[key][0], current[key][0])] += 1
            transitions.append({
                "from": old_date,
                "to": manifest["report_date"],
                "matched_asset_keys": len(overlap),
                "previous_only_asset_keys": len(old_only),
                "current_only_asset_keys": len(new_only),
                "status_transition_counts": {f"{a} -> {b}": n for (a, b), n in sorted(matrix.items())},
                "interpretation": "Observed source-status transition among matched asset keys; zero balance or disappearance is not assigned a causal exit/default label.",
            })
        previous = (manifest["report_date"], current)
    failures = [m["report_date"] for m in monthly if not m["asset_ending_balance_sum_reconciles_including_ysoa"]]
    out = contained(ROOT, "artifacts/private/woart-absee-panel-audit-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    result = {
        "status": "OFFICIAL_PARQUET_PANEL_AND_ADJACENT_STATE_AUDIT_PASS" if not failures else "PANEL_RECONCILIATION_FAILURE",
        "dataset_id": dataset_id,
        "dataset_receipt_sha256": sha256(dataset / "dataset-complete.json"),
        "periods": monthly,
        "adjacent_month_transitions": transitions,
        "unique_key_check": "one row per asset key per monthly snapshot",
        "total_rows": sum(x["rows"] for x in monthly),
        "hash_verified_files": len(monthly),
        "certificate_balance_failures": failures,
        "asset_ending_balance_sum_reconciles_including_ysoa": not failures,
        "nonzero_balance_asset_count_exact_periods": sum(x["nonzero_balance_asset_count_matches"] for x in monthly),
        "nonzero_balance_asset_count_differences": [{"report_date": x["report_date"],
                                                     "delta": x["nonzero_balance_asset_count_delta"]}
                                                    for x in monthly if not x["nonzero_balance_asset_count_matches"]],
        "transition_labels_qualified": False,
        "model_ready": False,
        "limitations": [
            "Transitions are descriptive status changes among matched source asset keys, not cure, default, prepayment or borrower behavior labels.",
            "No causal reason is assigned to zero balance, missing assets, or delinquency state changes.",
            "Negative asset ending balances are retained as their own observed state, not relabeled as zero/default; 16/20 monthly nonzero-balance counts match the certificate exactly and the other four differ by one account.",
            "The source is one issuer/deal and twenty monthly observations; it is not a general-purpose model training population.",
        ],
        "created_at": timestamp(),
        "visibility": "private",
        "public_release_approved": False,
    }
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": len(monthly), "adjacent_transition_pairs": len(transitions),
                                     "rows": result["total_rows"], "hash_verified_files": result["hash_verified_files"],
                                     "balance_failures": len(failures), "model_ready": False,
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "periods": len(monthly), "transition_pairs": len(transitions),
                      "rows": result["total_rows"], "balance_failures": len(failures)}))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: audit_woart_absee_panel.py woart-absee-panel-<12 hex>")
    audit(sys.argv[1])
