import argparse
import json
from credit_atlas.retail_features import prepare_features
from credit_atlas.workspace import app_root

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description="Prepare train-only retail development features")
    parser.add_argument("--case",required=True)
    args=parser.parse_args()
    print(json.dumps(prepare_features(app_root(),args.case),indent=2))
