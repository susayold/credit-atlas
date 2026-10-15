"""Record Nissan 2024-B partial evidence without changing requirement acceptance."""
import json
from pathlib import Path

from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
EVIDENCE = [
    "docs/NISSAN_2024B_EXTERNAL_VALIDATION_VI.md",
    "docs/ABS_APP_WORKFLOW.md",
    "docs/PROGRESS_UPDATE_2026-10-15_VI.md",
    "data/private/structured/nissan-2024b-validation-panel-7cd3605b4e07/acquisition-complete.json",
    "data/private/derived/nissan-2024b-validation-panel-9534e22c34fc/dataset-complete.json",
    "artifacts/private/nissan-2024b-absee-panel-audit-8b5590abd3d5/audit.json",
    "artifacts/private/nissan-2024b-absee-panel-audit-8b5590abd3d5/receipt.json",
    "artifacts/private/nissan-2024b-certificate-tieout-d7a71f85c77c/audit.json",
    "artifacts/private/nissan-2024b-certificate-tieout-d7a71f85c77c/receipt.json",
    "artifacts/private/nissan-2024b-event-exceptions-90406964d980/audit.json",
    "artifacts/private/nissan-2024b-event-exceptions-90406964d980/receipt.json",
    "artifacts/private/nissan-2024b-submission-refresh-a26fc17a6676/audit.json",
    "artifacts/private/nissan-2024b-submission-refresh-a26fc17a6676/receipt.json",
    "artifacts/private/nissan-2024b-recovery-dpd-exceptions-71362b31b1c1/audit.json",
    "artifacts/private/nissan-2024b-recovery-dpd-exceptions-71362b31b1c1/receipt.json",
    "artifacts/private/nissan-2024b-dpd-boundary-audit-762c0a8bcdf2/audit.json",
    "artifacts/private/nissan-2024b-dpd-boundary-audit-762c0a8bcdf2/receipt.json",
    "artifacts/private/nissan-2024b-external-ui-qa-cbcdea438399/receipt.json",
    "scripts/acquire_nissan_2024b_validation_panel.py",
    "scripts/build_nissan_2024b_validation_panel.py",
    "scripts/audit_nissan_2024b_absee_panel.py",
    "scripts/audit_nissan_2024b_certificate_tieout.py",
    "scripts/audit_nissan_2024b_event_exception_detail.py",
    "scripts/audit_nissan_2024b_submission_history.py",
    "scripts/audit_nissan_2024b_recovery_dpd_exceptions.py",
    "scripts/audit_nissan_2024b_dpd_boundary_rules.py",
    "scripts/browser_nissan_2024b_external_qa.py",
    "src/credit_atlas/absee_profile.py",
    "apps/web/app.js",
    "tests/test_absee_profile.py",
]


def record():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    if ledger.get("count") != 50:
        raise ValueError("Requirement ledger count changed; review before recording checkpoint")
    hashes = {rel: sha256(ROOT / rel) for rel in EVIDENCE}
    checkpoint = {
        "checkpoint": "nissan-2024b-external-issuer-transfer-20261015",
        "as_of": "2026-10-15",
        "document": "docs/NISSAN_2024B_EXTERNAL_VALIDATION_VI.md",
        "source": "data/private/structured/nissan-2024b-validation-panel-7cd3605b4e07/acquisition-complete.json",
        "panel": "data/private/derived/nissan-2024b-validation-panel-9534e22c34fc/dataset-complete.json",
        "panel_audit": "artifacts/private/nissan-2024b-absee-panel-audit-8b5590abd3d5/audit.json",
        "certificate_tieout": "artifacts/private/nissan-2024b-certificate-tieout-d7a71f85c77c/audit.json",
        "event_exception_audit": "artifacts/private/nissan-2024b-event-exceptions-90406964d980/audit.json",
        "submission_history_audit": "artifacts/private/nissan-2024b-submission-refresh-a26fc17a6676/audit.json",
        "recovery_dpd_audit": "artifacts/private/nissan-2024b-recovery-dpd-exceptions-71362b31b1c1/audit.json",
        "dpd_boundary_audit": "artifacts/private/nissan-2024b-dpd-boundary-audit-762c0a8bcdf2/audit.json",
        "browser": "artifacts/private/nissan-2024b-external-ui-qa-cbcdea438399/receipt.json",
        "scope": "23 paired SEC ABS-EE/10-D periods, 1,154,259 row-months/63,688 keys/63 fields. Pool/count exact 23/23; positive charge-off count 20/23; first-code-4 count 21/23; gross principal 21/23; first-code-4 amount 20/23; DPD count/balance 178/184; recovery exact 17/23 with signed delta +$8,859.23. Live SEC submissions census refreshed through 2026-09-25, byte-identical to acquisition and no July 2025 ABS-EE/A or 10-D/A. June DPD boundary candidate matches local residual 8/8 but worsens 23-period exact checks from 178/184 to 86/184, so original mapping is retained. Six recovery amount mismatches (Dec 2024-May 2025) total +$8,859.23; all positive recovery rows belong to assets with code 4 in a prior month, with no same-row positive charge-off, negative recovery, or other cash-collection fields; amount scope remains unresolved. Jul 2025 event exception remains unresolved. Certificate monthly net loss and cumulative net-loss identities exact 23/23; no PD/LGD/model validation is claimed.",
        "full_completion_proven": False,
        "evidence_sha256": hashes,
    }
    for requirement_id in ("P5.02", "P5.10"):
        requirement = next((x for x in ledger["requirements"] if x.get("id") == requirement_id), None)
        if requirement is None:
            raise ValueError(f"Requirement missing: {requirement_id}")
        evidence = requirement.setdefault("partial_evidence", [])
        existing = next((item for item in evidence if item.get("checkpoint") == checkpoint["checkpoint"]), None)
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
