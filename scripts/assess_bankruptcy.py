import argparse
import json
from credit_atlas.bankruptcy_assessment import run_assessment, verify_assessment
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--features', required=True)
    args = parser.parse_args()
    result = run_assessment(app_root(), args.features)
    _, _, metrics = verify_assessment(app_root(), result['assessment_id'])
    print(json.dumps({'assessment_id': result['assessment_id'], 'parity': result['parity'],
                      'validation_metrics': metrics, 'final_test_scored': False}, indent=2))
