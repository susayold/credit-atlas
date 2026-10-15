"""Record the Release-47 semantic trace as supplemental P2.02 evidence."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
RECEIPT = ROOT / "artifacts/private/d01-canonical-semantics-e2fe2cdc8cbf/receipt.json"
FILES = [
    "docs/D01_CANONICAL_SEMANTIC_AUDIT_VI.md",
    "docs/BACKLOG_STATUS.md",
    "docs/PLAN_MODULE_01.md",
    "docs/IMPLEMENTATION_STATUS.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "scripts/audit_d01_canonical_semantics.py",
    "scripts/record_d01_canonical_semantics.py",
    "artifacts/private/d01-canonical-semantics-e2fe2cdc8cbf/audit.json",
    "artifacts/private/d01-canonical-semantics-e2fe2cdc8cbf/receipt.json",
]

receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
if (receipt.get("status") != "PASS" or receipt.get("sentinel_fields_checked") != 17
        or receipt.get("enum_fields_checked") != 20
        or receipt.get("mapping_differences") != 0 or receipt.get("harp_flag_differences") != 0
        or any(receipt.get("date_mapping_differences", {}).values())):
    raise ValueError("Semantic audit receipt does not meet its pinned acceptance")
ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
if ledger.get("count") != 50:
    raise ValueError("Requirement ledger count changed; review before recording")
requirement = next(row for row in ledger["requirements"] if row["id"] == "P2.02")
entry = {
    "checkpoint": "d01-release47-canonical-semantic-trace-20261015",
    "audit": str(RECEIPT.parent.relative_to(ROOT) / "audit.json"),
    "receipt": str(RECEIPT.relative_to(ROOT)),
    "scope": "Supplemental raw-to-canonical semantic trace on supplied 2012 corpus: 17 sentinels, 20 enum fields, six month conversions, HARP flags, percentage-point cast parity, and 4,510,559 state/termination mappings; no source-release authentication or cross-vintage claim.",
    "status": "PASS",
    "full_completion_proven": False,
    "evidence_sha256": {rel: sha256(ROOT / rel) for rel in FILES},
}
items = requirement.setdefault("runtime_regression_evidence", [])
existing = next((item for item in items if item.get("checkpoint") == entry["checkpoint"]), None)
if existing is None:
    items.append(entry)
else:
    existing.clear()
    existing.update(entry)
LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"requirement": "P2.02", "status": "PASS",
                  "full_completion_proven": requirement["full_completion_proven"],
                  "evidence_files": len(FILES)}, ensure_ascii=False))
