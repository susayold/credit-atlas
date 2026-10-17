import argparse
import json
from pathlib import Path
from credit_atlas.market_views import MarketViews, build_market_view
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=app_root(), help='Private D: data workspace; defaults to this checkout')
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    result = build_market_view(args.workspace, args.case)
    MarketViews(args.workspace).view(result['view_id'])
    print(json.dumps(result, indent=2))
