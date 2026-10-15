import json
import sys
from credit_atlas.abs_views import build_abs_view
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    print(json.dumps(build_abs_view(app_root(), sys.argv[1]), indent=2))
