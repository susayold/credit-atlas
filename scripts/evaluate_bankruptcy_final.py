import argparse
import json
from credit_atlas.bankruptcy_holdout import evaluate_holdout, verify_holdout
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--freeze', help='One-time scoring; repeated access is rejected')
    group.add_argument('--evaluation', help='Verify/read saved evidence; no final predictor scoring')
    args = parser.parse_args()
    identifier = evaluate_holdout(app_root(), args.freeze)['evaluation_id'] if args.freeze else args.evaluation
    _, receipt, metrics, uncertainty = verify_holdout(app_root(), identifier)
    print(json.dumps({'evaluation_id': identifier, 'candidate': receipt['candidate'],
        'final_metrics': {key: value for key, value in metrics.items() if key != 'reliability_bins'},
        'uncertainty': uncertainty, 'model_training_performed': False}, indent=2))
