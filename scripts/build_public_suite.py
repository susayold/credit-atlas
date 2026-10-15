import argparse
import json
from credit_atlas.public_suite import build_source_warehouse
from credit_atlas.workspace import app_root

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build verified source-native private Parquet warehouse")
    parser.add_argument("--suite", required=True)
    arguments = parser.parse_args()
    print(json.dumps(build_source_warehouse(app_root(), arguments.suite), indent=2))
