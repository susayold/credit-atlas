import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
folders = sorted((ROOT / "data/private/mortgage").glob("freddie-public-reference-*"),
                 key=lambda folder: folder.stat().st_mtime, reverse=True)
folder = next(folder for folder in folders if (folder / "file-layout-july-2026.xlsx").is_file())
receipt_path = folder / "receipt.json"
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
audit_path = next((ROOT / "artifacts/private").glob("freddie-release47-reference-audit-*/audit.json"))
audit = json.loads(audit_path.read_text(encoding="utf-8"))
assert receipt["status"] == "ACQUIRED" and len(receipt["files"]) == 4
assert receipt["added_annual_vintages"] == 0
for item in receipt["files"]:
    assert sha256(folder / item["file"]) == item["sha256"] and item["http_status"] == 200
assert audit["example_file_profile"]["origination_performance_id_overlap"] == 0
assert audit["qualification"]["annual_vintage_qualified"] is False

ledger_path = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
data = json.loads(ledger_path.read_text(encoding="utf-8"))
before = [(row["id"], row["checkpoint_status"], row["full_completion_proven"])
          for row in data["requirements"]]
requirement = next(row for row in data["requirements"] if row["id"] == "P2.08")
evidence_files = [
    "docs/FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md",
    "docs/IMPLEMENTATION_STATUS.md",
    "docs/PLAN_MODULE_01.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "scripts/acquire_freddie_public_reference.py",
    "scripts/audit_freddie_release47_reference_samples.py",
    "scripts/record_freddie_reference_checkpoint.py",
    str(receipt_path.relative_to(ROOT)),
    str(audit_path.relative_to(ROOT)),
    "artifacts/private/browser-qa-5c6e7e1ec304/receipt.json",
]
entry = {
    "checkpoint": "freddie-release47-public-reference-20261015",
    "document": "docs/FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md",
    "source": str(receipt_path.relative_to(ROOT)),
    "audit": str(audit_path.relative_to(ROOT)),
    "browser": "artifacts/private/browser-qa-5c6e7e1ec304/receipt.json",
    "scope": "Public Release 47 examples/layout downloaded and hash/CRC checked; 31/35 fields match the layout. Example ID populations do not overlap; not joinable or a vintage. D01 browser QA 24 checks PASS.",
    "remaining": "No authorized additional annual loan sample; multi-vintage canonical panel, support/protocol, calibration/validation/OOT and model gate unmet.",
    "added_annual_vintages": 0,
    "full_completion_proven": False,
    "evidence_sha256": {rel: sha256(ROOT / rel) for rel in evidence_files},
}
items = requirement.setdefault("partial_evidence", [])
existing = next((item for item in items if item.get("checkpoint") == entry["checkpoint"]), None)
if existing is None:
    items.append(entry)
else:
    existing.clear()
    existing.update(entry)
assert before == [(row["id"], row["checkpoint_status"], row["full_completion_proven"])
                 for row in data["requirements"]]
ledger_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
print(json.dumps({"status": "CHECKPOINT_RECORDED", "reference_files": 4,
                  "added_annual_vintages": 0, "requirement": "P2.08",
                  "goal_achieved": False}, ensure_ascii=False))
