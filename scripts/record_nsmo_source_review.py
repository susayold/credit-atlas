"""Record the separate, source-specific FHFA/CFPB NSMO D02 research evidence."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
RECEIPT_PATH = ROOT / "artifacts/private/nsmo-source-docs-20261015/receipt.json"
FILES = [
    "docs/D01_NSMO_SOURCE_REVIEW_VI.md",
    "docs/NSMO_D02_CASE_BUILD_PLAN_VI.md",
    "docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md",
    "docs/BACKLOG_STATUS.md",
    "docs/PLAN_MODULE_01.md",
    "docs/TEST_SUITE_2026-10-15_VI.md",
    "docs/IMPLEMENTATION_STATUS.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "data/private/mortgage/nsmo-2026-05-27/source_docs/nsmo-technical-report-v70.pdf",
    "data/private/mortgage/nsmo-2026-05-27/source_docs/nsmo-appendix-c-v70.pdf",
    "data/private/mortgage/nsmo-2026-05-27/source_docs/nsmo-appendix-d-v70.pdf",
    "data/private/mortgage/nsmo-2026-05-27/source_docs/nsmo_v70_labels.sas",
    "data/private/mortgage/nsmo-2026-05-27/source_docs/nsmo_v70_formats.sas",
    "docs/data/nsmo-v70-field-dictionary.csv",
    "docs/data/nsmo-v70-value-labels.csv",
    "src/credit_atlas/nsmo_codebook.py",
    "src/credit_atlas/nsmo_views.py",
    "scripts/audit_nsmo_codebook.py",
    "scripts/audit_nsmo_performance_states.py",
    "scripts/audit_nsmo_weighted_tabulations.py",
    "artifacts/private/nsmo-codebook-20261015/receipt.json",
    "artifacts/private/nsmo-performance-state-audit-20261015/receipt.json",
    "artifacts/private/nsmo-weighted-tabulation-audit-20261015/receipt.json",
    "artifacts/private/nsmo-dictionary-browser-qa-20261015/receipt.json",
    "artifacts/private/test-suite-direct-20261015-nsmo-dictionary/receipt.json",
    "artifacts/private/public-mirror-tests-20261015-nsmo-dictionary/receipt.json",
    "src/credit_atlas/nsmo.py",
    "tests/test_nsmo.py",
    str(RECEIPT_PATH.relative_to(ROOT)),
    "artifacts/private/nsmo-parser-tests-20261015/junit.xml",
    "artifacts/private/test-suite-direct-20261015/receipt.json",
    "artifacts/private/test-suite-direct-20261015-nsmo-stream/receipt.json",
    "scripts/test.ps1",
]

receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
if receipt.get("status") != "PASS" or len(receipt.get("files", [])) != 5:
    raise ValueError("Official NSMO source documentation receipt did not pass")
if "PUF download is separately tracked" not in receipt.get("scope", ""):
    raise ValueError("NSMO documentation receipt must distinguish sources from PUF acquisition")

ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
requirement = next(row for row in ledger["requirements"] if row["id"] == "P2.08")
entry = {
    "checkpoint": "fhfa-nsmo-public-cohort-review-20261015",
    "document": "docs/D01_NSMO_SOURCE_REVIEW_VI.md",
    "source_review": "docs/D01_DATA_ACCESS_CHECK_2026-10-15_VI.md",
    "receipt": str(RECEIPT_PATH.relative_to(ROOT)),
    "scope": "Separate NSMO D02 source acquired after explicit FHFA Notice/Terms authorization; 62,359-row PUF structural/code-domain audit; 587/587 Appendix C + SAS field mapping; 59 formats/377 value labels; state/censoring profile; Appendix D Table 1 recomputation matches 462/462 published rounded cells; aggregate-only dashboard and searchable dictionary; no PUF rows or IDs in public repo. No Freddie vintage is added and no PD/model claim is made.",
    "remaining": "Review survey question/wave variants and point-in-time allowlist; complete D02 domain UI/browser acceptance; freeze a justified at-risk set, event/horizon/competing-risk/censoring and survey-weight variance protocol before considering model study.",
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
