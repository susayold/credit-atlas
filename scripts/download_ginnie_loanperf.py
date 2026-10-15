from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.ginnie_acquisition import (  # noqa: E402
    GinnieAcquisitionError,
    download_loanperf_202606,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the official Ginnie Mae LoanPerf 202606 pilot using a local Netscape cookie file."
    )
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    parser.add_argument("--cookie-file", type=Path, required=True,
                        help="Netscape cookie file saved by the user on D:; contents are never printed")
    parser.add_argument("--terms-accepted-by-user", action="store_true",
                        help="Confirm the user personally accepted the current Ginnie Mae loan-level Terms")
    args = parser.parse_args()
    if not args.terms_accepted_by_user:
        parser.error("The user must personally accept the current Ginnie Mae loan-level Terms first")
    try:
        receipt = download_loanperf_202606(args.root, args.cookie_file)
    except (OSError, GinnieAcquisitionError) as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
