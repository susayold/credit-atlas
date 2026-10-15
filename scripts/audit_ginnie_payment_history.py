from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.ginnie_payment_history import (  # noqa: E402
    audit_ginnie_payment_history,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate-only audit for a local Ginnie Mae payment-history file."
    )
    parser.add_argument("file_path", type=Path, help="Private local source text file stored on D:")
    parser.add_argument(
        "--terms-accepted-by-user",
        action="store_true",
        help="Confirm the user personally accepted current Ginnie loan-level Terms of Use",
    )
    args = parser.parse_args()
    try:
        result = audit_ginnie_payment_history(
            args.file_path,
            terms_accepted=args.terms_accepted_by_user,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
