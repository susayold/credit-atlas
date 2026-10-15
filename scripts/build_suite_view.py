import argparse
import json
from credit_atlas.suite_snapshot import build_suite_view
from credit_atlas.workspace import app_root

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build verified aggregate suite/retail app projection")
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--holdout", required=True)
    parser.add_argument("--business", help="Optional verified SBA business case")
    args = parser.parse_args()
    print(json.dumps(build_suite_view(app_root(), args.warehouse, args.freeze, args.holdout, args.business), indent=2))
