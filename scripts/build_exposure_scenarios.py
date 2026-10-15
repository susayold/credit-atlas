import argparse
import json
from credit_atlas.exposure_scenarios import build,verify
from credit_atlas.workspace import app_root

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--assumptions'); parser.add_argument('--verify'); args=parser.parse_args()
    if not args.verify and not args.assumptions: parser.error('--assumptions or --verify required')
    root=app_root(); identifier=args.verify or build(root,args.assumptions)['scenario_id']
    _,receipt,report=verify(root,identifier)
    print(json.dumps({'scenario_id':identifier,'status':receipt['status'],'scope':report['scope'],
        'scenarios':[{'id':s['id'],'totals':[r for r in s['aggregates'] if r['dimension']=='total']} for s in report['scenarios']]},indent=2))
