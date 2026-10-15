import argparse
import json
from credit_atlas.exposure_convergence import build,verify
from credit_atlas.workspace import app_root

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--assumptions'); parser.add_argument('--verify'); args=parser.parse_args()
    if not args.assumptions and not args.verify: parser.error('--assumptions or --verify required')
    root=app_root(); identifier=args.verify or build(root,args.assumptions)['convergence_id']
    _,receipt,report=verify(root,identifier)
    print(json.dumps({'convergence_id':identifier,'status':receipt['status'],'last_level_changes':[{'case_id':r['case_id'],'currency':r['currency'],'changes':r['last_two_level_changes']} for r in report['diagnostics']]},indent=2))
