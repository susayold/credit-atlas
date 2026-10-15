"""Reconcile NSMO v7.0 codebook fields to the PUF header without reading rows.

The parser is deliberately restricted to the codebook's Section 1 tables and
reads only the CSV header. It never loads or emits mortgage records.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


_FIELD = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_RANGE = re.compile(r"\bWaves?\s+(\d+)\s*[–−\-�]{1,4}\s*(\d+)\b", re.IGNORECASE)
_QUESTION = re.compile(r"\bQ\s*(\d{1,3})\s*:", re.IGNORECASE)
_QUARTER_SUFFIX = re.compile(r"(?:^|_)(?:[A-Za-z]+)?(\d{2})(\d{2})(?:_|$)")
_SAS_LABEL = re.compile(
    r'^\s*(\w+)\s+length\s*=\s*(\$?\d+)\.\s+format\s*=\s*(\$?[A-Za-z0-9_]+)\.\s+label\s*=\s*"([^"]*)"\s*$'
)
_SAS_FORMAT_HEADER = re.compile(r"^\s*value\s+(\$?[A-Za-z0-9_]+)\s*$", re.IGNORECASE)
_SAS_FORMAT_VALUE = re.compile(
    r'''^\s*(.*?)\s*=\s*(?:'((?:[^']|'')*)'|"((?:[^"]|"")*)")\s*$'''
)


def classify_nsmo_field(name: str, ordinal: int, part: str) -> dict[str, str]:
    """Return a conservative source family and predictor-use gate."""
    normalized = name.casefold()
    if ordinal == 1 or normalized == "nsmoid":
        return {"field_family": "sample_identifier", "timing_class": "identifier", "predictor_use": "NEVER_FEATURE"}
    if ordinal == 2 or normalized == "survey_wave":
        return {"field_family": "survey_wave", "timing_class": "survey_design_metadata", "predictor_use": "SAMPLE_METADATA_ONLY"}
    if ordinal == 3 or normalized == "analysis_weight":
        return {"field_family": "analysis_weight", "timing_class": "survey_design_metadata", "predictor_use": "ESTIMATION_ONLY_AFTER_DESIGN_REVIEW"}
    if part == "A" or ordinal <= 322:
        return {"field_family": "survey_response", "timing_class": "post_origination_survey_response", "predictor_use": "NOT_ORIGINATION_TIME_SAFE"}
    if normalized.startswith("score_orig_"):
        return {"field_family": "origination_credit_score", "timing_class": "at_origination", "predictor_use": "CANDIDATE_AFTER_ROLE_AND_MISSINGNESS_REVIEW; VANTAGESCORE_NOT_FICO"}
    if normalized.startswith("score_"):
        return {"field_family": "quarterly_credit_score", "timing_class": "quarterly_as_of", "predictor_use": "DYNAMIC_ONLY_AT_OR_BEFORE_INDEX_DATE; NO_FUTURE_VALUES"}
    if normalized.startswith("perf_status_"):
        return {"field_family": "quarterly_performance_status", "timing_class": "quarterly_outcome_history", "predictor_use": "OUTCOME_HISTORY; NOT_SAME_PERIOD_OR_FUTURE_FEATURE"}
    if normalized.startswith("close_"):
        return {"field_family": "mortgage_termination", "timing_class": "termination_through_2025Q3", "predictor_use": "COMPETING_EVENT_OR_CENSORING_ONLY"}
    if normalized == "cashout":
        return {"field_family": "cashout_refinance_flag", "timing_class": "origination_characteristic", "predictor_use": "CANDIDATE_AFTER_DEFINITION_AND_PURPOSE_REVIEW"}
    if normalized.startswith("forb"):
        return {"field_family": "quarterly_forbearance", "timing_class": "quarterly_as_of", "predictor_use": "DYNAMIC_ONLY_AT_OR_BEFORE_INDEX_DATE; NOT_ORIGINATION_FEATURE"}
    if normalized.startswith("mtmltv"):
        return {"field_family": "quarterly_mark_to_market_ltv", "timing_class": "quarterly_as_of", "predictor_use": "DYNAMIC_ONLY_AT_OR_BEFORE_INDEX_DATE; REVIEW_LOOKAHEAD"}
    return {"field_family": "origination_mortgage_or_borrower_attribute", "timing_class": "origination_characteristic", "predictor_use": "CANDIDATE_AFTER_ASOF_AND_MISSINGNESS_REVIEW"}


def parse_codebook_pdf(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Extract Section 1 variable names and short labels from FHFA's PDF."""
    try:
        import pdfplumber
    except ImportError as error:  # pragma: no cover - exercised by CLI setup
        raise RuntimeError("Install the optional PDF parser: python -m pip install pdfplumber") from error

    records: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as document:
        # Physical pages 5-153 contain Section 1, codebook entries 1-587.
        for page_index in range(4, min(153, len(document.pages))):
            page_number = page_index + 1
            for table in document.pages[page_index].extract_tables():
                for row in table:
                    if len(row) >= 6:
                        ordinal_cell, name_cell, definition_cell = row[0], row[1], row[4]
                        part = "A"
                    elif len(row) >= 4:
                        ordinal_cell, name_cell, definition_cell = row[0], row[1], row[2]
                        part = "B"
                    else:
                        continue

                    ordinals = [
                        int(value.strip())
                        for value in (ordinal_cell or "").splitlines()
                        if re.fullmatch(r"\s*\d+\s*", value)
                    ]
                    names = [
                        value.strip()
                        for value in (name_cell or "").splitlines()
                        if _FIELD.fullmatch(value.strip())
                    ]
                    if not ordinals and not names:
                        continue
                    if len(ordinals) != len(names):
                        raise ValueError(
                            f"Codebook table mismatch on PDF page {page_number}: "
                            f"{len(ordinals)} ordinals but {len(names)} field names"
                        )

                    definitions = [
                        value.strip()
                        for value in (definition_cell or "").splitlines()
                        if value.strip()
                        and not value.strip().lower().startswith("(continued")
                        and value.strip().lower() not in {
                            "see close_status_1224, close_year and close_month for clarification of",
                            "codes a and b.",
                        }
                    ]
                    for position, (ordinal, name) in enumerate(zip(ordinals, names)):
                        if len(definitions) == len(names):
                            definition = definitions[position]
                        else:
                            definition = " ".join(definitions)
                        condition = re.search(
                            r"\((\s*when\b[^)]*)\)", name_cell or "", re.IGNORECASE | re.DOTALL
                        )
                        wave_ranges = sorted(
                            {f"{start}-{end}" for start, end in _RANGE.findall(definition)},
                            key=lambda value: tuple(int(part) for part in value.split("-")),
                        )
                        question_refs = sorted({
                            f"Q{number}"
                            for number in _QUESTION.findall(definition)
                        })
                        name_lc = name.casefold()
                        classification = classify_nsmo_field(name, ordinal, part)
                        quarter = ""
                        match = _QUARTER_SUFFIX.search(name)
                        if match and classification["timing_class"] == "quarterly_as_of":
                            month, year = (int(piece) for piece in match.groups())
                            quarter = f"20{year:02d}-Q{(month - 1) // 3 + 1}"

                        records.append({
                            "codebook_order": ordinal,
                            "csv_column": name_lc,
                            "codebook_name": name,
                            "codebook_part": part,
                            "survey_wave_ranges": ";".join(wave_ranges),
                            "survey_question_refs": ";".join(question_refs),
                            "codebook_condition": " ".join(condition.group(1).split()) if condition else "",
                            "wave_variant_flags": ";".join(flag for flag, present in (
                                ("MULTI_QUESTION_ID", len(question_refs) > 1),
                                ("DIFFERENT_SCALE", "different scale" in definition.casefold()),
                                ("NOT_ASKED_IN_SOME_WAVES", "question not asked" in definition.casefold()),
                            ) if present),
                            "quarter": quarter,
                            "pdf_page": page_number,
                            "printed_page": f"C-{page_number - 2}",
                            **classification,
                        })

    records.sort(key=lambda record: record["codebook_order"])
    ordinals = [record["codebook_order"] for record in records]
    names = [record["csv_column"] for record in records]
    if len(records) != 587 or sorted(ordinals) != list(range(1, 588)):
        raise ValueError(f"Expected codebook fields 1-587; parsed {len(records)} records")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate codebook variable names (case-insensitive)")
    return records


