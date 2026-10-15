"""Audit aggregate NSMO survey-field response coverage by assigned wave."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def lookup_label(value: str, code_map: dict[str, str]) -> str:
    if value in code_map:
        return code_map[value]
    try:
        numeric = float(value)
    except ValueError:
        return ""
    for key, label in code_map.items():
        match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*", key)
        if match and float(match.group(1)) <= numeric <= float(match.group(2)):
            return label
    return ""


def compress_waves(values: list[int]) -> str:
    ordered = sorted(set(values))
    if not ordered:
        return ""
    ranges = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ";".join(ranges)


def write_public_coverage_csv(report: dict, dictionary_path: Path, output: Path) -> None:
    dictionary = {row["csv_column"]: row for row in csv.DictReader(
        dictionary_path.open(encoding="utf-8-sig", newline=""))}
    by_field: dict[str, list[dict]] = defaultdict(list)
    for row in report["field_wave_rows"]:
        by_field[row["field"]].append(row)
    columns = ["csv_column", "sas_label", "sas_format", "question_refs", "codebook_variant_flags",
               "observed_response_waves", "entirely_not_asked_waves", "partially_not_asked_waves",
               "not_applicable_waves", "waves_with_missing_code", "interpretation"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for name, field_rows in sorted(by_field.items()):
            metadata = dictionary[name]
            writer.writerow({
                "csv_column": name,
                "sas_label": metadata["sas_label"],
                "sas_format": metadata["sas_format"],
                "question_refs": metadata["survey_question_refs"],
                "codebook_variant_flags": metadata["wave_variant_flags"],
                "observed_response_waves": compress_waves([x["survey_wave"] for x in field_rows if x["substantive_or_other_labeled_n"] > 0]),
                "entirely_not_asked_waves": compress_waves([x["survey_wave"] for x in field_rows if x["not_asked_n"] == x["wave_n"]]),
                "partially_not_asked_waves": compress_waves([x["survey_wave"] for x in field_rows if 0 < x["not_asked_n"] < x["wave_n"]]),
                "not_applicable_waves": compress_waves([x["survey_wave"] for x in field_rows if x["not_applicable_n"] > 0]),
                "waves_with_missing_code": compress_waves([x["survey_wave"] for x in field_rows if x["missing_code_n"] > 0]),
                "interpretation": "Observed values and SAS availability codes only; wording/scale invariance requires questionnaire review.",
            })


def run_audit(puf: Path, dictionary: Path, labels_path: Path) -> dict:
    fields = list(csv.DictReader(dictionary.open(encoding="utf-8-sig", newline="")))
    survey_fields = [row for row in fields if row["field_family"] == "survey_response"]
    labels: dict[str, dict[str, str]] = defaultdict(dict)
    for row in csv.DictReader(labels_path.open(encoding="utf-8-sig", newline="")):
        labels[row["format_name"].casefold()][row["format_value"].strip()] = row["format_label"].casefold()
    field_codes = {
        row["csv_column"]: labels.get(row["sas_format"].casefold(), {})
        for row in survey_fields
    }
    headers = None
    wave_totals: Counter[str] = Counter()
    counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    unknown = Counter()
    with puf.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        positions = {name.casefold(): index for index, name in enumerate(headers)}
        if "survey_wave" not in positions or any(name not in positions for name in field_codes):
            raise ValueError("PUF header does not match the supplied survey field dictionary")
        for row in reader:
            wave = row[positions["survey_wave"]].strip()
            if not wave:
                raise ValueError("Blank survey_wave value")
            wave_totals[wave] += 1
            for name, code_map in field_codes.items():
                value = row[positions[name]].strip()
                if not value:
                    category = "blank"
                else:
                    label = lookup_label(value, code_map)
                    if "not asked in wave" in label:
                        category = "not_asked"
                    elif "not applicable" in label:
                        category = "not_applicable"
                    elif "don't know" in label or "do not know" in label:
                        category = "dont_know"
                    elif "missing" in label:
                        category = "missing_code"
                    elif label:
                        category = "substantive_or_other_labeled"
                    else:
                        category = "unmapped_value"
                        unknown[(name, value)] += 1
                counts[(name, wave)][category] += 1
    rows = []
    for (name, wave), counter in sorted(counts.items(), key=lambda item: (item[0][0], int(item[0][1]))):
        field = next(row for row in survey_fields if row["csv_column"] == name)
        rows.append({
            "field": name,
            "label": field["sas_label"],
            "sas_format": field["sas_format"],
            "survey_wave": int(wave),
            "wave_n": wave_totals[wave],
            "substantive_or_other_labeled_n": counter["substantive_or_other_labeled"],
            "dont_know_n": counter["dont_know"],
            "not_asked_n": counter["not_asked"],
            "not_applicable_n": counter["not_applicable"],
            "missing_code_n": counter["missing_code"],
            "blank_n": counter["blank"],
            "unmapped_value_n": counter["unmapped_value"],
        })
    return {
        "schema_version": "nsmo-wave-response-coverage-v1",
        "status": "PASS" if not unknown else "FAIL",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source": {"puf": puf.name, "puf_sha256": sha256(puf), "dictionary_sha256": sha256(dictionary), "value_labels_sha256": sha256(labels_path)},
        "row_count": sum(wave_totals.values()),
        "survey_field_count": len(survey_fields),
        "wave_count": len(wave_totals),
        "wave_totals": dict(sorted(((int(key), value) for key, value in wave_totals.items()))),
        "field_wave_rows": rows,
        "unknown_value_count": sum(unknown.values()),
        "unknown_value_fields": sorted({name for name, _ in unknown}),
        "limitations": [
            "Field availability by assigned survey wave is structural evidence, not proof that wording, construct, scale, sampling or response mode is invariant.",
            "Only explicit SAS-format labels identify not-asked, not-applicable, don't-know and missing codes; unmapped values fail the audit.",
            "Counts are mortgage-row aggregates and do not account for survey design variance or nonresponse adjustment.",
            "No identifiers or respondent-level records are emitted.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puf-csv", required=True, type=Path)
    parser.add_argument("--field-dictionary", required=True, type=Path)
    parser.add_argument("--value-labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--public-coverage-csv", required=True, type=Path)
    args = parser.parse_args()
    report = run_audit(args.puf_csv, args.field_dictionary, args.value_labels)
    write_public_coverage_csv(report, args.field_dictionary, args.public_coverage_csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["row_count"], "survey_fields": report["survey_field_count"], "waves": report["wave_count"], "field_wave_cells": len(report["field_wave_rows"]), "unmapped_values": report["unknown_value_count"], "public_coverage_csv": str(args.public_coverage_csv)}, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
