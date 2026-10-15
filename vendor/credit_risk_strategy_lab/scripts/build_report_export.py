"""Freeze a canonical private aggregate report contract from the website snapshot."""
import argparse
import json
from pathlib import Path

from crsl.reporting.export import dumps
from crsl.source import sha256, utc_now, write_json_new


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=Path('site/dist/data.json'))
    parser.add_argument('--output', type=Path, default=None,
                        help='Optional output path outside the repository artifact directory.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    snapshot_path = (root / args.snapshot).resolve() if not args.snapshot.is_absolute() else args.snapshot.resolve()
    payload = json.loads(snapshot_path.read_text(encoding='utf-8'))
    serialized = dumps(payload)
    output = (root / 'artifacts/private' / f"{payload['pipeline_run']}-report-data.json"
              if args.output is None else args.output.resolve())
    write_json_new(output, json.loads(serialized))
    receipt = output.with_name(output.stem + '-receipt.json')
    write_json_new(receipt, {'status': 'REPORT_EXPORT_COMPLETE', 'visibility': 'private',
        'public_release_approved': False, 'pipeline_run': payload['pipeline_run'],
        'snapshot_sha256': sha256(snapshot_path), 'report_sha256': sha256(output), 'created_at': utc_now()})
    print(output)
