"""Prepare and verify a reported ABS source case; no model fit or projection."""
import json
import sys
from credit_atlas.abs_servicer import prepare
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    r=prepare(app_root(),sys.argv[1])
    print(json.dumps({'case_id':r['case_id'],'periods':len(r['periods']),
        'files':r['files'],'checks':len(r['checks']),'failed_checks':r['failed_checks']}))
