"""Reconcile FHFA NSMO v7.0 codebook metadata with the PUF header only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from credit_atlas.nsmo_codebook import (
    parse_codebook_pdf,
    parse_sas_formats,
    parse_sas_labels,
    read_csv_header,
    reconcile_headers,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_dictionary(
    codebook_pdf: Path,
    puf_csv: Path,
    sas_labels_path: Path,
    sas_formats_path: Path,
    output_csv: Path,
    format_output_csv: Path,
) -> dict:
    records = parse_codebook_pdf(codebook_pdf)
    headers = read_csv_header(puf_csv)
    reconcile_headers(records, headers)
    sas_labels = parse_sas_labels(sas_labels_path)
    sas_formats = parse_sas_formats(sas_formats_path)
    if len(records) != 587 or len(sas_labels) != 587 or len(sas_formats) != 59:
        raise ValueError(
            f"Unexpected source metadata counts: codebook={len(records)}, "
            f"SAS labels={len(sas_labels)}, SAS formats={len(sas_formats)}"
        )
    field_names = {record["csv_column"] for record in records}
    if field_names != set(sas_labels):
        raise ValueError("Codebook field names and official SAS-label fields do not match")
    missing_formats = sorted({
        metadata["sas_format"].casefold()
        for metadata in sas_labels.values()
    } - set(sas_formats))
    if missing_formats:
        raise ValueError(f"SAS labels reference undefined formats: {missing_formats}")
    for record in records:
        record.update(sas_labels[record["csv_column"]])

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    columns = list(records[0])
    with output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)

    format_output_csv.parent.mkdir(parents=True, exist_ok=True)
    format_columns = ["format_name", "format_value", "format_label"]
    with format_output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=format_columns)
        writer.writeheader()
        for format_name in sorted(sas_formats):
            writer.writerows(sas_formats[format_name])

    family_counts = Counter(record["field_family"] for record in records)
    timing_counts = Counter(record["timing_class"] for record in records)
    variant_counts = Counter(
        flag
        for record in records
        for flag in record["wave_variant_flags"].split(";")
        if flag
    )
    return {
        "schema_version": "nsmo-codebook-reconciliation-v1",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "codebook": {
            "file": codebook_pdf.name,
            "sha256": sha256(codebook_pdf),
            "official_url": "https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-c-v70.pdf",
            "pdf_pages": 336,
            "codebook_physical_pages": "5-153",
            "field_count": len(records),
            "part_a_count": sum(record["codebook_part"] == "A" for record in records),
            "part_b_count": sum(record["codebook_part"] == "B" for record in records),
        },
        "sas_labels": {
            "file": sas_labels_path.name,
            "sha256": sha256(sas_labels_path),
            "field_count": len(sas_labels),
            "official_url": "https://www.fhfa.gov/document/d/nsmo/nsmo_v70_labels.sas",
        },
        "sas_formats": {
            "file": sas_formats_path.name,
            "sha256": sha256(sas_formats_path),
            "format_count": len(sas_formats),
            "labeled_value_count": sum(len(values) for values in sas_formats.values()),
            "official_url": "https://www.fhfa.gov/document/d/nsmo/nsmo_v70_formats.sas",
        },
        "puf_header": {
            "file": puf_csv.name,
            "header_count": len(headers),
            "matched_header_count": len(headers),
            "unmatched_header_count": 0,
            "rows_read": 0,
            "loan_identifiers_read": 0,
        },
        "dictionary": {
            "file": output_csv.name,
            "sha256": sha256(output_csv),
            "value_labels_file": format_output_csv.name,
            "value_labels_sha256": sha256(format_output_csv),
            "field_family_counts": dict(sorted(family_counts.items())),
            "timing_class_counts": dict(sorted(timing_counts.items())),
            "wave_variant_flag_counts": dict(sorted(variant_counts.items())),
        },
        "interpretation": [
            "Header reconciliation reads the PUF header only; it never reads or exports mortgage rows.",
            "Survey question responses are collected after mortgage origination and are not approved as origination-time predictors by this audit.",
            "Quarterly scores, performance, forbearance, and MTM-LTV remain time-indexed; only values known on or before a defined score date may be considered for a dynamic model.",
            "The dictionary is schema/use metadata, not a target, model feature approval, or PD result.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codebook", required=True, type=Path)
    parser.add_argument("--puf-csv", required=True, type=Path)
    parser.add_argument("--sas-labels", required=True, type=Path)
    parser.add_argument("--sas-formats", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--format-output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    report = build_dictionary(
        args.codebook, args.puf_csv, args.sas_labels, args.sas_formats,
        args.output, args.format_output,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "field_count": report["codebook"]["field_count"],
        "part_a_count": report["codebook"]["part_a_count"],
        "part_b_count": report["codebook"]["part_b_count"],
        "header_count": report["puf_header"]["header_count"],
        "matched_header_count": report["puf_header"]["matched_header_count"],
        "rows_read": report["puf_header"]["rows_read"],
        "sas_label_count": report["sas_labels"]["field_count"],
        "sas_format_count": report["sas_formats"]["format_count"],
        "value_label_count": report["sas_formats"]["labeled_value_count"],
        "field_family_counts": report["dictionary"]["field_family_counts"],
        "wave_variant_flag_counts": report["dictionary"]["wave_variant_flag_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
