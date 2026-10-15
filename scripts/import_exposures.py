import argparse
import json
from credit_atlas.exposure_imports import import_exposures, verify_import
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--csv'); parser.add_argument('--metadata'); parser.add_argument('--verify')
    args = parser.parse_args()
    if args.verify:
        _, receipt, report = verify_import(app_root(), args.verify)
    elif args.csv and args.metadata:
        receipt = import_exposures(app_root(), args.csv, args.metadata)
        _, _, report = verify_import(app_root(), receipt['import_id'])
    else: parser.error('Use --csv/--metadata or --verify')
    print(json.dumps({'import_id': receipt['import_id'], 'status': receipt['status'], 'records': report['records'], 'currencies': report['currencies']}, indent=2))
