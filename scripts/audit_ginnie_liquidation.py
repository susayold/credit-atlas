from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.ginnie_liquidation import audit_ginnie_liquidation_zip  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate-only structural audit for a local Ginnie liquidation ZIP."
    )
    parser.add_argument("zip_path", type=Path, help="Private local ZIP stored on D:")
    parser.add_argument(
        "--terms-accepted-by-user",
        action="store_true",
        help="Confirm the user personally accepted current Ginnie loan-level Terms of Use",
    )
    parser.add_argument("--member", help="Select the data member when ZIP contains more than one")
    args = parser.parse_args()
    try:
        result = audit_ginnie_liquidation_zip(
            args.zip_path,
            terms_accepted=args.terms_accepted_by_user,
            member_name=args.member,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
