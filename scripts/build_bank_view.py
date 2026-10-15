import argparse
import json
from credit_atlas.bank_views import BankViews, build_bank_view
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--panel', required=True)
    result = build_bank_view(app_root(), parser.parse_args().panel)
    BankViews(app_root()).view(result['view_id'])
    print(json.dumps(result, indent=2))
