"""Profile official Auto Loan XSD types against the private ABS-EE panel."""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
import xml.etree.ElementTree as ET

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "woart-absee-panel-91efe12963d6"
XSD_DIR = "data/private/structured/sec-abs-xml-spec-542aab868783/xsd/ABS XML Schema Files"
FIELDS = [
    "paymentToIncomePercentage", "reportingPeriodBeginningLoanBalanceAmount",
    "nextReportingPeriodPaymentAmountDue", "reportingPeriodInterestRatePercentage",
    "nextInterestRatePercentage", "servicingFeePercentage",
    "reportingPeriodActualEndBalanceAmount", "reportingPeriodScheduledPaymentAmount",
    "currentDelinquencyStatus", "zeroBalanceEffectiveDate", "zeroBalanceCode",
    "chargedoffPrincipalAmount", "recoveredAmount", "repossessedIndicator",
    "repossessedProceedsAmount",
]
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")


def panel_column(field: str) -> str:
    return "currentDelinquencyStatus_raw" if field == "currentDelinquencyStatus" else field


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def schema_dictionary(xsd_dir: Path) -> dict:
    ns = {"x": "http://www.w3.org/2001/XMLSchema"}
    documents = {p.name: ET.parse(p).getroot() for p in xsd_dir.glob("*.xsd")}
    elements = {}
    for root in documents.values():
        for element in root.findall(".//x:element", ns):
            name = element.attrib.get("name")
            if name in FIELDS:
                elements[name] = {
                    "type": element.attrib.get("type", "").split(":")[-1],
                    "min_occurs": element.attrib.get("minOccurs", "1"),
                    "max_occurs": element.attrib.get("maxOccurs", "1"),
                }
    if set(elements) != set(FIELDS):
        raise ValueError(f"Auto Loan XSD fields missing: {sorted(set(FIELDS) - set(elements))}")
    types = {}
    for root in documents.values():
        for simple in root.findall(".//x:simpleType", ns):
            name = simple.attrib.get("name")
            if name and name not in types:
                facets = {}
                for node in simple.iter():
                    tag = local(node.tag)
                    if tag in {"restriction", "enumeration", "pattern", "minInclusive", "maxInclusive", "totalDigits", "fractionDigits", "minLength", "maxLength"}:
                        facets.setdefault(tag, []).append(node.attrib)
                types[name] = facets
    for name, declaration in elements.items():
        declaration["facets"] = types.get(declaration["type"], {})
        if not declaration["type"]:
            raise ValueError(f"Missing declared type for {name}")
    return elements


def empty_profile() -> dict:
    return {"rows": 0, "present_cells": 0, "null_or_empty_cells": 0, "value_counts": Counter(),
            "decimal_min": None, "decimal_max": None, "decimal_max_scale": 0,
            "decimal_negative_count": 0, "decimal_zero_count": 0, "decimal_parse_errors": 0,
            "examples": Counter()}


