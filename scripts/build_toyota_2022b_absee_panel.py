"""Build a source-preserving monthly Parquet panel for Toyota Auto Receivables 2022-B."""
from __future__ import annotations

import gzip
import json
import uuid
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "toyota-2022b-absee-history-435918e7209a"
REFERENCE_PANEL = "data/private/derived/woart-absee-panel-91efe12963d6/monthly/2025-01.parquet"
AUTO_XSD = "data/private/structured/sec-abs-xml-spec-542aab868783/xsd/ABS XML Schema Files/eis_ABS_AutoLoanAssetData.xsd"
MAX_ROWS_PER_BATCH = 4096


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def source_schema(fields: set[str]) -> tuple[pa.Schema, set[str]]:
    xsd_path = contained(ROOT, AUTO_XSD)
    root = ET.parse(xsd_path).getroot()
    repeated = {element.attrib["name"] for element in root.iter()
                if local(element.tag) == "element" and "name" in element.attrib
                and element.attrib.get("maxOccurs", "1") == "unbounded"}
    if not {"assetTypeNumber", "assetNumber", "currentDelinquencyStatus", "reportingPeriodEndingDate"} <= fields:
        raise ValueError("Required identity/report fields absent from the auto-loan schema")
    built = [pa.field("report_date", pa.date32(), nullable=False), pa.field("accession", pa.string(), nullable=False)]
    for name in sorted(fields):
        if name == "currentDelinquencyStatus":
            built.extend([pa.field(name + "_raw", pa.string()), pa.field(name + "_days_past_due", pa.int32())])
        elif name in repeated:
            built.append(pa.field(name, pa.list_(pa.string())))
        else:
            built.append(pa.field(name, pa.string()))
    return pa.schema(built), repeated


def parse_month(xml_path: Path, report: dict, fields: set[str], repeated: set[str],
                writer: pq.ParquetWriter) -> tuple[int, int]:
    report_date = date.fromisoformat(report["report_date"])
    count = 0
    batch = []
    keys = set()
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
            key = (row["assetTypeNumber"][0], row["assetNumber"][0])
            if key in keys:
                raise ValueError(f"Duplicate asset key in Toyota 2022-B {report_date}")
            keys.add(key)
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
                        raise ValueError(f"Repeated non-repeating field {name}")
                    record[name] = values[0] if values else None
            batch.append(record)
            count += 1
            if len(batch) >= MAX_ROWS_PER_BATCH:
                writer.write_table(pa.Table.from_pylist(batch, schema=writer.schema))
                batch.clear()
    if batch:
        writer.write_table(pa.Table.from_pylist(batch, schema=writer.schema))
    return count, len(keys)


def build() -> Path:
    source = contained(ROOT, "data/private/structured/" + SOURCE_ID)
    receipt_path = source / "acquisition-complete.json"
    receipt = read_json(receipt_path)
    reports = receipt.get("reports", [])
    if (receipt.get("status") != "SEC_OFFICIAL_TOYOTA_2022B_ABSEE_HISTORY_ACQUIRED"
            or len(reports) != 51 or receipt.get("report_start") != "2022-04-30"
            or receipt.get("report_end") != "2026-06-30"):
        raise ValueError("Toyota 2022-B acquisition receipt/period span mismatch")

    reference = pq.ParquetFile(contained(ROOT, REFERENCE_PANEL)).schema_arrow.names
    internal = {"report_date", "accession", "currentDelinquencyStatus_days_past_due"}
    fields = {name[:-4] if name.endswith("_raw") else name for name in reference if name not in internal}
    schema, repeated = source_schema(fields)
    output = contained(ROOT, "data/private/derived/toyota-2022b-absee-panel-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    monthly = output / "monthly"
    monthly.mkdir()
    manifests = []
    for report in reports:
        xml_record = report["xml"]
        path = contained(source, xml_record["file"])
        if (path.stat().st_size != xml_record["compressed_bytes"]
                or sha256(path) != xml_record["compressed_sha256"]):
            raise ValueError(f"Source XML compressed hash/size mismatch for {report['report_date']}")
        target = monthly / (report["report_date"][:7] + ".parquet")
        writer = pq.ParquetWriter(target, schema, compression="zstd", use_dictionary=True)
        try:
            rows, unique_keys = parse_month(path, report, fields, repeated, writer)
        finally:
            writer.close()
        if rows != unique_keys:
            raise ValueError("Monthly unique-key count mismatch")
        manifests.append({"report_date": report["report_date"], "accession": xml_record["accession"],
                          "file": "monthly/" + target.name, "rows": rows, "unique_asset_keys": unique_keys,
                          "bytes": target.stat().st_size, "sha256": sha256(target)})
        print(f"{report['report_date']} {rows} {target.stat().st_size}", flush=True)

    result = {
        "dataset_id": output.name, "status": "OFFICIAL_TOYOTA_2022B_ABSEE_PANEL_PARQUET_BUILT",
        "source_id": SOURCE_ID, "source_receipt_sha256": sha256(receipt_path),
        "reference_schema_source": REFERENCE_PANEL, "schema_source": AUTO_XSD,
        "schema_sha256": sha256(contained(ROOT, AUTO_XSD)), "field_count": len(fields),
        "repeated_xsd_fields": sorted(fields & repeated), "row_count": sum(x["rows"] for x in manifests),
        "report_count": len(manifests), "report_start": manifests[0]["report_date"],
        "report_end": manifests[-1]["report_date"], "parquet_files": manifests,
        "data_contract": {"raw_xml_values_preserved_as_strings": True, "nulls_preserved": True,
                          "repeated_xsd_fields_preserved_as_lists": True,
                          "currentDelinquencyStatus_raw_preserved": True,
                          "currentDelinquencyStatus_days_past_due_added_per_sec_xsd": True,
                          "default_or_exit_labels_created": False, "private_asset_keys_in_data": True},
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False,
        "limitations": ["One issuer/deal, 51 monthly snapshots; not a representative retail credit population.",
                        "Monthly source-key uniqueness does not establish borrower identity.",
                        "Zero balances/disappearance and sign of reported amounts are not assigned causal labels.",
                        "Amounts/codes remain raw pending full XSD/semantic/certificate review."],
    }
    write_new(output / "dataset-complete.json", result)
    write_new(output / "receipt.json", {"status": result["status"], "dataset_sha256": sha256(output / "dataset-complete.json"),
                                        "periods": result["report_count"], "rows": result["row_count"],
                                        "fields": result["field_count"],
                                        "duplicate_key_periods": 0, "visibility": "private",
                                        "public_release_approved": False})
    print(output)
    print(json.dumps({"status": result["status"], "periods": result["report_count"],
                      "rows": result["row_count"], "fields": result["field_count"],
                      "parquet_bytes": sum(x["bytes"] for x in manifests)}))
    return output


if __name__ == "__main__":
    build()
