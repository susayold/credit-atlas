import json
import sys
from credit_atlas.abs_waterfall import build_replay
from credit_atlas.workspace import app_root

if __name__=='__main__':
    r=build_replay(app_root(),sys.argv[1])
    print(json.dumps({k:r[k] for k in ('waterfall_id','status','failed_checks')}))
    print('Periods:',len(r['periods']),'Checks:',len(r['checks']))
