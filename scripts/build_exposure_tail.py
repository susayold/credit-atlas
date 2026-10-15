import argparse
import json
from credit_atlas.exposure_tail import build,verify
from credit_atlas.workspace import app_root

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--assumptions'); parser.add_argument('--verify'); args=parser.parse_args()
    if not args.assumptions and not args.verify: parser.error('--assumptions or --verify required')
    root=app_root(); identifier=args.verify or build(root,args.assumptions)['tail_id']; _,receipt,report=verify(root,identifier)
    print(json.dumps({'tail_id':identifier,'status':receipt['status'],'results':[{'case_id':r['id'],'currency':r['currency'],
        'mean_loss':r['mean_loss'],'analytic_expected_loss':r['analytic_expected_loss'],'tails':r['tails']} for r in report['results']]},indent=2))
