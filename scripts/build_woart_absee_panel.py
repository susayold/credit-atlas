"""Stream official WOART ABS-EE XML into a private, provenance-preserving Parquet panel."""
from __future__ import annotations

import gzip
import json
import uuid
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

import pyarrow as pa
import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "woart-absee-history-948a4d8e4f18"
PROFILE = "artifacts/private/woart-absee-official-profile-0c8de9d2359d/profile.json"
PROFILE_RECEIPT = "artifacts/private/woart-absee-official-profile-0c8de9d2359d/receipt.json"
AUDIT_RECEIPT = "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/receipt.json"
AUTO_XSD = "data/private/structured/sec-abs-xml-spec-542aab868783/xsd/ABS XML Schema Files/eis_ABS_AutoLoanAssetData.xsd"
MAX_ROWS_PER_BATCH = 4096


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def schema_from_xsd(path: Path, fields: set[str]) -> tuple[pa.Schema, set[str]]:
    root = ET.parse(path).getroot()
    repeated = {element.attrib["name"] for element in root.iter()
                if local(element.tag) == "element" and "name" in element.attrib
                and element.attrib.get("maxOccurs", "1") == "unbounded"}
    if not {"assetTypeNumber", "assetNumber", "currentDelinquencyStatus"}.issubset(fields):
        raise ValueError("Required asset identity/day-count fields absent from observed schema")
    schema_fields = [pa.field("report_date", pa.date32(), nullable=False),
                     pa.field("accession", pa.string(), nullable=False)]
    for name in sorted(fields):
        if name == "currentDelinquencyStatus":
            schema_fields.append(pa.field(name + "_raw", pa.string()))
            schema_fields.append(pa.field(name + "_days_past_due", pa.int32()))
        elif name in repeated:
            schema_fields.append(pa.field(name, pa.list_(pa.string())))
        else:
            schema_fields.append(pa.field(name, pa.string()))
    return pa.schema(schema_fields), repeated


def parse_month(xml_path: Path, report: dict, fields: set[str], repeated: set[str], writer: pq.ParquetWriter) -> int:
    report_date = date.fromisoformat(report["report_date"])
    count = 0
    batch = []
    with gzip.open(xml_path, "rb") as source:
        for _, element in ET.iterparse(source, events=("end",)):
            if local(element.tag) != "assets" or any(local(child.tag) == "assets" for child in element):
                continue
            row = {}
            for child in element:
                name = local(child.tag)
                if name not in fields:
                    raise ValueError(f"Unexpected XML field {name} in {report_date}")
                row.setdefault(name, []).append(child.text)
            element.clear()
            if not row.get("assetTypeNumber") or not row.get("assetNumber"):
                raise ValueError("Missing required asset key")
            end_date = row.get("reportingPeriodEndingDate", [None])[0]
            if end_date != report_date.strftime("%m-%d-%Y"):
                raise ValueError("Asset reporting period end date mismatch")
            record = {"report_date": report_date, "accession": report["xml"]["accession"]}
            for name in fields:
                values = row.get(name, [])
                if name == "currentDelinquencyStatus":
                    raw = values[0] if values else None
                    record[name + "_raw"] = raw
                    if raw is None or not raw.strip():
                        record[name + "_days_past_due"] = None
                    else:
                        parsed = int(raw)
                        if not -99_999_999 <= parsed <= 99_999_999:
                            raise ValueError("Delinquency day count outside SEC XSD bounds")
                        record[name + "_days_past_due"] = parsed
                elif name in repeated:
                    record[name] = values or None
                else:
                    if len(values) > 1:
                        raise ValueError(f"Unexpected repeated non-repeating field {name}")
                    record[name] = values[0] if values else None
            batch.append(record)
            count += 1
            if len(batch) >= MAX_ROWS_PER_BATCH:
                writer.write_table(pa.Table.from_pylist(batch, schema=writer.schema))
                batch.clear()
    if batch:
        writer.write_table(pa.Table.from_pylist(batch, schema=writer.schema))
    return count


