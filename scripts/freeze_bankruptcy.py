import argparse
import json
from credit_atlas.bankruptcy_freeze import freeze_model
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--comparison', required=True)
    args = parser.parse_args()
    print(json.dumps(freeze_model(app_root(), args.comparison), indent=2))