def audit() -> Path:
    dataset = contained(ROOT, "data/private/derived/" + DATASET_ID)
    manifest = read_json(dataset / "dataset-complete.json")
    if manifest.get("status") != "OFFICIAL_ABSEE_RAW_PANEL_PARQUET_BUILT" or manifest.get("report_count") != 20:
        raise ValueError("Official 20-period panel prerequisite not verified")
    xsd_dir = contained(ROOT, XSD_DIR)
    schema = schema_dictionary(xsd_dir)
    profiles = {name: empty_profile() for name in FIELDS}
    monthly_nulls = []
    cross = Counter()
    columns = [panel_column(field) for field in FIELDS]
    for item in manifest["parquet_files"]:
        path = contained(dataset, item["file"])
        month_nulls = {"report_date": item["report_date"], "rows": 0, "fields": {}}
        for field in FIELDS:
            month_nulls["fields"][field] = {"present": 0, "null_or_empty": 0}
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=columns):
            rows = batch.to_pylist()
            month_nulls["rows"] += len(rows)
            for field in FIELDS:
                profile = profiles[field]
                month = month_nulls["fields"][field]
                profile["rows"] += len(rows)
                for row in rows:
                    value = row.get(panel_column(field))
                    if value is None or value == [] or value == "":
                        profile["null_or_empty_cells"] += 1
                        month["null_or_empty"] += 1
                        continue
                    profile["present_cells"] += 1
                    month["present"] += 1
                    values = value if isinstance(value, list) else [value]
                    for raw in values:
                        text = str(raw)
                        if len(profile["examples"]) < 12:
                            profile["examples"][text] += 1
                        if field in {"zeroBalanceCode", "repossessedIndicator", "currentDelinquencyStatus"}:
                            profile["value_counts"][text] += 1
                        if "DECIMAL" in schema[field]["type"]:
                            if not DECIMAL_RE.fullmatch(text):
                                profile["decimal_parse_errors"] += 1
                                continue
                            try:
                                number = Decimal(text)
                            except InvalidOperation:
                                profile["decimal_parse_errors"] += 1
                                continue
                            profile["decimal_min"] = number if profile["decimal_min"] is None else min(profile["decimal_min"], number)
                            profile["decimal_max"] = number if profile["decimal_max"] is None else max(profile["decimal_max"], number)
                            scale = max(0, -number.as_tuple().exponent)
                            profile["decimal_max_scale"] = max(profile["decimal_max_scale"], scale)
                            profile["decimal_negative_count"] += number < 0
                            profile["decimal_zero_count"] += number == 0
            for row in rows:
                codes = row.get("zeroBalanceCode") or []
                chargeoff = row.get("chargedoffPrincipalAmount")
                has_code4 = "4" in codes
                cross["zero_balance_code_4_cells"] += has_code4
                cross["code_4_with_chargeoff_amount"] += has_code4 and chargeoff is not None
                cross["code_4_without_chargeoff_amount"] += has_code4 and chargeoff is None
                cross["chargeoff_amount_present_cells"] += chargeoff is not None
                cross["chargeoff_amount_without_code_4"] += chargeoff is not None and not has_code4
                repo = row.get("repossessedIndicator")
                proceeds = row.get("repossessedProceedsAmount")
                cross["repossessed_true_cells"] += repo == "true"
                cross["repossessed_false_cells"] += repo == "false"
                cross["repossessed_true_zero_proceeds_cells"] += repo == "true" and proceeds == "0.00"
                cross["repossessed_true_nonzero_proceeds_cells"] += repo == "true" and proceeds not in (None, "0.00")
                cross["repossessed_false_nonzero_proceeds_cells"] += repo == "false" and proceeds not in (None, "0.00")
        monthly_nulls.append(month_nulls)

    normalized = {}
    for name, p in profiles.items():
        normalized[name] = {
            "xsd": schema[name], "panel_column": panel_column(name), "rows": p["rows"], "present_cells": p["present_cells"],
            "null_or_empty_cells": p["null_or_empty_cells"],
            "observed_value_counts": dict(sorted(p["value_counts"].items())),
            "observed_examples": dict(p["examples"]),
            "decimal_min": str(p["decimal_min"]) if p["decimal_min"] is not None else None,
            "decimal_max": str(p["decimal_max"]) if p["decimal_max"] is not None else None,
            "decimal_max_observed_scale": p["decimal_max_scale"],
            "decimal_negative_value_count": p["decimal_negative_count"],
            "decimal_zero_value_count": p["decimal_zero_count"],
            "decimal_parse_errors": p["decimal_parse_errors"],
        }
    for field, profile in normalized.items():
        if "DECIMAL" not in profile["xsd"]["type"]:
            continue
        facets = profile["xsd"]["facets"]
        fraction_digits = int(facets["fractionDigits"][0]["value"])
        min_value = Decimal(facets["minInclusive"][0]["value"])
        max_value = Decimal(facets["maxInclusive"][0]["value"])
        if profile["decimal_parse_errors"] or profile["decimal_max_observed_scale"] > fraction_digits:
            raise ValueError(f"Decimal values violate XSD format for {field}")
        if Decimal(profile["decimal_min"]) < min_value or Decimal(profile["decimal_max"]) > max_value:
            raise ValueError(f"Decimal values violate XSD range for {field}")
    if cross["code_4_without_chargeoff_amount"] or cross["chargeoff_amount_without_code_4"]:
        raise ValueError("Code 4 and charged-off principal field did not align in the published panel")
    out = contained(ROOT, "artifacts/private/woart-absee-field-semantics-audit-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    result = {"status": "AUTO_LOAN_XSD_FIELDS_PROFILED_AGAINST_OFFICIAL_PANEL", "dataset_id": DATASET_ID,
              "dataset_receipt_sha256": sha256(dataset / "dataset-complete.json"),
              "xsd_directory": XSD_DIR, "xsd_file_hashes": {p.name: sha256(p) for p in xsd_dir.glob("*.xsd")},
              "period_count": len(monthly_nulls), "row_count": sum(x["rows"] for x in monthly_nulls),
              "field_profiles": normalized, "monthly_nulls": monthly_nulls,
              "cross_field_checks": dict(cross),
              "semantics": {"xsd_min_occurs_zero_means_optional_in_xml": True,
                  "blank_or_absent_is_preserved_as_missing_and_is_not_imputed": True,
                  "decimal_percentage_units_are_not_inferred_from_field_name": True,
                  "observed_values_are_not_contractual_default_or_loss_labels": True},
              "limitations": ["Schema types constrain XML representation but do not by themselves establish transaction-specific business meaning or units.",
                  "This is a completeness and value-profile audit, not a full record-by-record legal or certificate validation.",
                  "The observed panel belongs to one securitization and does not establish population representativeness."],
              "created_at": timestamp(), "visibility": "private", "public_release_approved": False}
    write_new(out / "audit.json", result)
    receipt = {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
               "periods": result["period_count"], "rows": result["row_count"],
               "fields": len(FIELDS), "decimal_parse_errors": sum(v["decimal_parse_errors"] for v in normalized.values()),
               "xsd_fields_verified": len(schema), "visibility": "private", "public_release_approved": False}
    write_new(out / "receipt.json", receipt)
    print(out)
    print(json.dumps(receipt))
    return out


if __name__ == "__main__":
    audit()
