import json
import sys
from credit_atlas.abs_contract import build
from credit_atlas.workspace import app_root

if __name__=='__main__':
    r=build(app_root(),sys.argv[1])
    print(json.dumps({k:r[k] for k in ('terms_id','status','failed_checks','unsupported_interest_periods')}))
    print('Checks:',len(r['checks']))
