"""Build or verify an ordered observation bridge between typed imports."""
import argparse
import json
from credit_atlas.exposure_movements import build, verify
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--opening'); parser.add_argument('--closing'); parser.add_argument('--verify')
    args = parser.parse_args(); root = app_root()
    if args.verify: identifier = args.verify
    else:
        if not args.opening or not args.closing: parser.error('--opening and --closing required')
        identifier = build(root, args.opening, args.closing)['movement_id']
    _, receipt, report = verify(root, identifier)
    print(json.dumps({'movement_id': identifier, 'status': receipt['status'], 'identity_counts': report['identity_counts'], 'currencies': report['currencies']}, indent=2))
