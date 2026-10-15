"""Compare official NSMO questionnaire wording across waves; writes local receipt."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from credit_atlas.nsmo_questionnaires import compare_questionnaire_packages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    acquisition = json.loads(args.acquisition_receipt.read_text(encoding="utf-8"))
    report = compare_questionnaire_packages(acquisition["documents"], Path.cwd())
    report["built_at"] = datetime.now(timezone.utc).isoformat()
    report["acquisition_receipt_sha256"] = __import__("hashlib").sha256(
        args.acquisition_receipt.read_bytes()
    ).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    variants = [row for row in report["question_profiles"] if row["text_variant_count"] > 1]
    print(json.dumps({
        "status": report["status"],
        "source_documents": report["source_document_count"],
        "question_numbers": len(report["question_profiles"]),
        "exact_text_stable_question_numbers": len(report["question_profiles"]) - len(variants),
        "question_numbers_with_text_variants": len(variants),
        "receipt": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
