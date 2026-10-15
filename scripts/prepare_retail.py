import argparse
import json
from credit_atlas.retail import build_retail
from credit_atlas.workspace import app_root

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare private UCI350 behavioral benchmark")
    parser.add_argument("--suite", required=True)
    args = parser.parse_args()
    print(json.dumps(build_retail(app_root(), args.suite), indent=2))
