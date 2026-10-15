import argparse
import json
from credit_atlas.retail_explanations import build, verify
from credit_atlas.workspace import app_root, read_json

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--assumptions')
    group.add_argument('--verify')
    args = parser.parse_args()
    root = app_root()
    if args.verify:
        _, receipt, report = verify(root, args.verify)
        result = {'status': 'PASS', 'explanations_id': receipt['explanations_id'],
                  'records': report['records'], 'global_permutation': report['global_permutation']}
    else:
        result = build(root, read_json(root / args.assumptions))
        _, _, report = verify(root, result['explanations_id'])
        result.update(status='PASS', global_permutation=report['global_permutation'])
    print(json.dumps(result, indent=2))
