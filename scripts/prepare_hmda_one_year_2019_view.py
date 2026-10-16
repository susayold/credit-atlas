"""Build a private, aggregate-only view for verified HMDA 2019 One-Year data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.hmda_one_year_2019_views import build_national_view


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    parser.add_argument("--source-id", required=True, help="Verified hmda-national-one-year-2019-<12 hex> source id")
    args = parser.parse_args()
    if args.root.resolve().drive.upper() != "D:":
        parser.error("Private national HMDA aggregates must remain on D:")
    try:
        print(json.dumps(build_national_view(args.root, args.source_id), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

