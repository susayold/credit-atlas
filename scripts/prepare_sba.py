import argparse
import json
from credit_atlas.business_sba import prepare_sba
from credit_atlas.workspace import app_root

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare dictionary-backed SBA record facts and descriptive marts")
    parser.add_argument("--suite", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_sba(app_root(), args.suite), indent=2))
