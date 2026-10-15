import argparse
import json
from credit_atlas.sec_financials import prepare_sec_case, verify_case
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--source', required=True)
    args = parser.parse_args()
    receipt = prepare_sec_case(app_root(), args.source)
    verify_case(app_root(), receipt['case_id'])
    print(json.dumps(receipt, indent=2))
