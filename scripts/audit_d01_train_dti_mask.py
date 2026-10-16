from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.dti_mask_audit import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate-only original-DTI sentinel audit over included train rows."
    )
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    parser.add_argument("--study", required=True)
    args = parser.parse_args()
    try:
        result = run(args.root, args.study)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
