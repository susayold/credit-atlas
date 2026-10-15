import argparse
import json
from credit_atlas.bankruptcy_model_views import BankruptcyModelViews, build_model_view
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluation', required=True)
    args = parser.parse_args()
    receipt = build_model_view(app_root(), args.evaluation)
    BankruptcyModelViews(app_root()).view(receipt['view_id'])
    print(json.dumps(receipt, indent=2))
