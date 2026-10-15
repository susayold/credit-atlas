import argparse
import json
from credit_atlas.retail_cohort_explanations import build, verify
from credit_atlas.workspace import app_root, read_json

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--assumptions'); group.add_argument('--verify'); args=parser.parse_args(); root=app_root()
    if args.verify:
        _,_,report,_=verify(root,args.verify)
        result={'status':'PASS','cohort_id':args.verify,'records':report['records']}
    else:
        result=build(root,read_json(root/args.assumptions))
        _,_,report,_=verify(root,result['cohort_id']); result['status']='PASS'
    result['global_group_contributions']=report['global_group_contributions']
    print(json.dumps(result,indent=2))
