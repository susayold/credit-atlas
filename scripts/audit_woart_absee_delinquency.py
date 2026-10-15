"""Map SEC ABS-EE day-past-due observations and reconcile them to certificates."""
from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = "artifacts/private/woart-absee-official-profile-0c8de9d2359d/profile.json"
PROFILE_RECEIPT = "artifacts/private/woart-absee-official-profile-0c8de9d2359d/receipt.json"
CASE_ID = "abs-case-fcbaa9573ac3"
SPEC = "data/private/structured/sec-abs-xml-spec-542aab868783/xsd/ABS XML Schema Files/eis_ABS_AutoLoanAssetData.xsd"
COMMON = "data/private/structured/sec-abs-xml-spec-542aab868783/xsd/ABS XML Schema Files/eis_Common.xsd"
BUCKETS = (("31_60", 31, 60), ("61_90", 61, 90), ("91_120", 91, 120), ("121_plus", 121, 99_999_999))


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def schema_evidence(auto_path: Path, common_path: Path) -> dict:
    tree = ET.parse(auto_path)
    element = next((e for e in tree.iter() if e.attrib.get("name") == "currentDelinquencyStatus"), None)
    if element is None or element.attrib.get("type", "").split(":")[-1] != "INTEGER_TYPE_8_A":
        raise ValueError("Unexpected currentDelinquencyStatus schema declaration")
    raw = auto_path.read_text(encoding="utf-8")
    match = re.search(r"<!--\s*Item 3\(f\)\(25\).*?-->\s*<xs:element name=\"currentDelinquencyStatus\"[^>]+>", raw, re.S)
    docs = " ".join(match.group(0).split()) if match else ""
    if "number of days" not in docs.lower() or "governing transaction agreement" not in docs.lower():
        raise ValueError("Schema documentation does not state day-delinquency semantics")
    common = ET.parse(common_path)
    int_type = next((e for e in common.iter() if e.attrib.get("name") == "INTEGER_TYPE_8_A"), None)
    values = {e.attrib.get("value") for e in int_type.iter() if local(e.tag) in ("minInclusive", "maxInclusive")} if int_type is not None else set()
    if values != {"-99999999", "99999999"}:
        raise ValueError("Unexpected SEC INTEGER_TYPE_8_A bounds")
    return {"field": "currentDelinquencyStatus", "type": "INTEGER_TYPE_8_A",
            "meaning": docs, "min_inclusive": -99999999, "max_inclusive": 99999999,
            "xsd_sha256": sha256(auto_path), "common_xsd_sha256": sha256(common_path)}


