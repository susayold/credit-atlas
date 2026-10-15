"""Record transition denominator interpretation and current browser regression."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
AUDIT_RECEIPT = ROOT / "artifacts/private/transition-acceptance-be68432843fc/receipt.json"
BROWSER = ROOT / "artifacts/private/browser-qa-f35adbcaeddf/receipt.json"
FILES = [
    "docs/D01_TRANSITION_DENOMINATORS_VI.md",
    "docs/P2_TRANSITION_ACCEPTANCE_VI.md",
    "docs/BACKLOG_STATUS.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "scripts/audit_transition_acceptance.py",
    "src/credit_atlas/period_transitions.py",
    "apps/web/app.js",
    "scripts/browser_qa.py",
    str(AUDIT_RECEIPT.relative_to(ROOT)),
    str(BROWSER.relative_to(ROOT)),
]


def record():
    audit = json.loads(AUDIT_RECEIPT.read_text(encoding="utf-8"))
    browser = json.loads(BROWSER.read_text(encoding="utf-8"))
    if (audit.get("status") != "PASS" or audit.get("adjacent_pairs") != 4460559
            or audit.get("year_cells") != 1091 or audit.get("lifetime_cells") != 94
            or audit.get("export_scopes_checked") != 68):
        raise ValueError("Independent transition audit no longer matches expected scope")
    if browser.get("status") != "PASS" or not any("transition basis and cell support" in x
                                                     for x in browser.get("checks", [])):
        raise ValueError("Latest browser receipt does not include transition cell acceptance")
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    if ledger.get("count") != 50:
        raise ValueError("Requirement ledger count changed; review before recording")
    requirement = next(row for row in ledger["requirements"] if row["id"] == "P2.05")
    entry = {
        "checkpoint": "d01-transition-denominator-interpretation-20261015",
        "audit": str(AUDIT_RECEIPT.relative_to(ROOT)),
        "browser": str(BROWSER.relative_to(ROOT)),
        "scope": "Adjacent-pair count/opening-UPB denominators and lifetime/year scopes documented for the one-vintage descriptive matrix; current browser cell support regressed. Pair-weighted share is not called PD.",
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
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    return {"requirement": "P2.05", "status": "PASS", "full_completion_proven": requirement["full_completion_proven"],
            "evidence_files": len(FILES)}


if __name__ == "__main__":
    print(json.dumps(record(), ensure_ascii=False))
