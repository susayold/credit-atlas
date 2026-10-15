"""Pin descriptive-chart support audit evidence without closing model gates."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
AUDIT_PATH = ROOT / "artifacts/private/d01-chart-support-a5a39d8e7acc/receipt.json"
BROWSER_PATH = ROOT / "artifacts/private/browser-qa-7a281849bd29/receipt.json"
FILES = [
    "docs/D01_CHART_SUPPORT_AUDIT_VI.md", "docs/D01_REPRODUCTION_AUDIT_VI.md",
    "docs/D01_CASE_STUDY_VI.md", "docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md",
    "docs/BACKLOG_STATUS.md",
    "docs/PLAN_MODULE_01.md", "docs/IMPLEMENTATION_STATUS.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md", "docs/TEST_SUITE_2026-10-15_VI.md",
    "scripts/audit_d01_chart_support.py",
    "scripts/browser_qa.py", "scripts/record_d01_chart_support.py", "apps/web/style.css", "apps/web/app.js",
    "scripts/test_batches.py", "src/credit_atlas/foundation.py",
    "tests/test_foundation_reproduction_receipts.py",
    str(AUDIT_PATH.relative_to(ROOT)), "artifacts/private/browser-qa-7a281849bd29/receipt.json",
    "artifacts/private/d01-a24484b21a21/reproduction-pipeline-0415306845cd.json",
    "artifacts/private/test-batches-e8453a2adc33/receipt.json",
]

audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
if audit.get("status") != "PASS" or len(audit.get("checks", [])) != 6:
    raise ValueError("Chart/support audit receipt did not pass")
browser = json.loads(BROWSER_PATH.read_text(encoding="utf-8"))
if browser.get("status") != "PASS" or len(browser.get("checks", [])) != 39:
    raise ValueError("Expanded browser receipt did not pass 39 checks")
suite = json.loads((ROOT / "artifacts/private/test-batches-e8453a2adc33/receipt.json").read_text(encoding="utf-8"))
if suite.get("status") != "PASS" or suite.get("collected_tests") != 1568:
    raise ValueError("Latest full-suite receipt did not pass")

ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
if ledger.get("count") != 50:
    raise ValueError("Requirement ledger count changed")
for requirement_id in ("P2.03", "P2.05", "P2.07", "P2.09"):
    requirement = next(row for row in ledger["requirements"] if row["id"] == requirement_id)
    entry = {
        "checkpoint": "d01-chart-support-rendered-series-20261015",
        "audit": str(AUDIT_PATH.relative_to(ROOT)),
        "browser": str(BROWSER_PATH.relative_to(ROOT)),
        "scope": "Supplemental real-run chart/support reconciliation for monthly stock denominators, vintage risk sets, profile shares, annual/lifetime transition matrices and signed loss bridge; browser confirms rendered series/support, sparse warnings, five mobile screens, and fail-closed stale/missing/unlisted runs, 503, connection failure and malformed JSON; does not prove multi-vintage qualification, market representativeness or a qualified model.",
        "status": "PASS",
        "full_completion_proven": False,
        "evidence_sha256": {path: sha256(ROOT / path) for path in FILES},
    }
    items = requirement.setdefault("runtime_regression_evidence", [])
    old = next((item for item in items if item.get("checkpoint") == entry["checkpoint"]), None)
    if old is None:
        items.append(entry)
    else:
        old.clear()
        old.update(entry)

for requirement_id, scope in (
        ("P2.02", "Supplemental clean-rebuild reproduction of the 2012 frozen source: same manifest/code fingerprint; 13 parquet tables and four stable summaries with zero differences. This proves supplied-corpus reproducibility only."),
        ("P2.10", "Descriptive case-study handoff documents the question, data, target, denominator contracts, findings, limitations and linked evidence; qualified model card and final R4 release remain unmet.")):
    requirement = next(row for row in ledger["requirements"] if row["id"] == requirement_id)
    receipt = "artifacts/private/d01-a24484b21a21/reproduction-pipeline-0415306845cd.json"
    entry = {"checkpoint": "d01-reproduction-and-descriptive-handoff-20261015",
             "audit": receipt, "document": "docs/D01_CASE_STUDY_VI.md", "scope": scope,
             "status": "PASS", "full_completion_proven": False,
             "evidence_sha256": {path: sha256(ROOT / path) for path in FILES}}
    items = requirement.setdefault("runtime_regression_evidence", [])
    old = next((item for item in items if item.get("checkpoint") == entry["checkpoint"]), None)
    if old is None:
        items.append(entry)
    else:
        old.clear()
        old.update(entry)

LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"requirements": ["P2.03", "P2.05", "P2.07", "P2.09"],
                  "status": "PASS", "full_completion_proven": False}, ensure_ascii=False))
