import argparse
import json
from credit_atlas.hmda_cohorts import build_cohorts, verify_cohorts
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--case'); mode.add_argument('--verify'); args = parser.parse_args()
    if args.case: receipt = build_cohorts(app_root(), args.case)
    else: _, receipt, _ = verify_cohorts(app_root(), args.verify)
    print(json.dumps({'cohort_id': receipt['cohort_id'], 'status': receipt['status'], 'years': receipt['years']}))
