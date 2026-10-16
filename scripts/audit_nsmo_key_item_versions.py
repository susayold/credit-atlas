"""Locate selected credit-relevant items and response scales in FHFA PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import csv
from datetime import datetime, timezone
from pathlib import Path


ITEMS = {
    "x05f": "your credit history or credit score",
    "x88d": "late payments will lower my credit rating",
    "x88e": "lenders shouldn't care about any late payments",
    "x88f": "it is okay to default or stop making mortgage payments",
    "x93b": "difficulties making your mortgage payments",
    "x94a": "pay your bills for the next 3 months without borrowing",
}


def normalized(value: str) -> str:
    value = value.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", value).casefold().strip()


def locate_items(documents: list[dict], root: Path) -> dict:
    try:
        import pdfplumber
    except ImportError as error:  # pragma: no cover
        raise RuntimeError("Install PDF research dependencies with .[research]") from error
    profiles = []
    for document in documents:
        path = Path(document["path"])
        if not path.is_absolute():
            path = root / path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != document["sha256"]:
            raise ValueError(f"Questionnaire hash mismatch: {document['source_id']}")
        occurrences = []
        with pdfplumber.open(path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                middle = page.width / 2
                for column, bounds in (("left", (0, 0, middle, page.height)), ("right", (middle, 0, page.width, page.height))):
                    text = page.crop(bounds).extract_text() or ""
                    clean = normalized(text)
                    for field, phrase in ITEMS.items():
                        needle = normalized(phrase)
                        start = clean.find(needle)
                        if start >= 0:
                            occurrences.append({
                                "field": field,
                                "phrase": phrase,
                                "page": page_index + 1,
                                "column": column,
                                "context": clean[max(0, start - 180):min(len(clean), start + len(needle) + 240)],
                            })
        profiles.append({
            "package": document["source_id"],
            "waves": document["waves"],
            "document_sha256": digest,
            "items": occurrences,
        })
    coverage = {field: [row["package"] for row in profiles if any(item["field"] == field for item in row["items"])] for field in ITEMS}
    return {
        "schema_version": "nsmo-key-item-version-locator-v1",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "package_count": len(profiles),
        "item_phrases": ITEMS,
        "package_profiles": profiles,
        "phrase_package_coverage": coverage,
        "limitations": [
            "Text extraction locates items in the questionnaire; it can miss wording that varies and cannot determine measurement invariance.",
            "Response-scale and routing interpretation must be checked visually against each PDF and the corresponding Appendix C/SAS labels.",
            "The selected items are retrospective survey answers and are not thereby approved as origination predictors.",
        ],
    }


def write_comparability_index(report: dict, dictionary_path: Path, labels_path: Path,
                              coverage_path: Path, output: Path) -> None:
    fields = {row["csv_column"]: row for row in csv.DictReader(
        dictionary_path.open(encoding="utf-8-sig", newline=""))}
    coverage = {row["csv_column"]: row for row in csv.DictReader(
        coverage_path.open(encoding="utf-8-sig", newline=""))}
    label_groups: dict[str, list[str]] = {}
    for row in csv.DictReader(labels_path.open(encoding="utf-8-sig", newline="")):
        label_groups.setdefault(row["format_name"].casefold(), []).append(
            f"{row['format_value']}={row['format_label']}"
        )
    rows = []
    for name, phrase in ITEMS.items():
        field = fields[name]
        rows.append({
            "field": name,
            "sas_label": field["sas_label"],
            "puf_nonmissing_value_waves": coverage[name]["puf_nonmissing_value_waves"],
            "not_asked_waves": coverage[name]["entirely_not_asked_waves"],
            "question_refs": field["survey_question_refs"],
            "sas_format": field["sas_format"],
            "scale_labels": " | ".join(label_groups.get(field["sas_format"].casefold(), [])),
            "exact_item_phrase_found_in_packages": len(report["phrase_package_coverage"][name]),
            "assessment": (
                "COMMON_ITEM_CANDIDATE; wording found in all packages; waves 1-10: "
                "borrow enough money from a bank or credit union; waves 11-46: "
                "borrow a significant amount from a bank or credit union; PVERYFM "
                "labels unchanged; stratify or run sensitivity before interpreting "
                "long-run trend; verify routing/respondent/mode and scale before use"
                if name == "x94a" else
                "COMMON_ITEM_CANDIDATE; wording found in all packages; verify routing/respondent/mode and scale before trend use"
            ),
        })
    additional = {
        "x14a": "Separate from x14a_1: PIMPFM scale, nonmissing PUF values in waves 7-46; do not pool raw numeric codes.",
        "x14a_1": "Separate from x14a: PVERYFM scale, nonmissing PUF values in waves 1-6; do not pool raw numeric codes.",
        "x20j": "Wave-limited item: PUF values in waves 13-24 only; not-asked in other waves. Codebook parsed wave range is not authoritative.",
    }
    for name, assessment in additional.items():
        field = fields[name]
        rows.append({
            "field": name,
            "sas_label": field["sas_label"],
            "puf_nonmissing_value_waves": coverage[name]["puf_nonmissing_value_waves"],
            "not_asked_waves": coverage[name]["entirely_not_asked_waves"],
            "question_refs": field["survey_question_refs"],
            "sas_format": field["sas_format"],
            "scale_labels": " | ".join(label_groups.get(field["sas_format"].casefold(), [])),
            "exact_item_phrase_found_in_packages": "",
            "assessment": assessment,
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-receipt", required=True, type=Path)
    parser.add_argument("--field-dictionary", required=True, type=Path)
    parser.add_argument("--value-labels", required=True, type=Path)
    parser.add_argument("--wave-coverage", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--comparability-csv", required=True, type=Path)
    args = parser.parse_args()
    acquisition = json.loads(args.acquisition_receipt.read_text(encoding="utf-8"))
    report = locate_items(acquisition["documents"], Path.cwd())
    write_comparability_index(report, args.field_dictionary, args.value_labels,
                              args.wave_coverage, args.comparability_csv)
    report["acquisition_receipt_sha256"] = hashlib.sha256(args.acquisition_receipt.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": report["status"], "packages": report["package_count"], "phrase_coverage": {key: len(value) for key, value in report["phrase_package_coverage"].items()}, "comparability_csv": str(args.comparability_csv)}, indent=2))


if __name__ == "__main__":
    main()
