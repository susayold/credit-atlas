import argparse
import json
from credit_atlas.market_views import MarketViews, build_market_view
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    result = build_market_view(app_root(), parser.parse_args().case)
    MarketViews(app_root()).view(result['view_id'])
    print(json.dumps(result, indent=2))
