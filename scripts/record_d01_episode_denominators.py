"""Record descriptive episode-denominator evidence without changing model gates."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
AUDIT = ROOT / "artifacts/private/d01-episode-denominators-a3a3093f04b8/audit.json"
RECEIPT = ROOT / "artifacts/private/d01-episode-denominators-a3a3093f04b8/receipt.json"
BROWSER = ROOT / "artifacts/private/browser-qa-f35adbcaeddf/receipt.json"
FILES = [
    "docs/D01_EPISODE_DENOMINATORS_VI.md",
    "docs/P2_CURE_ACCEPTANCE_VI.md",
    "docs/BACKLOG_STATUS.md",
    "docs/IMPLEMENTATION_STATUS.md",
    "docs/PLAN_MODULE_01.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "scripts/audit_d01_episode_denominators.py",
    "scripts/browser_qa.py",
    "apps/web/app.js",
    str(AUDIT.relative_to(ROOT)),
    str(RECEIPT.relative_to(ROOT)),
    str(BROWSER.relative_to(ROOT)),
    "tests/test_episode_followup.py",
    "tests/test_period_transitions.py",
]


def record():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    browser = json.loads(BROWSER.read_text(encoding="utf-8"))
    if (receipt.get("status") != "PASS" or audit["totals"]["followup_denominator_checks"] != 24
            or not audit["totals"]["all_status_partitions_exact"]):
        raise ValueError("Episode denominator audit is not fully reconciled")
    if browser.get("status") != "PASS" or not any("episode event and unique-loan denominators" in x
                                                     for x in browser.get("checks", [])):
        raise ValueError("Mortgage browser did not verify episode denominator display")
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    if ledger.get("count") != 50:
        raise ValueError("Requirement ledger count changed; review before recording")
    requirement = next(row for row in ledger["requirements"] if row["id"] == "P2.06")
    entry = {
        "checkpoint": "d01-episode-denominators-and-ui-20261015",
        "audit": str(AUDIT.relative_to(ROOT)),
        "receipt": str(RECEIPT.relative_to(ROOT)),
        "browser": str(BROWSER.relative_to(ROOT)),
        "scope": "4,902 event occurrences/1,713 unique loans; repeated event support retained; 24/24 event-type×segment×horizon status partitions exact; browser displays event rows and unique-loan counts separately. No event probability or survival model inferred.",
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
    return {"requirement": "P2.06", "status": "PASS", "full_completion_proven": requirement["full_completion_proven"],
            "followup_partitions": 24, "evidence_files": len(FILES)}


if __name__ == "__main__":
    print(json.dumps(record(), ensure_ascii=False))
