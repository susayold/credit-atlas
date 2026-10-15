"""Record the reviewed FHFA/CFPB NSMO alternative source without claiming data ingestion."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
RECEIPT_PATH = ROOT / "artifacts/private/nsmo-source-docs-20261015/receipt.json"
FILES = [
    "docs/D01_NSMO_SOURCE_REVIEW_VI.md",
    "docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md",
    "docs/BACKLOG_STATUS.md",
    "docs/PLAN_MODULE_01.md",
    "docs/TEST_SUITE_2026-10-15_VI.md",
    "docs/IMPLEMENTATION_STATUS.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "data/private/mortgage/nsmo-2026-05-27/source_docs/nsmo-technical-report-v70.pdf",
    "data/private/mortgage/nsmo-2026-05-27/source_docs/nsmo-appendix-c-v70.pdf",
    "src/credit_atlas/nsmo.py",
    "tests/test_nsmo.py",
    str(RECEIPT_PATH.relative_to(ROOT)),
    "artifacts/private/nsmo-parser-tests-20261015/junit.xml",
    "artifacts/private/test-suite-direct-20261015/receipt.json",
    "artifacts/private/test-suite-direct-20261015-nsmo-stream/receipt.json",
    "scripts/test.ps1",
]

receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
if receipt.get("status") != "PASS" or len(receipt.get("files", [])) != 2:
    raise ValueError("Official NSMO source documentation receipt did not pass")
if "no public-use microdata downloaded" not in receipt.get("scope", ""):
    raise ValueError("NSMO docs receipt must distinguish docs from microdata")

ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
requirement = next(row for row in ledger["requirements"] if row["id"] == "P2.08")
entry = {
    "checkpoint": "fhfa-nsmo-public-cohort-review-20261015",
    "document": "docs/D01_NSMO_SOURCE_REVIEW_VI.md",
    "source_review": "docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md",
    "receipt": str(RECEIPT_PATH.relative_to(ROOT)),
    "scope": "FHFA/CFPB NSMO May 2026 documentation/codebook reviewed; identifies a distinct 2013-2024 mortgage cohort with quarterly performance through 2025Q3, as-of credit-score and origination variables, and sample weights. Codebook-grounded CSV-streaming status helper passes nine synthetic-fixture unit tests; full repository suite then passed 1,577/1,577. No PUF payload, file-level validation, additional Freddie vintage, or qualified PD study is claimed.",
    "remaining": "User authorization to acknowledge FHFA monitoring/terms; retrieve and freeze PUF; audit keys, weights, status history, censoring, target compatibility, and source-specific temporal evaluation.",
    "status": "PARTIAL",
    "added_freddie_vintages": 0,
    "full_completion_proven": False,
    "evidence_sha256": {path: sha256(ROOT / path) for path in FILES},
}
items = requirement.setdefault("partial_evidence", [])
old = next((item for item in items if item.get("checkpoint") == entry["checkpoint"]), None)
if old is None:
    items.append(entry)
else:
    old.clear()
    old.update(entry)

LEDGER_PATH.write_text(
    json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)
print(json.dumps({"requirement": "P2.08", "status": "PARTIAL", "added_freddie_vintages": 0}, ensure_ascii=False))