def parse_sas_labels(path: str | Path) -> dict[str, dict[str, str]]:
    """Read FHFA's official SAS label/format assignment for each field."""
    labels: dict[str, dict[str, str]] = {}
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        if "label =" not in line:
            continue
        match = _SAS_LABEL.fullmatch(line)
        if not match:
            raise ValueError(f"Unparsed SAS label statement at line {line_number}")
        name, length, format_name, label = match.groups()
        key = name.casefold()
        if key in labels:
            raise ValueError(f"Duplicate SAS label field: {name}")
        labels[key] = {
            "sas_length": length,
            "sas_format": format_name,
            "sas_label": label,
        }
    return labels


def parse_sas_formats(path: str | Path) -> dict[str, list[dict[str, str]]]:
    """Parse categorical/range value labels from FHFA's SAS format file."""
    formats: dict[str, list[dict[str, str]]] = {}
    active: str | None = None
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        if active is None:
            match = _SAS_FORMAT_HEADER.fullmatch(line)
            if match:
                active = match.group(1).casefold()
                if active in formats:
                    raise ValueError(f"Duplicate SAS format: {active}")
                formats[active] = []
            continue
        if line.strip() == ";":
            active = None
            continue
        if not line.strip():
            continue
        match = _SAS_FORMAT_VALUE.fullmatch(line)
        if not match:
            raise ValueError(f"Unparsed SAS format statement at line {line_number}")
        value, single_quoted, double_quoted = match.groups()
        formats[active].append({
            "format_name": active,
            "format_value": value.strip(),
            "format_label": (single_quoted if single_quoted is not None else double_quoted).replace("''", "'").replace('""', '"').strip(),
        })
    if active is not None:
        raise ValueError(f"Unterminated SAS format block: {active}")
    return formats


def read_csv_header(csv_path: str | Path) -> list[str]:
    """Read only the first line of the PUF for schema reconciliation."""
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle), [])


def reconcile_headers(records: list[dict[str, Any]], headers: list[str]) -> None:
    codebook = {record["csv_column"] for record in records}
    physical = {header.casefold() for header in headers}
    if len(headers) != len(physical):
        raise ValueError("PUF header contains case-insensitive duplicate fields")
    missing_in_codebook = sorted(physical - codebook)
    missing_in_puf = sorted(codebook - physical)
    if missing_in_codebook or missing_in_puf:
        raise ValueError(
            f"Header/codebook mismatch: absent from codebook={missing_in_codebook}; "
            f"absent from PUF={missing_in_puf}"
        )
