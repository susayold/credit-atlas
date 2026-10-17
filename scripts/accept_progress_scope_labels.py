#!/usr/bin/env python3
"""Check historical docs do not present CreditAtlas 26/50 as a D01-only rate."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RECEIPT = DOCS / "data" / "progress-scope-label-scan-2026-10-18.json"
CORRECTION_CUES = (
    "đính chính",
    "correction",
    "gán nhầm",
    "cách gán",
    "must be read with this correction",
    "not d01 alone",
)

# Match affirmative claims that D01 itself has the project-wide completion rate.
# Mentions in a scope correction are retained and excluded from this test.
STALE_CLAIM = re.compile(
    r"(?:\bd01(?:['’]s)?\s+(?:(?:master|requirement|completion|acceptance|overall)\s+)*"
    r"(?:count|rate|status)?\s*(?:remains?|stays?|is|at|=)\s*[:=]?\s*"
    r"(?:\*\*)?26\s*/\s*50|\bd01(?:['’]s)?\s+(?:still\s+)?"
    r"(?:\*\*)?26\s*/\s*50|\b26\s*/\s*50\s*(?:=\s*)?52\s*%[^\n]{0,80}"
    r"\bd01(?:['’]s)?\s+(?:completion|requirement|master|overall|rate))",
    re.IGNORECASE,
)

REQUIRED_CORRECTIONS = {
    "docs/BACKLOG_STATUS.md": "Scope correction, 2026-10-18",
    "docs/D01_PROGRESS_AND_DATA_PRIORITY_2026-10-16_VI.md": "Đính chính phạm vi tỷ lệ (18/10/2026)",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md": "Đính chính phạm vi thêm ngày 18/10/2026",
    "docs/IMPLEMENTATION_STATUS.md": "Scope note, 2026-10-18",
}
REGRESSION_CASES = {
    "D01 remains 26/50 (52%)": True,
    "D01's completion count remains 26/50": True,
    "The CreditAtlas-wide P1–P5 ledger remains 26/50; D01 model gates do not change.": False,
    "Scope correction: old D01 26/50 wording is wrong.": False,
}


def is_stale_claim(line: str) -> bool:
    lowered = line.casefold()
    return bool(STALE_CLAIM.search(line)) and not any(cue in lowered for cue in CORRECTION_CUES)


def main() -> int:
    regression_failures = [
        {"text": text, "expected_stale": expected, "actual_stale": is_stale_claim(text)}
        for text, expected in REGRESSION_CASES.items()
        if is_stale_claim(text) != expected
    ]
    markdown_files = sorted(DOCS.rglob("*.md"))
    missing_corrections: list[str] = []
    for rel, marker in REQUIRED_CORRECTIONS.items():
        path = ROOT / rel
        if not path.is_file() or marker.casefold() not in path.read_text(encoding="utf-8").casefold():
            missing_corrections.append(rel)

    candidates: list[dict[str, object]] = []
    stale_claims: list[dict[str, object]] = []
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            lowered = line.casefold()
            if "d01" not in lowered or not re.search(r"26\s*/\s*50|52\s*%", lowered):
                continue
            record = {
                "file": path.relative_to(ROOT).as_posix(),
                "line": line_no,
                "text": line.strip(),
            }
            candidates.append(record)
            if is_stale_claim(line):
                stale_claims.append(record)

    status = "PASS" if not regression_failures and not missing_corrections and not stale_claims else "FAIL"
    receipt = {
        "evidence_type": "creditatlas_progress_scope_label_static_acceptance",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "All Markdown files under docs/; no raw datasets scanned or modified.",
        "rule": "Reject affirmative claims assigning the CreditAtlas-wide 26/50 (52%) P1–P5 completion ledger to D01 itself.",
        "markdown_files_scanned": len(markdown_files),
        "d01_metric_cooccurrence_lines_reviewed": len(candidates),
        "required_scope_correction_files": list(REQUIRED_CORRECTIONS),
        "missing_scope_corrections": missing_corrections,
        "regression_cases": len(REGRESSION_CASES),
        "regression_failures": regression_failures,
        "stale_misattributions": stale_claims,
        "browser_ui_render_verified": False,
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
