"""Create a verified private app view for the HMDA 2018 Three-Year release."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.hmda_three_year_2018_views import build_view


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    args = parser.parse_args()
    if args.root.resolve().drive.upper() != "D:":
        parser.error("Private HMDA aggregates must remain on D:")
    try:
        print(json.dumps(build_view(args.root), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
