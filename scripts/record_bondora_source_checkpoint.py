from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
DOC = ROOT / "docs/BONDORA_PUBLIC_DATASET_RESEARCH_VI.md"
RECEIPT = ROOT / "artifacts/private/bondora-public-dataset-profile/receipt.json"
PROFILE = ROOT / "artifacts/private/bondora-public-dataset-profile/profile.json"
SOURCE = ROOT / "data/private/retail/bondora-source/loan_dataset_investor.xlsx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


doc = json.loads(LEDGER.read_text(encoding="utf-8"))
before = {row["id"]: (row["checkpoint_status"], row["full_completion_proven"]) for row in doc["requirements"]}
row = next(row for row in doc["requirements"] if row["id"] == "P1.02")
if row["full_completion_proven"] or row["checkpoint_status"] != "Cần dữ liệu":
    raise SystemExit("P1.02 is not in the expected open state; no ledger update made")
for path in (DOC, RECEIPT, PROFILE, SOURCE):
    if not path.is_file():
        raise SystemExit(f"Required evidence missing: {path}")
receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
profile = json.loads(PROFILE.read_text(encoding="utf-8"))
if receipt["status"] != "PROFILED" or profile["source"]["sha256"] != sha256(SOURCE):
    raise SystemExit("Profile receipt/source hash mismatch; no ledger update made")

checkpoint = "bondora-public-loan-dataset-profile-20261015"
items = row.setdefault("partial_evidence", [])
entry = next((item for item in items if item.get("checkpoint") == checkpoint), None)
if entry is None:
    entry = {
        "checkpoint": checkpoint,
        "document": "docs/BONDORA_PUBLIC_DATASET_RESEARCH_VI.md",
        "audit": "artifacts/private/bondora-public-dataset-profile/receipt.json",
        "profile": "artifacts/private/bondora-public-dataset-profile/profile.json",
        "source": "data/private/retail/bondora-source/loan_dataset_investor.xlsx",
        "scope": "Official public investor loan workbook; 789144 loan rows/31 columns; source/dictionary/null/date/12-MOB-label profile; private row-level source; no model fit or individual IDs emitted",
        "remaining": "Application/decision timestamps, requested terms, bureau, reject population, confirmed feature availability, snapshot/censoring specification and intended-use/OOT remain absent; does not satisfy P1.02",
        "full_completion_proven": False,
        "evidence_sha256": {
            "docs/BONDORA_PUBLIC_DATASET_RESEARCH_VI.md": sha256(DOC),
            "artifacts/private/bondora-public-dataset-profile/receipt.json": sha256(RECEIPT),
            "artifacts/private/bondora-public-dataset-profile/profile.json": sha256(PROFILE),
            "data/private/retail/bondora-source/loan_dataset_investor.xlsx": sha256(SOURCE),
        },
    }
    items.append(entry)
else:
    entry["evidence_sha256"] = {
        "docs/BONDORA_PUBLIC_DATASET_RESEARCH_VI.md": sha256(DOC),
        "artifacts/private/bondora-public-dataset-profile/receipt.json": sha256(RECEIPT),
        "artifacts/private/bondora-public-dataset-profile/profile.json": sha256(PROFILE),
        "data/private/retail/bondora-source/loan_dataset_investor.xlsx": sha256(SOURCE),
    }
doc["as_of"] = "2026-10-15"
after = {item["id"]: (item["checkpoint_status"], item["full_completion_proven"]) for item in doc["requirements"]}
if before != after:
    raise SystemExit("Requirement acceptance states changed unexpectedly; no ledger update made")
LEDGER.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "RECORDED_PARTIAL_ONLY", "requirement": "P1.02", "accepted_count": sum(item["full_completion_proven"] for item in doc["requirements"]), "total": len(doc["requirements"]), "as_of": doc["as_of"]}, ensure_ascii=False))
