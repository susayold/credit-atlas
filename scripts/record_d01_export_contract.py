"""Record real schema-2 export scope/privacy/browser evidence in P2 ledgers."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
AUDIT = ROOT / "artifacts/private/d01-export-contract-dc182aeaae7e/receipt.json"
BROWSER = ROOT / "artifacts/private/browser-qa-d7e3d9425f14/receipt.json"
SUITE = ROOT / "artifacts/private/test-batches-6149b9cdd460/receipt.json"
FILES = [
    "docs/D01_EXPORT_CONTRACT_AUDIT_VI.md",
    "docs/EXPORT_CONTRACT.md",
    "docs/BACKLOG_STATUS.md",
    "docs/IMPLEMENTATION_STATUS.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "src/credit_atlas/service.py",
    "tests/test_frozen_service.py",
    "scripts/audit_d01_export_contract.py",
    "scripts/record_d01_export_contract.py",
    str(AUDIT.relative_to(ROOT)),
    str(BROWSER.relative_to(ROOT)),
    str(SUITE.relative_to(ROOT)),
]

audit = json.loads(AUDIT.read_text(encoding="utf-8"))
browser = json.loads(BROWSER.read_text(encoding="utf-8"))
suite = json.loads(SUITE.read_text(encoding="utf-8"))
if (audit.get("status") != "PASS" or audit.get("scope_count") != 5
        or audit.get("source_ids_scanned") != 50000 or audit.get("source_id_matches") != 0
        or len(audit.get("unsupported_metric_uses_rejected", [])) != 3):
    raise ValueError("Export contract receipt failed acceptance")
if (browser.get("status") != "PASS" or len(browser.get("checks", [])) != 25
        or not any("private export matches selected run" in check for check in browser["checks"])):
    raise ValueError("Browser report/export regression is not present")
if (suite.get("status") != "PASS" or suite.get("collected_tests") != 1566
        or not suite.get("all_collected_nodes_executed")
        or any(batch.get("status") != "PASS" for batch in suite.get("batches", []))):
    raise ValueError("Full repository suite receipt is not a clean 1,566-test pass")
ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
if ledger.get("count") != 50:
    raise ValueError("Requirement ledger count changed; review before recording")
entries = []
for requirement_id, checkpoint, scope in [
    ("P2.02", "d01-schema2-export-contract-20261015",
     "Descriptive schema-2/schema-1 aggregate export checked on five real-case scopes; exact run/method lineage, supplemental digests, 50,000 source-ID privacy scan, deterministic repeat, unavailable-year behavior, and PD12/ECL/cash-flow override rejection."),
    ("P2.05", "d01-transition-export-consumer-contract-20261015",
     "Supplemental period-transition export preserves selected reporting year and explicit lifetime comparator; current 25-check browser export regression and full 1,566-test repository suite pass."),
]:
    requirement = next(row for row in ledger["requirements"] if row["id"] == requirement_id)
    entry = {"checkpoint": checkpoint, "audit": str(AUDIT.parent.relative_to(ROOT) / "audit.json"),
        "receipt": str(AUDIT.relative_to(ROOT)), "browser": str(BROWSER.relative_to(ROOT)),
        "suite": str(SUITE.relative_to(ROOT)), "scope": scope, "status": "PASS",
        "full_completion_proven": False,
        "evidence_sha256": {rel: sha256(ROOT / rel) for rel in FILES}}
    existing = next((item for item in requirement.setdefault("runtime_regression_evidence", [])
                     if item.get("checkpoint") == checkpoint), None)
    if existing is None:
        requirement["runtime_regression_evidence"].append(entry)
    else:
        existing.clear()
        existing.update(entry)
    entries.append({"requirement": requirement_id,
                    "full_completion_proven": requirement["full_completion_proven"]})
LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"status": "PASS", "requirements": entries, "evidence_files": len(FILES)}, ensure_ascii=False))
