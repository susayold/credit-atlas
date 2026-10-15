"""Record Toyota 2024-B partial evidence without changing requirement acceptance."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
EVIDENCE = [
    "docs/TOYOTA_2024B_VALIDATION_RESEARCH_VI.md",
    "docs/ABS_APP_WORKFLOW.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "data/private/structured/toyota-2024b-validation-panel-5286fb3cae94/acquisition-complete.json",
    "data/private/derived/toyota-2024b-validation-panel-35e5183b1c22/dataset-complete.json",
    "artifacts/private/toyota-2024b-absee-panel-audit-148e4a9f9a76/audit.json",
    "artifacts/private/toyota-2024b-absee-panel-audit-148e4a9f9a76/receipt.json",
    "artifacts/private/toyota-2024b-certificate-tieout-6223784d25dd/audit.json",
    "artifacts/private/toyota-2024b-certificate-tieout-6223784d25dd/receipt.json",
    "artifacts/private/toyota-2024b-validation-ui-qa-39ae2625c9ec/receipt.json",
    "scripts/build_toyota_2024b_validation_panel.py",
    "scripts/audit_toyota_2024b_absee_panel.py",
    "scripts/audit_toyota_2024b_certificate_tieout.py",
    "scripts/browser_toyota_2024b_validation_qa.py",
    "src/credit_atlas/absee_profile.py",
    "apps/web/app.js",
]


def record():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    if ledger.get("count") != 50:
        raise ValueError("Requirement ledger count changed; review before recording checkpoint")
    hashes = {rel: sha256(ROOT / rel) for rel in EVIDENCE}
    checkpoint = {
        "checkpoint": "toyota-2024b-same-issuer-deal-validation-20261015",
        "as_of": "2026-10-15",
        "document": "docs/TOYOTA_2024B_VALIDATION_RESEARCH_VI.md",
        "source": "data/private/structured/toyota-2024b-validation-panel-5286fb3cae94/acquisition-complete.json",
        "panel": "data/private/derived/toyota-2024b-validation-panel-35e5183b1c22/dataset-complete.json",
        "panel_audit": "artifacts/private/toyota-2024b-absee-panel-audit-148e4a9f9a76/audit.json",
        "certificate_tieout": "artifacts/private/toyota-2024b-certificate-tieout-6223784d25dd/audit.json",
        "browser": "artifacts/private/toyota-2024b-validation-ui-qa-39ae2625c9ec/receipt.json",
        "scope": "29 paired Toyota 2024-B SEC months; 1,518,106 asset row-months/70,254 keys; pool, positive contract count, liquidation event count/gross principal exact 29/29 and delinquency count/balance 232/232. Recovery ties 1/29 with signed aggregate +$1,764,558.08 asset-minus-certificate delta. Same Toyota issuer/servicer family as 2022-B; no independent issuer validation, PD/LGD qualification or forecast.",
        "full_completion_proven": False,
        "evidence_sha256": hashes,
    }
    for requirement_id in ("P5.02", "P5.10"):
        requirement = next((x for x in ledger["requirements"] if x.get("id") == requirement_id), None)
        if requirement is None:
            raise ValueError(f"Requirement missing: {requirement_id}")
        evidence = requirement.setdefault("partial_evidence", [])
        existing = next((x for x in evidence if x.get("checkpoint") == checkpoint["checkpoint"]), None)
        if existing is None:
            evidence.append(checkpoint.copy())
        else:
            existing.clear()
            existing.update(checkpoint)
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"updated": ["P5.02", "P5.10"], "count": ledger["count"],
                      "full_completion_proven": False, "evidence_files": len(hashes)}, ensure_ascii=False))


if __name__ == "__main__":
    record()
