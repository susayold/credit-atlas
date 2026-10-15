import argparse
import json
from credit_atlas.bankruptcy_comparison import run_comparison, verify_comparison
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assessment', required=True)
    args = parser.parse_args()
    result = run_comparison(app_root(), args.assessment)
    _, _, summary = verify_comparison(app_root(), result['comparison_id'])
    print(json.dumps({'comparison_id': result['comparison_id'], 'valid_replicates': summary['valid_replicates'],
        'validation_rows': summary['validation_rows'], 'validation_groups': summary['validation_groups'],
        'paired_boosting_minus_logistic': summary['paired_deltas']['boosting_platt_minus_logistic_platt']}, indent=2))
