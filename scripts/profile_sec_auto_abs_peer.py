"""Profile the private one-period Toyota peer sample without exporting asset IDs."""
from __future__ import annotations

import gzip
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "sec-auto-abs-peer-fe7022e04210"
WOART_DATASET_ID = "woart-absee-panel-91efe12963d6"
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")


def tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def decimal(raw: str | None) -> Decimal | None:
    if raw is None or raw.strip() == "":
        return None
    text = raw.strip()
    if not DECIMAL_RE.fullmatch(text):
        raise ValueError("Non-decimal value in a decimal field")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal") from exc


def profile(source_id: str = SOURCE_ID) -> Path:
    source = contained(ROOT, "data/private/structured/" + source_id)
    receipt = read_json(source / "acquisition-complete.json")
    xml = source / receipt["asset_data_xml"]["file"]
    if (receipt.get("status") != "SEC_OFFICIAL_AUTO_ABS_PEER_PERIOD_ACQUIRED"
            or sha256(xml) != receipt["asset_data_xml"]["compressed_sha256"]
            or xml.stat().st_size != receipt["asset_data_xml"]["compressed_bytes"]):
        raise ValueError("Toyota peer acquisition receipt/hash verification failed")

    row_count = 0
    keys: set[tuple[str, str]] = set()
    duplicate_rows = 0
    field_rows = Counter()
    field_cells = Counter()
    multi_value_rows = Counter()
    parse_errors = Counter()
    numeric = {name: {"min": None, "max": None, "sum": Decimal(0), "negative": 0, "zero": 0, "positive": 0}
               for name in ("originalLoanAmount", "originalInterestRatePercentage",
                            "paymentToIncomePercentage", "reportingPeriodBeginningLoanBalanceAmount",
                            "reportingPeriodActualEndBalanceAmount", "chargedoffPrincipalAmount",
                            "recoveredAmount", "repossessedProceedsAmount")}
    ending_balance_counts = Counter()
    status_counts = Counter()
    period_counts = Counter()
    asset_type_counts = Counter()

    with gzip.open(xml, "rb") as stream:
        for _, asset in ET.iterparse(stream, events=("end",)):
            if tag_name(asset.tag) != "assets":
                continue
            row_count += 1
            cells: dict[str, list[str]] = {}
            for child in list(asset):
                name = tag_name(child.tag)
                cells.setdefault(name, []).append(child.text.strip() if child.text else "")
            for name, values in cells.items():
                field_rows[name] += 1
                field_cells[name] += len(values)
                if len(values) > 1:
                    multi_value_rows[name] += 1
            kind = cells.get("assetTypeNumber", [""])[0]
            asset_number = cells.get("assetNumber", [""])[0]
            if not kind or not asset_number:
                raise ValueError("Asset key missing in peer XML")
            key = (kind, asset_number)
            if key in keys:
                duplicate_rows += 1
            keys.add(key)
            asset_type_counts[kind] += 1
            report_dates = cells.get("reportingPeriodEndingDate", [""])
            period_counts[report_dates[0] if report_dates else "blank"] += 1
            status = cells.get("currentDelinquencyStatus", [""])[0]
            status_counts[status if status else "blank"] += 1

            ending = decimal(cells.get("reportingPeriodActualEndBalanceAmount", [None])[0])
            if ending is None:
                ending_balance_counts["blank"] += 1
            elif ending > 0:
                ending_balance_counts["positive"] += 1
            elif ending < 0:
                ending_balance_counts["negative"] += 1
            else:
                ending_balance_counts["zero"] += 1

            for name, stats in numeric.items():
                values = cells.get(name, [])
                for raw in values:
                    if raw == "":
                        continue
                    try:
                        value = decimal(raw)
                    except ValueError:
                        parse_errors[name] += 1
                        continue
                    if value is None:
                        continue
                    stats["min"] = value if stats["min"] is None else min(stats["min"], value)
                    stats["max"] = value if stats["max"] is None else max(stats["max"], value)
                    stats["sum"] += value
                    stats["negative"] += value < 0
                    stats["zero"] += value == 0
                    stats["positive"] += value > 0
            asset.clear()

    woart = contained(ROOT, "data/private/derived/" + WOART_DATASET_ID)
    manifest = read_json(woart / "dataset-complete.json")
    woart_field_names = set()
    for month in manifest["parquet_files"][:1]:
        woart_field_names = set(pq.ParquetFile(contained(woart, month["file"])).schema_arrow.names)
    peer_fields = set(field_rows)
    # Rename the private panel's source-value helper column back to the official XML field;
    # exclude internal date/accession and parsed-DPD helper columns from source-schema comparison.
    woart_fields = {name[:-4] if name.endswith("_raw") else name for name in woart_field_names
                    if name not in {"accession", "report_date", "currentDelinquencyStatus_days_past_due"}}
    serialized_numeric = {
        name: {k: (str(v) if isinstance(v, Decimal) else v) for k, v in stats.items()}
        for name, stats in numeric.items()
    }
    result = {
        "status": "SEC_AUTO_ABS_PEER_XML_PROFILED",
        "source_id": source_id,
        "source_receipt_sha256": sha256(source / "acquisition-complete.json"),
        "source_xml_compressed_sha256": sha256(xml),
        "peer": {"issuer": receipt["issuer"], "cik": receipt["cik"], "accession": receipt["accession"],
                 "filing_date": receipt["filing_date"], "report_date": receipt["report_date"]},
        "row_count": row_count,
        "unique_asset_keys": len(keys),
        "duplicate_key_rows": duplicate_rows,
        "period_counts": dict(period_counts),
        "asset_type_counts": dict(asset_type_counts),
        "ending_balance_state_counts": dict(ending_balance_counts),
        "raw_delinquency_counts": dict(status_counts),
        "field_count": len(peer_fields),
        "woart_field_count": len(woart_fields),
        "common_field_count": len(peer_fields & woart_fields),
        "peer_only_fields": sorted(peer_fields - woart_fields),
        "woart_only_fields": sorted(woart_fields - peer_fields),
        "field_row_coverage": {name: {"rows_present": count, "cell_count": field_cells[name]}
                               for name, count in sorted(field_rows.items())},
        "multi_value_fields": dict(sorted(multi_value_rows.items())),
        "numeric_field_profiles": serialized_numeric,
        "decimal_parse_errors": dict(parse_errors),
        "limitations": [
            "One Toyota Auto Receivables 2026-C report month only; no matched borrower/deal cohort or vintage curve.",
            "Distinct asset keys are within this filing only; no loan continuity or outcome is inferred.",
            "Field-name overlap does not qualify unit, enum, timing, or legal-semantic equivalence across issuers.",
            "Private profile omits source asset identifiers and keeps source-native amounts/scales.",
        ],
        "created_at": timestamp(),
        "visibility": "private",
        "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/sec-auto-abs-peer-profile-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "profile.json", result)
    write_new(out / "receipt.json", {
        "status": result["status"], "profile_sha256": sha256(out / "profile.json"),
        "rows": row_count, "fields": len(peer_fields), "common_fields_with_woart": len(peer_fields & woart_fields),
        "unique_asset_keys": len(keys), "duplicate_key_rows": duplicate_rows,
        "decimal_parse_errors": sum(parse_errors.values()),
        "visibility": "private", "public_release_approved": False,
    })
    print(out)
    print(json.dumps({"status": result["status"], "rows": row_count, "fields": len(peer_fields),
                      "common_fields_with_woart": len(peer_fields & woart_fields),
                      "duplicate_key_rows": duplicate_rows, "decimal_parse_errors": sum(parse_errors.values())}))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("Usage: profile_sec_auto_abs_peer.py [sec-auto-abs-peer-<id>]")
    profile(sys.argv[1] if len(sys.argv) == 2 else SOURCE_ID)
