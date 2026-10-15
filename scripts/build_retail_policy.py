import argparse
import json
from pathlib import Path
from credit_atlas.retail_policy import build,verify
from credit_atlas.workspace import app_root,read_json

if __name__=='__main__':
    parser=argparse.ArgumentParser(); choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--assumptions'); choice.add_argument('--verify'); args=parser.parse_args()
    root=app_root(); identifier=args.verify or build(root,read_json(Path(args.assumptions)))['policy_id']
    _,receipt,report=verify(root,identifier)
    print(json.dumps({'policy_id':identifier,'status':receipt['status'],'records':report['records'],'events':report['events'],
        'cases':[{k:r[k] for k in ('id','review_records','review_capacity_exceeded','expected_declared_cost','retrospective_cost_proxy')} for r in report['cases']]},indent=2))
