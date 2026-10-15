"""Audit NSMO score and forbearance fields; write only aggregate bins/counts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from credit_atlas.nsmo_codebook import parse_sas_formats, parse_sas_labels


_NUMBER_OR_RANGE = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:\s*-\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)))?$")


def _compile_formats(sas_formats: dict[str, list[dict[str, str]]]) -> dict[str, list[tuple]]:
    result = {}
    for name, rows in sas_formats.items():
        rules = []
        for row in rows:
            value = row["format_value"].strip()
            if value.startswith("'") and value.endswith("'"):
                rules.append(("string", value[1:-1]))
                continue
            match = _NUMBER_OR_RANGE.fullmatch(value)
            if not match:
                raise ValueError(f"Unsupported FHFA SAS format domain in {name}")
            rules.append(("number", float(match.group(1)), float(match.group(2) or match.group(1))))
        result[name.casefold()] = rules
    return result


def _value_in_format(value: str, rules: list[tuple]) -> bool:
    for rule in rules:
        if rule[0] == "string" and value == rule[1]:
            return True
        if rule[0] == "number":
            try:
                number = float(value)
            except ValueError:
                continue
            if math.isfinite(number) and rule[1] <= number <= rule[2]:
                return True
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bucket_for_value(value: str, rules: list[tuple], labels: list[dict[str, str]]) -> str:
    """Map a numeric field value to the official SAS range token; preserve special codes."""
    for rule, label in zip(rules, labels):
        if rule[0] == "string" and value == rule[1]:
            return label["format_value"].strip()
        if rule[0] == "number":
            try:
                number = float(value)
            except ValueError:
                continue
            if math.isfinite(number) and rule[1] <= number <= rule[2]:
                return label["format_value"].strip()
    raise ValueError("Value is outside its reviewed FHFA SAS format")


def _field_summary(field: dict[str, str], counts: Counter[str], weights: Counter[str],
                   format_rows: list[dict[str, str]], row_count: int,
                   *, known_codes: set[str] | None = None,
                   affirmative_code: str | None = None) -> dict:
    total_weight = sum(weights.values())
    categories = []
    for item in format_rows:
        token = item["format_value"].strip()
        n = int(counts[token])
        weighted = float(weights[token])
        categories.append({
            "code": token,
            "label": item["format_label"],
            "n": n,
            "share_of_full_sample": n / row_count if row_count else 0.0,
            "weight_sum_descriptive_only": round(weighted, 2),
        })
    blank = int(counts["<blank>"])
    eligible_codes = known_codes or {item["format_value"].strip() for item in format_rows
                                     if item["format_value"].strip() not in {"-2", "-4"}}
    known = sum(int(counts[code]) for code in eligible_codes)
    weighted_known = sum(float(weights[code]) for code in eligible_codes)
    weighted_valid = weighted_known
    result = {
        "field": field["csv_column"],
        "label": field["sas_label"],
        "quarter": field.get("quarter", ""),
        "sas_format": field["sas_format"],
        "row_count": row_count,
        "blank_n": blank,
        "domain_n": sum(category["n"] for category in categories),
        "categories": categories,
        "available_n": known,
        "available_share_of_full_sample": known / row_count if row_count else 0.0,
        "available_weight_sum_descriptive_only": round(weighted_known, 2),
        "available_weighted_share_of_full_sample_descriptive_only": weighted_known / total_weight if total_weight else None,
    }
    if affirmative_code is not None:
        affirmative_n = int(counts[affirmative_code])
        affirmative_weight = float(weights[affirmative_code])
        result.update({
            "affirmative_code": affirmative_code,
            "affirmative_n": affirmative_n,
            "affirmative_share_of_known_responses": affirmative_n / known if known else None,
            "affirmative_weighted_share_of_known_responses_descriptive_only": (
                affirmative_weight / weighted_valid if weighted_valid else None),
        })
    return result


def audit(puf_csv: Path, sas_labels_path: Path, sas_formats_path: Path,
          field_dictionary_path: Path) -> dict:
    sas_labels = parse_sas_labels(sas_labels_path)
    sas_formats = parse_sas_formats(sas_formats_path)
    compiled = _compile_formats(sas_formats)
    with field_dictionary_path.open("r", encoding="utf-8-sig", newline="") as stream:
        dictionary = list(csv.DictReader(stream))
    family_fields = {
        family: [row for row in dictionary if row["field_family"] == family]
        for family in ("origination_mortgage_or_borrower_attribute", "cashout_refinance_flag",
                       "origination_credit_score", "quarterly_credit_score", "quarterly_forbearance")
    }
    origination_attributes = (family_fields["origination_mortgage_or_borrower_attribute"]
                              + family_fields["cashout_refinance_flag"])
    orig_scores = family_fields["origination_credit_score"]
    quarterly_scores = [row for row in family_fields["quarterly_credit_score"]
                        if row["csv_column"].endswith("_r")]
    forbearance = family_fields["quarterly_forbearance"]
    if len(orig_scores) != 5 or len(quarterly_scores) != 51 or len(forbearance) != 23:
        raise ValueError("NSMO score/forbearance dictionary families do not match v7.0")

    selected = origination_attributes + orig_scores + quarterly_scores + forbearance
    count_by_field: dict[str, Counter[str]] = defaultdict(Counter)
    weight_by_field: dict[str, Counter[str]] = defaultdict(Counter)
    unknown_by_field: Counter[str] = Counter()
    row_count = width_errors = 0
    with puf_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        if len(headers) != 587 or len({name.casefold() for name in headers}) != 587:
            raise ValueError("NSMO PUF must have 587 unique case-insensitive headers")
        positions = {name.casefold(): index for index, name in enumerate(headers)}
        if set(positions) != set(sas_labels):
            raise ValueError("NSMO PUF headers do not match official SAS labels")
        required = {row["csv_column"].casefold() for row in selected} | {"analysis_weight"}
        if not required.issubset(positions):
            raise ValueError("NSMO PUF is missing a score/forbearance field or Analysis_Weight")
        weight_index = positions["analysis_weight"]
        for row in reader:
            row_count += 1
            if len(row) != len(headers):
                width_errors += 1
                continue
            try:
                weight = float(row[weight_index].strip())
            except ValueError:
                weight = 0.0
            if not math.isfinite(weight) or weight <= 0:
                weight = 0.0
            for field in selected:
                name = field["csv_column"]
                value = row[positions[name.casefold()]].strip()
                if not value:
                    count_by_field[name]["<blank>"] += 1
                    continue
                format_name = field["sas_format"].casefold()
                if not _value_in_format(value, compiled[format_name]):
                    unknown_by_field[name] += 1
                    continue
                bucket = _bucket_for_value(value, compiled[format_name], sas_formats[field["sas_format"].casefold()])
                count_by_field[name][bucket] += 1
                weight_by_field[name][bucket] += weight

    def summarize(fields: list[dict[str, str]], known_codes: set[str] | None = None,
                  affirmative_code: str | None = None) -> list[dict]:
        return [
            _field_summary(field, count_by_field[field["csv_column"]],
                           weight_by_field[field["csv_column"]],
                           sas_formats[field["sas_format"].casefold()],
                           row_count,
                           known_codes=known_codes, affirmative_code=affirmative_code)
            for field in fields
        ]

    report = {
        "schema_version": "nsmo-domain-aggregate-audit-v1",
        "status": "PASS" if row_count == 62359 and width_errors == 0 and not unknown_by_field else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "puf_csv": {"bytes": puf_csv.stat().st_size, "sha256": _sha256(puf_csv)},
            "sas_labels_sha256": _sha256(sas_labels_path),
            "sas_formats_sha256": _sha256(sas_formats_path),
            "field_dictionary_sha256": _sha256(field_dictionary_path),
        },
        "schema": {"row_count": row_count, "column_count": 587,
                   "origination_attribute_fields": len(origination_attributes),
                   "origination_score_fields": len(orig_scores),
                   "quarterly_respondent_score_fields": len(quarterly_scores),
                   "quarterly_forbearance_fields": len(forbearance),
                   "bad_width_rows": width_errors,
                   "unknown_domain_counts": dict(sorted(unknown_by_field.items()))},
        "origination_attributes": summarize(origination_attributes),
        "origination_scores": summarize(orig_scores),
        "quarterly_respondent_scores": summarize(quarterly_scores),
        "quarterly_forbearance": summarize(forbearance, known_codes={"1", "2"}, affirmative_code="1"),
        "limitations": [
            "Score fields are VantageScore 3.0 categories and the published PUF bins, not exact scores or classic FICO.",
            "The five origination score fields represent respondent, spouse/partner, and up to three other-borrower roles; rows are mortgages, not a deduplicated borrower denominator.",
            "Quarterly respondent scores and forbearance are as-of snapshots; they must not be used before their observation quarter.",
            "Shares use either the full mortgage sample or known response codes as explicitly named; weighted shares are descriptive only and have no survey-design variance estimator.",
            "No identifiers, row-level values, target labels, PD estimates, or model outputs are included.",
        ],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puf-csv", required=True, type=Path)
    parser.add_argument("--sas-labels", required=True, type=Path)
    parser.add_argument("--sas-formats", required=True, type=Path)
    parser.add_argument("--field-dictionary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.puf_csv, args.sas_labels, args.sas_formats, args.field_dictionary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["schema"]["row_count"],
                      "origination_score_fields": report["schema"]["origination_score_fields"],
                      "origination_attribute_fields": report["schema"]["origination_attribute_fields"],
                      "quarterly_respondent_score_fields": report["schema"]["quarterly_respondent_score_fields"],
                      "forbearance_fields": report["schema"]["quarterly_forbearance_fields"],
                      "unknown_domain_fields": len(report["schema"]["unknown_domain_counts"])}, indent=2))


if __name__ == "__main__":
    main()
