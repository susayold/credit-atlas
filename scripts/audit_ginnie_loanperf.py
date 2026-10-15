from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.ginnie_performance import audit_ginnie_loanperf_zip  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate-only structural audit of a local Ginnie Mae LoanPerf ZIP."
    )
    parser.add_argument("zip_path", type=Path, help="Local LoanPerf ZIP in a private D: directory")
    parser.add_argument(
        "--terms-accepted-by-user",
        action="store_true",
        help="Confirm the user personally accepted the current Ginnie Mae loan-level Terms of Use",
    )
    parser.add_argument("--member", help="Select the data member if the ZIP contains more than one file")
    args = parser.parse_args()
    try:
        result = audit_ginnie_loanperf_zip(
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
