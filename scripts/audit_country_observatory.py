import argparse
import json
from credit_atlas.country_audit import run_audit
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    print(json.dumps(run_audit(app_root(), args.case), indent=2))
