import argparse
import json
from credit_atlas.market_data import prepare_market, verify_market
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', required=True)
    args = parser.parse_args()
    result = prepare_market(app_root(), args.suite)
    verify_market(app_root(), result['case_id'])
    print(json.dumps({key: result[key] for key in ('case_id', 'status', 'native_records', 'monthly_records', 'coverage', 'profiles')}, indent=2))
