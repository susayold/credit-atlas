import argparse
import json
from credit_atlas.exposure_ecl import build,verify
from credit_atlas.workspace import app_root

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--assumptions'); parser.add_argument('--verify'); args=parser.parse_args()
    if not args.assumptions and not args.verify: parser.error('--assumptions or --verify required')
    root=app_root(); identifier=args.verify or build(root,args.assumptions)['ecl_id']
    _,receipt,report=verify(root,identifier)
    print(json.dumps({'ecl_id':identifier,'status':receipt['status'],'scope':report['scope'],
        'stages':{k:v['stage'] for k,v in report['stage_assessments'].items()},
        'totals':[r for r in report['probability_weighted_aggregates'] if r['dimension']=='total']},indent=2))
