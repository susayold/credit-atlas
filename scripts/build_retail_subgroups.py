import argparse
import json
from pathlib import Path
from credit_atlas.retail_subgroups import build,verify
from credit_atlas.workspace import app_root,read_json

if __name__=='__main__':
    parser=argparse.ArgumentParser();choice=parser.add_mutually_exclusive_group(required=True);choice.add_argument('--assumptions');choice.add_argument('--verify');args=parser.parse_args()
    root=app_root();identifier=args.verify or build(root,read_json(Path(args.assumptions)))['subgroups_id']
    _,receipt,report=verify(root,identifier)
    print(json.dumps({'subgroups_id':identifier,'status':receipt['status'],'overall':report['overall'],'coverage':report['coverage']},indent=2))