def build() -> Path:
    folder = contained(ROOT, "data/private/structured/" + SOURCE_ID)
    source_receipt = read_json(folder / "acquisition-complete.json")
    profile_path = contained(ROOT, PROFILE)
    profile_receipt_path = contained(ROOT, PROFILE_RECEIPT)
    profile = read_json(profile_path)
    profile_receipt = read_json(profile_receipt_path)
    audit_receipt = read_json(contained(ROOT, AUDIT_RECEIPT))
    if (source_receipt.get("status") != "SEC_OFFICIAL_ABSEE_HISTORY_ACQUIRED" or len(source_receipt.get("reports", [])) != 20
            or profile_receipt.get("rows") != 880773 or not profile_receipt.get("all_monthly_balances_match_to_cent")
            or audit_receipt.get("failed_checks") != 0 or audit_receipt.get("checks") != 200):
        raise ValueError("Official source/profile/delinquency audit prerequisites failed")
    fields = {field for period in profile["periods"] for field in period["fields"]}
    schema, repeated = schema_from_xsd(contained(ROOT, AUTO_XSD), fields)
    output = contained(ROOT, "data/private/derived/woart-absee-panel-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    data_folder = output / "monthly"
    data_folder.mkdir()
    manifest = []
    for report in source_receipt["reports"]:
        month = report["report_date"][:7]
        target = data_folder / f"{month}.parquet"
        writer = pq.ParquetWriter(target, schema, compression="zstd", use_dictionary=True)
        try:
            row_count = parse_month(folder / report["xml"]["file"], report, fields, repeated, writer)
        finally:
            writer.close()
        expected = next(x["rows"] for x in profile["periods"] if x["report_date"] == report["report_date"])
        if row_count != expected:
            raise ValueError(f"Panel row count mismatch for {month}")
        manifest.append({"report_date": report["report_date"], "accession": report["xml"]["accession"],
                         "file": f"monthly/{month}.parquet", "rows": row_count,
                         "bytes": target.stat().st_size, "sha256": sha256(target)})
        print(f"{month} {row_count} {target.stat().st_size}", flush=True)
    receipt = {
        "dataset_id": output.name,
        "status": "OFFICIAL_ABSEE_RAW_PANEL_PARQUET_BUILT",
        "source_id": SOURCE_ID,
        "source_receipt_sha256": sha256(folder / "acquisition-complete.json"),
        "source_profile_sha256": sha256(profile_path),
        "source_delinquency_audit_receipt_sha256": sha256(contained(ROOT, AUDIT_RECEIPT)),
        "schema_source": AUTO_XSD,
        "schema_sha256": sha256(contained(ROOT, AUTO_XSD)),
        "field_count": len(fields),
        "repeated_xsd_fields": sorted(fields & repeated),
        "row_count": sum(x["rows"] for x in manifest),
        "report_count": len(manifest),
        "report_start": manifest[0]["report_date"],
        "report_end": manifest[-1]["report_date"],
        "parquet_files": manifest,
        "data_contract": {
            "raw_xml_values_preserved_as_strings": True,
            "nulls_preserved": True,
            "repeated_xsd_fields_preserved_as_lists": True,
            "currentDelinquencyStatus_raw_preserved": True,
            "currentDelinquencyStatus_days_past_due_added_per_sec_xsd": True,
            "default_or_exit_labels_created": False,
            "private_asset_keys_in_data": True,
        },
        "created_at": timestamp(),
        "visibility": "private",
        "public_release_approved": False,
        "limitations": [
            "This is a typed, provenance-preserving raw monthly panel; it is not a default model dataset.",
            "Other amounts/codes remain raw source strings pending field-level unit and NULL semantics review.",
            "Asset keys are source identifiers and are not treated as borrower identities.",
            "Month-to-month disappearance is not assigned a default/prepayment/repo cause.",
        ],
    }
    write_new(output / "dataset-complete.json", receipt)
    print(output)
    print(json.dumps({"status": receipt["status"], "rows": receipt["row_count"],
                      "periods": receipt["report_count"], "fields": receipt["field_count"],
                      "parquet_bytes": sum(x["bytes"] for x in manifest)}))
    return output


if __name__ == "__main__":
    build()
