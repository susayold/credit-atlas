"""Record the descriptive 2012 analyst findings without changing project acceptance."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
EVIDENCE = [
    "docs/D01_ANALYST_FINDINGS_VI.md",
    "docs/D01_DATA_AND_METHOD_CARD.md",
    "docs/BACKLOG_STATUS.md",
    "scripts/audit_d01_analyst_findings.py",
    "artifacts/private/d01-analyst-findings-a9579df23a87/audit.json",
    "artifacts/private/d01-analyst-findings-a9579df23a87/receipt.json",
    "artifacts/private/browser-qa-f35adbcaeddf/receipt.json",
]


def record():
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    if ledger.get("count") != 50:
        raise ValueError("Requirement ledger count changed; review before recording")
    requirement = next(row for row in ledger["requirements"] if row["id"] == "P2.03")
    entry = {
        "checkpoint": "d01-analyst-findings-single-vintage-20261015",
        "audit": "artifacts/private/d01-analyst-findings-a9579df23a87/audit.json",
        "receipt": "artifacts/private/d01-analyst-findings-a9579df23a87/receipt.json",
        "browser": "artifacts/private/browser-qa-f35adbcaeddf/receipt.json",
        "scope": "Hash-verified analyst interpretation of D3 stock, competing incidence by Relief and observed loss coverage on the frozen 2012 sample; descriptive only, no model or multi-vintage claims.",
        "status": "PASS",
        "full_completion_proven": False,
        "evidence_sha256": {rel: sha256(ROOT / rel) for rel in EVIDENCE},
    }
    evidence = requirement.setdefault("runtime_regression_evidence", [])
    existing = next((item for item in evidence if item.get("checkpoint") == entry["checkpoint"]), None)
    if existing is None:
        evidence.append(entry)
    else:
        existing.clear()
        existing.update(entry)
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    return {"requirement": "P2.03", "status": "PASS", "full_completion_proven": requirement["full_completion_proven"],
            "evidence_files": len(EVIDENCE)}


if __name__ == "__main__":
    print(json.dumps(record(), ensure_ascii=False))
