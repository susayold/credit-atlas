import argparse
import json
from credit_atlas.bankruptcy_study import create_study, prepare_features, verify_features
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    parser.add_argument('--horizon', type=int, default=1)
    args = parser.parse_args()
    study = create_study(app_root(), args.case, args.horizon)
    print(json.dumps({key: study[key] for key in ('study_id', 'horizon', 'rows', 'exact_feature_groups', 'support')}, indent=2), flush=True)
    features = prepare_features(app_root(), study['study_id'])
    verify_features(app_root(), features['feature_id'])
    print(json.dumps(features, indent=2))