def audit() -> Path:
    profile_path = contained(ROOT, PROFILE_PATH)
    profile_receipt_path = contained(ROOT, PROFILE_RECEIPT)
    profile = read_json(profile_path)
    receipt = read_json(profile_receipt_path)
    if (receipt.get("status") != "OFFICIAL_XML_PROFILED_AND_CERTIFICATE_RECONCILIATION_COMPLETE"
            or receipt.get("periods") != 20 or not receipt.get("all_monthly_balances_match_to_cent")):
        raise ValueError("Required official XML profile did not pass")
    schema = schema_evidence(contained(ROOT, SPEC), contained(ROOT, COMMON))
    case_path = contained(ROOT, f"artifacts/private/{CASE_ID}/reported_metrics.parquet")
    source_metrics = pq.read_table(case_path).to_pylist()
    idx = {(m["collection_end"], m["section"], m["metric"], m["slot"]): m for m in source_metrics}
    months = []
    checks = []
    for period in profile["periods"]:
        buckets = {name: {"accounts": 0, "ending_balance": Decimal(0)}
                   for name in ("current_0_30", *(b[0] for b in BUCKETS), "blank", "negative_unmapped")}
        for status, values in period["balance_by_delinquency_status_raw"].items():
            bucket = "blank"
            if status != "<BLANK>":
                days = int(status)
                if not -99_999_999 <= days <= 99_999_999:
                    raise ValueError("Observed delinquency status outside SEC XSD range")
                if days < 0:
                    bucket = "negative_unmapped"
                elif days <= 30:
                    bucket = "current_0_30"
                else:
                    bucket = next(name for name, lo, hi in BUCKETS if lo <= days <= hi)
            buckets[bucket]["accounts"] += int(values["accounts"])
            buckets[bucket]["ending_balance"] += Decimal(values["ending_balance"])
        date = period["report_date"]
        month_checks = []
        for name, _, _ in BUCKETS:
            metric = "delinquent_" + name
            for suffix, value_key in (("", "ending_balance"), ("_accounts", "accounts")):
                cert_metric = idx[(date, "pool", metric + suffix, "")]
                expected = Decimal(cert_metric["value"])
                actual = Decimal(buckets[name][value_key])
                delta = actual - expected
                check = {"report_date": date, "metric": metric + suffix,
                         "xml": str(actual), "certificate": str(expected), "delta": str(delta),
                         "pass": delta == 0}
                checks.append(check)
                month_checks.append(check)
        total_amt = sum((buckets[name]["ending_balance"] for name, _, _ in BUCKETS), Decimal(0))
        total_count = sum(buckets[name]["accounts"] for name, _, _ in BUCKETS)
        for metric, actual in (("delinquent_total", total_amt), ("delinquent_total_accounts", Decimal(total_count))):
            expected = Decimal(idx[(date, "pool", metric, "")]["value"])
            delta = actual - expected
            check = {"report_date": date, "metric": metric, "xml": str(actual),
                     "certificate": str(expected), "delta": str(delta), "pass": delta == 0}
            checks.append(check)
            month_checks.append(check)
        if buckets["blank"]["ending_balance"] != 0:
            raise ValueError("Blank delinquency observations contain positive/negative principal")
        months.append({"report_date": date, "buckets": {
            name: {"accounts": x["accounts"], "ending_balance": str(x["ending_balance"])}
            for name, x in buckets.items()},
            "blank_status_accounts_zero_balance": buckets["blank"]["ending_balance"] == 0,
            "certificate_checks_passed": sum(c["pass"] for c in month_checks),
            "certificate_checks_total": len(month_checks)})
    failures = [c for c in checks if not c["pass"]]
    out = contained(ROOT, "artifacts/private/woart-absee-delinquency-audit-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    result = {
        "status": "XSD_DAY_DELINQUENCY_MAPPED_AND_CERTIFICATE_RECONCILED" if not failures else "RECONCILIATION_FAILURES",
        "schema_evidence": schema,
        "profile_sha256": sha256(profile_path),
        "profile_receipt_sha256": sha256(profile_receipt_path),
        "monthly_servicer_case_receipt_sha256": sha256(ROOT / f"artifacts/private/{CASE_ID}/case-complete.json"),
        "periods": months,
        "checks": checks,
        "check_count": len(checks),
        "failed_checks": len(failures),
        "all_monthly_asset_delinquency_amounts_and_counts_match_certificate": not failures,
        "blank_status_accounts_have_zero_ending_balance": all(m["blank_status_accounts_zero_balance"] for m in months),
        "limitations": [
            "Day-count bucket matching validates reported amounts/counts; it does not reconstruct receivable-level contractual delinquency thresholds.",
            "Amendment Conversion Date and account-level payment-due amounts remain unknown.",
            "No default, cure, prepayment, or causal exit label is inferred from delinquency status alone.",
        ],
        "created_at": timestamp(),
        "visibility": "private",
        "public_release_approved": False,
    }
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": len(months), "checks": len(checks), "failed_checks": len(failures),
                                     "all_amounts_and_counts_match": result["all_monthly_asset_delinquency_amounts_and_counts_match_certificate"],
                                     "private": True})
    print(out)
    print(json.dumps({"status": result["status"], "checks": len(checks), "failed_checks": len(failures),
                      "all_amounts_and_counts_match": result["all_monthly_asset_delinquency_amounts_and_counts_match_certificate"]}))
    return out


if __name__ == "__main__":
    audit()
