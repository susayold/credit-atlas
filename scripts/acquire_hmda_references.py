import argparse
import json
from credit_atlas.hmda_references import acquire_references, verify_references
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source')
    mode.add_argument('--verify')
    parser.add_argument('--lenders-only', action='store_true', help='Acquire only filer references; county labels remain explicitly unacquired')
    args = parser.parse_args()
    if args.verify:
        _, receipt, payload = verify_references(app_root(), args.verify)
    else:
        receipt, payload = acquire_references(app_root(), args.source, 'lender_only' if args.lenders_only else 'lender_and_county')
    print(json.dumps({'reference_id': receipt['reference_id'], 'status': receipt['status'],
        'files': len(receipt['files']), 'bytes': sum(item['bytes'] for item in receipt['files']),
        'coverage': payload['coverage']}, indent=2))
