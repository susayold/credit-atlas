"""Audit SEC zero-balance reason codes and unexplained asset-key disappearance."""
from __future__ import annotations

import json
import uuid
from collections import Counter
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "woart-absee-panel-91efe12963d6"
PANEL_AUDIT = "artifacts/private/woart-absee-panel-audit-f689e9c70199/audit.json"
AUTO_XSD = "data/private/structured/sec-abs-xml-spec-542aab868783/xsd/ABS XML Schema Files/eis_ABS_AutoLoanAssetData.xsd"
ZERO_CODES = {"1": "Prepaid or Matured", "2": "Third-party Sale", "3": "Repurchased or Replaced",
              "4": "Charged-off", "5": "Servicing Transfer", "99": "Unavailable"}


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def verify_xsd(path: Path) -> dict:
    tree = ET.parse(path)
    element = next((x for x in tree.iter() if x.attrib.get("name") == "zeroBalanceCode"), None)
    if element is None or element.attrib.get("type", "").split(":")[-1] != "ZERO_BAL_CODE_TYPE" or element.attrib.get("maxOccurs") != "unbounded":
        raise ValueError("Unexpected SEC zeroBalanceCode declaration")
    type_node = next((x for x in tree.iter() if x.attrib.get("name") == "ZERO_BAL_CODE_TYPE"), None)
    enumerations = {x.attrib.get("value") for x in type_node.iter() if local(x.tag) == "enumeration"} if type_node is not None else set()
    if enumerations != set(ZERO_CODES):
        raise ValueError("Observed zero balance code list differs from SEC XSD")
    return {"element": "zeroBalanceCode", "type": "ZERO_BAL_CODE_TYPE", "enumerations": sorted(enumerations),
            "descriptions": ZERO_CODES, "xsd_sha256": sha256(path)}


def read_month(path: Path) -> dict:
    data = {}
    for batch in pq.ParquetFile(path).iter_batches(batch_size=4096):
        for r in batch.to_pylist():
            key = (r["assetTypeNumber"], r["assetNumber"])
            if key in data:
                raise ValueError("Duplicate asset key in monthly panel")
            bal = Decimal(r.get("reportingPeriodActualEndBalanceAmount") or "0")
            codes = r.get("zeroBalanceCode") or []
            unknown = set(codes) - set(ZERO_CODES)
            if unknown:
                raise ValueError("Unknown zeroBalanceCode outside SEC XSD")
            data[key] = {"balance": bal, "codes": codes,
                         "days": r.get("currentDelinquencyStatus_days_past_due")}
    return data


def audit() -> Path:
    dataset = contained(ROOT, "data/private/derived/" + DATASET_ID)
    manifest = read_json(dataset / "dataset-complete.json")
    panel_audit = read_json(contained(ROOT, PANEL_AUDIT))
    if manifest.get("status") != "OFFICIAL_ABSEE_RAW_PANEL_PARQUET_BUILT" or panel_audit.get("hash_verified_files") != 20:
        raise ValueError("Official panel prerequisite not verified")
    xsd = verify_xsd(contained(ROOT, AUTO_XSD))
    months = []
    transitions = []
    prev = None
    overall_reasons = Counter()
    for item in manifest["parquet_files"]:
        current = read_month(contained(dataset, item["file"]))
        code_counts = Counter()
        zero_count = 0
        zero_missing = 0
        zero_negative = 0
        for row in current.values():
            if row["balance"] == 0:
                zero_count += 1
                if not row["codes"]:
                    zero_missing += 1
                for code in row["codes"]:
                    code_counts[code] += 1
                    overall_reasons[code] += 1
            elif row["balance"] < 0:
                zero_negative += 1
        months.append({"report_date": item["report_date"], "rows": len(current),
                       "zero_balance_assets": zero_count, "zero_balance_missing_code": zero_missing,
                       "zero_balance_code_values": dict(sorted(code_counts.items())),
                       "negative_balance_assets": zero_negative})
        if prev:
            old_date, old = prev
            overlap = set(old) & set(current)
            new_only = set(old) - set(current)
            moved_to_zero = [k for k in overlap if old[k]["balance"] != 0 and current[k]["balance"] == 0]
            transition_code_counts = Counter()
            uncoded_to_zero = 0
            for key in moved_to_zero:
                codes = current[key]["codes"]
                if not codes:
                    uncoded_to_zero += 1
                for code in codes:
                    transition_code_counts[code] += 1
            missing_previous_balance = Counter()
            missing_previous_days = Counter()
            missing_previous_zero_codes = Counter()
            missing_previous_amount = Decimal(0)
            for key in new_only:
                row = old[key]
                missing_previous_balance["negative" if row["balance"] < 0 else "zero" if row["balance"] == 0 else "positive"] += 1
                if not row["codes"]:
                    missing_previous_zero_codes["blank"] += 1
                else:
                    for code in row["codes"]:
                        missing_previous_zero_codes[code] += 1
                days = row["days"]
                state = "missing" if days is None else "0-30" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "91-120" if days <= 120 else "121+"
                missing_previous_days[state] += 1
                missing_previous_amount += row["balance"]
            transitions.append({"from": old_date, "to": item["report_date"],
                "matched_asset_keys": len(overlap), "prior_keys_not_in_current_filing": len(new_only),
                "prior_keys_not_in_current_filing_by_prior_balance": dict(missing_previous_balance),
                "prior_keys_not_in_current_filing_by_prior_days_bucket": dict(missing_previous_days),
                "prior_keys_not_in_current_filing_by_previously_reported_zero_balance_code": dict(sorted(missing_previous_zero_codes.items())),
                "prior_ending_balance_of_not_included_keys": str(missing_previous_amount),
                "matched_nonzero_to_zero_count": len(moved_to_zero),
                "matched_nonzero_to_zero_code_counts": dict(sorted(transition_code_counts.items())),
                "matched_nonzero_to_zero_missing_code": uncoded_to_zero,
                "interpretation": "XSD reason codes are reported as published; disappearance without a current-period record remains unclassified."})
        prev = (item["report_date"], current)
    out = contained(ROOT, "artifacts/private/woart-absee-zero-balance-audit-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    result = {"status": "XSD_ZERO_BALANCE_CODES_AND_EXIT_SCOPE_AUDITED", "dataset_id": DATASET_ID,
              "dataset_receipt_sha256": sha256(dataset / "dataset-complete.json"), "xsd": xsd,
              "months": months, "adjacent_month_transitions": transitions,
              "zero_balance_code_value_counts": dict(sorted(overall_reasons.items())),
              "unclassified_missing_records": sum(x["prior_keys_not_in_current_filing"] for x in transitions),
              "causal_exit_labels_created": False,
              "limitations": ["Zero-balance XSD reasons can be multivalued and do not alone prove contractual default or investor loss.",
                  "No exit reason is inferred for an asset key missing from a later file.",
                  "Previously reported zeroBalanceCode values are descriptive fields on the prior filing, not verified causes of later removal.",
                  "Code 99 explicitly means unavailable; blank is not converted to any code."],
              "created_at": timestamp(), "visibility": "private", "public_release_approved": False}
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                      "periods": len(months), "transition_pairs": len(transitions),
                                      "zero_balance_code_counts": dict(sorted(overall_reasons.items())),
                                      "unclassified_missing_records": result["unclassified_missing_records"],
                                      "causal_exit_labels_created": False, "visibility": "private",
                                      "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "periods": len(months), "transitions": len(transitions),
                      "reason_counts": dict(sorted(overall_reasons.items())),
                      "missing_record_exits": result["unclassified_missing_records"]}))
    return out


if __name__ == "__main__":
    audit()
