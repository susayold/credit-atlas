"""Extract a conservative question-number/text inventory from official PDFs."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


_QUESTION_START = re.compile(r"(?m)(?<!\S)(\d{1,3})\.\s+(?=[A-Z\u00c0-\u00de])")
_SPACE = re.compile(r"\s+")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_question_text(value: str) -> str:
    """Normalize typography/whitespace only; retain wording and answer options."""
    value = value.replace("\u00ad", "").replace("\ufffd", " ")
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = value.replace("–", "-").replace("—", "-")
    return _SPACE.sub(" ", value).strip().casefold()


def split_question_blocks(text: str) -> list[dict[str, Any]]:
    """Split one questionnaire column into numbered blocks, retaining answer text."""
    matches = list(_QUESTION_START.finditer(text))
    blocks: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end]
        # Footer page numbers and the adjacent column's barcode/noise are not content.
        body = re.sub(r"(?m)^\s*\d{1,6}\s*$", " ", body)
        body = _SPACE.sub(" ", body).strip(" \n\r\t|•")
        if len(body) >= 12:
            blocks.append({
                "question_number": int(match.group(1)),
                "text": body,
                "normalized": normalize_question_text(body),
            })
    return blocks


def extract_questionnaire(path: Path) -> list[dict[str, Any]]:
    try:
        import pdfplumber
    except ImportError as error:  # pragma: no cover - dependency setup
        raise RuntimeError("Install the optional PDF parser: python -m pip install '.[research]'") from error
    records: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        # FHFA questionnaire packets place the numbered survey on printed pages 1-8.
        for page_index in range(2, min(10, len(pdf.pages))):
            page = pdf.pages[page_index]
            middle = page.width / 2
            for column, bounds in (("left", (0, 0, middle, page.height)), ("right", (middle, 0, page.width, page.height))):
                for block in split_question_blocks(page.crop(bounds).extract_text() or ""):
                    block["pdf_page"] = page_index + 1
                    block["column"] = column
                    records.append(block)
    # The same question may be split across columns only when the PDF has unusual layout.
    # Keep each occurrence so the audit can flag duplicates instead of silently merging.
    return records


def compare_questionnaire_packages(documents: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    by_question: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    package_rows = []
    for document in documents:
        path = Path(document["path"])
        if not path.is_absolute():
            path = root / path
        if not path.is_file() or sha256_file(path) != document["sha256"]:
            raise ValueError(f"Questionnaire source hash mismatch: {document['source_id']}")
        questions = extract_questionnaire(path)
        for question in questions:
            by_question[question["question_number"]][question["normalized"]].append({
                "package": document["source_id"],
                "waves": document["waves"],
                "page": question["pdf_page"],
                "column": question["column"],
                "text": question["text"],
            })
        package_rows.append({
            "package": document["source_id"],
            "waves": document["waves"],
            "sha256": document["sha256"],
            "question_occurrences": len(questions),
            "distinct_question_numbers": sorted({q["question_number"] for q in questions}),
        })

    question_profiles = []
    for number, variants in sorted(by_question.items()):
        packages = {row["package"] for group in variants.values() for row in group}
        question_profiles.append({
            "question_number": number,
            "package_count": len(packages),
            "text_variant_count": len(variants),
            "classification": "EXACT_TEXT_STABLE" if len(variants) == 1 else "REVIEW_WORDING_OR_SCALE",
            "variants": [
                {"text": rows[0]["text"], "package_wave_occurrences": [
                    {"package": row["package"], "waves": row["waves"]} for row in rows
                ]}
                for _, rows in sorted(variants.items())
            ],
        })
    return {
        "schema_version": "nsmo-questionnaire-comparison-v1",
        "status": "PASS",
        "source_document_count": len(package_rows),
        "package_profiles": package_rows,
        "question_profiles": question_profiles,
        "interpretation": [
            "Exact text stability is a candidate for manual review only; it does not prove construct, population, mode or response coding invariance.",
            "Different text requires review; question-number changes across waves are not themselves evidence of a changed construct.",
            "The extraction keeps response options with question text where present; visual layout may still require manual PDF inspection.",
            "Questionnaire answers are retrospective survey measures, not origination-time predictor approval.",
        ],
    }
