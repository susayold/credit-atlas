import json
from credit_atlas.country_observatory import acquire_country_source
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    print(json.dumps(acquire_country_source(app_root()), indent=2))
