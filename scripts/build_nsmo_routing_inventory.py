"""Build a conservative field-to-question routing review from the public NSMO codebook."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


FIELDS = [
    "codebook_order", "csv_column", "codebook_name", "survey_question_refs", "resolved_question_refs",
    "question_reference_status", "reference_evidence", "questionnaire_wave_coverage", "label_phrase_check",
    "survey_wave_ranges", "codebook_condition", "routing_gate_fields", "routing_gate_questions",
    "routing_gate_resolution", "wave_variant_flags", "route_review_status", "predictor_use",
    "routing_review_required",
]


def _waves(value: str) -> set[int]:
    result: set[int] = set()
    for token in value.split(";"):
        match = re.fullmatch(r"\s*(\d+)\s*[-–]\s*(\d+)\s*", token)
        if match:
            start, end = map(int, match.groups())
            result.update(range(start, end + 1))
        elif token.strip().isdigit():
            result.add(int(token.strip()))
    return result


def classify(row: dict[str, str]) -> tuple[str, str]:
    condition = row["codebook_condition"].strip()
    if "retired gateway" in condition.casefold():
        return "LEGACY_GATEWAY_MAPPING_REQUIRED", "Identify which historical gateway/response path applies by wave; do not infer a stable not-asked meaning across versions."
    if condition:
        return "CONDITIONAL_ROUTING_DOCUMENTED", "Check applicable wave questionnaire and response mode; blank/not-asked values may reflect routing rather than borrower state."
    return "NO_CONDITION_LISTED_IN_CODEBOOK", "No condition is listed in this codebook row; this is not proof the item was asked identically in every wave or mode."


def build(source: Path, output: Path, reconciliation_path: Path | None = None) -> dict:
    with source.open(encoding="utf-8-sig", newline="") as stream:
        fields = list(csv.DictReader(stream))
    survey = [row for row in fields if row.get("field_family") == "survey_response"]
    if len(fields) != 587 or len(survey) != 319 or len({row["csv_column"].casefold() for row in survey}) != 319:
        raise ValueError("Expected the reviewed 587-field dictionary with 319 survey-response fields")
    reconciliations = {}
    if reconciliation_path is not None:
        with reconciliation_path.open(encoding="utf-8-sig", newline="") as stream:
            reconciliations = {row["csv_column"]: row for row in csv.DictReader(stream)}
        if len(reconciliations) != 7 or not set(reconciliations).issubset({row["csv_column"] for row in survey}):
            raise ValueError("Expected the reviewed seven-field NSMO question-reference reconciliation")
        by_field = {row["csv_column"]: row for row in survey}
        for name, evidence in reconciliations.items():
            code_match = re.match(r"x(\d+)", name, re.IGNORECASE)
            field_waves = _waves(by_field[name]["survey_wave_ranges"])
            question_waves = _waves(evidence["questionnaire_wave_coverage"])
            if (not code_match or evidence["question_ref"] != f"Q{int(code_match.group(1))}"
                    or not field_waves.issubset(question_waves)
                    or evidence["label_phrase_check"] not in {"MATCHED_IN_QUESTIONNAIRE_TEXT", "WAVE_VARIANT_REVIEW"}):
                raise ValueError(f"Question-reference reconciliation failed identifier/wave/evidence checks: {name}")
    rows = []
    dictionary_names = {row["csv_column"] for row in fields}
    for row in survey:
        status, review = classify(row)
        reconciliation = reconciliations.get(row["csv_column"], {})
        resolved_refs = row["survey_question_refs"].strip() or reconciliation.get("question_ref", "")
        reference_status = (
            "EXPLICIT_IN_CODEBOOK" if row["survey_question_refs"].strip()
            else "RECONCILED_FROM_FIELD_ID_AND_QUESTIONNAIRE" if reconciliation else "UNRESOLVED"
        )
        evidence = (
            "Explicit question reference in codebook"
            if row["survey_question_refs"].strip()
            else reconciliation.get("reference_basis", "No question reference; reconciliation pending")
        )
        if reconciliation.get("label_phrase_check") == "WAVE_VARIANT_REVIEW":
            review += " Review the documented historical wording/scale variant before combining responses."
        if reference_status == "UNRESOLVED":
            review = "Question reference is missing. " + review
        gate_fields = sorted({
            "x" + match.group(1).casefold()
            for match in re.finditer(r"\bX(\d+(?:_\d+)?)\b", row["codebook_condition"], re.IGNORECASE)
        })
        if not row["codebook_condition"].strip():
            gate_resolution = "NO_CONDITION_LISTED"
        elif "retired gateway" in row["codebook_condition"].casefold():
            gate_resolution = "RETIRED_GATEWAY_UNSPECIFIED"
        elif gate_fields and set(gate_fields).issubset(dictionary_names):
            gate_resolution = "EXPLICIT_GATE_FIELDS_PRESENT"
        else:
            gate_resolution = "GATE_FIELDS_NOT_RECONCILED"
        gate_questions = []
        for name in gate_fields:
            gate_match = re.match(r"x(\d+)", name)
            if gate_match:
                gate_questions.append(f"Q{int(gate_match.group(1))}")
        rows.append({**row, "resolved_question_refs": resolved_refs,
                     "question_reference_status": reference_status, "reference_evidence": evidence,
                     "questionnaire_wave_coverage": reconciliation.get("questionnaire_wave_coverage", ""),
                     "label_phrase_check": reconciliation.get("label_phrase_check", "NOT_APPLICABLE"),
                     "routing_gate_fields": ";".join(gate_fields),
                     "routing_gate_questions": ";".join(sorted(set(gate_questions))),
                     "routing_gate_resolution": gate_resolution,
                     "route_review_status": status,
                     "routing_review_required": review})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in FIELDS} for row in rows)
    from collections import Counter

    return {"rows": len(rows), "route_statuses": dict(sorted(Counter(row["route_review_status"] for row in rows).items())),
            "question_reference_statuses": dict(sorted(Counter(row["question_reference_status"] for row in rows).items()))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=Path("docs/data/nsmo-v70-field-dictionary.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/nsmo-v70-routing-review.csv"))
    parser.add_argument("--reconciliation", type=Path,
                        default=Path("docs/data/nsmo-v70-question-reference-reconciliation.csv"))
    args = parser.parse_args()
    print(build(args.dictionary, args.output, args.reconciliation))


if __name__ == "__main__":
    main()
