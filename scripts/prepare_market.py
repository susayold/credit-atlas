import argparse
import json
from pathlib import Path
from credit_atlas.market_data import prepare_market, verify_market
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=app_root(), help='Private D: data workspace; defaults to this checkout')
    parser.add_argument('--suite', required=True)
    parser.add_argument('--treasury-run', help='Use receipt-bound Treasury direct par yields from 1990 plus FRED pre-1990 extension')
    args = parser.parse_args()
    result = prepare_market(args.workspace, args.suite, args.treasury_run)
    verify_market(args.workspace, result['case_id'])
    print(json.dumps({key: result[key] for key in ('case_id', 'status', 'native_records', 'monthly_records', 'coverage', 'profiles')}, indent=2))
