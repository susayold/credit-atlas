import argparse
import json
from credit_atlas.sec_views import SecViews, build_sec_view
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--case', required=True)
    args = parser.parse_args()
    receipt = build_sec_view(app_root(), args.case)
    SecViews(app_root()).view(receipt['view_id'])
    print(json.dumps(receipt, indent=2))
