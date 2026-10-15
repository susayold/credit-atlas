"""Export the non-identifying aggregate evidence package for version control."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


FORBIDDEN_KEYS = {'loan_id', 'borrower_id', 'account_id', 'prediction'}
PATH_PATTERN = re.compile(r'[A-Z]:[\\/]|/Users/|/home/')


def assert_safe(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                raise ValueError(f'Forbidden identity key: {key}')
            assert_safe(child)
    elif isinstance(value, list):
        for child in value:
            assert_safe(child)
    elif isinstance(value, str) and PATH_PATTERN.search(value):
        raise ValueError('Private filesystem path in aggregate package')


def write_json(path: Path, payload):
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def write_csv(path: Path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def run(root: Path, snapshot: Path, output: Path):
    payload = json.loads(snapshot.read_text(encoding='utf-8'))
    if payload.get('visibility') != 'private' or payload.get('public_release_approved') is not False:
        raise ValueError('Private, non-public-approved snapshot required')
    assert_safe(payload)
    output.mkdir(parents=True, exist_ok=True)

    write_json(output / 'research-snapshot.json', payload)
    write_csv(output / 'label-outcomes.csv', payload.get('outcomes', []), ['outcome', 'loans'])
    write_csv(output / 'portfolio-monthly.csv', payload.get('monthly', []), [
        'period', 'active_loans', 'state_usable_active_loans', 'd3_active_loans',
        'unknown_active_loans', 'observed_active_upb', 'state_usable_active_upb',
        'd3_active_upb', 'd3_count_share', 'd3_balance_share'])
    write_csv(output / 'state-transitions.csv', payload.get('transitions', []), [
        'origin', 'destination', 'pairs', 'opening_upb', 'missing_balance_pairs',
        'count_probability', 'opening_balance_probability'])
    segmented = payload.get('segmented_transitions') or {}
    write_csv(output / 'segmented-transitions.csv', segmented.get('rows', []), [
        'segment', 'origin', 'destination', 'pairs', 'distinct_loans', 'opening_upb',
        'missing_balance_pairs', 'origin_pairs', 'count_probability',
        'balance_probability', 'sparse_cell'])
    profile = payload.get('portfolio_profile') or {}
    write_csv(output / 'portfolio-profile.csv', profile.get('rows', []), [
        'segment', 'dimension_order', 'dimension', 'bucket', 'loans',
        'known_upb_loans', 'missing_upb_loans', 'opening_upb', 'segment_loans',
        'segment_known_upb_loans', 'segment_opening_upb', 'count_share',
        'balance_share'])
    evidence = payload.get('vintage_evidence') or {}
    write_csv(output / 'vintage-competing-risk.csv', evidence.get('rows', []), [
        'origination_year', 'segment', 'observation_age', 'source_loans', 'eligible_loans',
        'excluded_loans', 'excluded_share', 'at_risk', 'calendar_mature_loans',
        'maturity_complete', 'observed_d3_count', 'observed_prepayment_count',
        'observed_other_exit_count', 'unknown_before_horizon', 'unknown_share',
        'cif_d3', 'cif_prepayment', 'cif_other_exit', 'sparse_d3', 'ci_lower',
        'ci_upper', 'ci_level', 'ci_method', 'ci_status', 'resamples'])
    write_json(output / 'observed-loss-summary.json', payload.get('loss_summary') or {})

    files = sorted(p for p in output.iterdir() if p.is_file() and p.name != 'manifest.json')
    manifest = {
        'package': 'aggregate-only-development-evidence',
        'pipeline_run': payload['pipeline_run'],
        'source_snapshot': str(snapshot.name),
        'visibility': 'private_aggregate',
        'public_release_approved': False,
        'raw_or_loan_level_rows_included': False,
        'files': [{'name': p.name, 'bytes': p.stat().st_size,
                   'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
        'limitations': [
            'One-vintage descriptive evidence only; not model performance.',
            'Null means unavailable, not zero.',
            'Raw Freddie Mac data and loan-level derived artifacts remain local/private.',
        ],
    }
    write_json(output / 'manifest.json', manifest)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=Path('site/dist/data.json'))
    parser.add_argument('--output', type=Path, default=Path('data/aggregate'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    snapshot = args.snapshot if args.snapshot.is_absolute() else root / args.snapshot
    output = args.output if args.output.is_absolute() else root / args.output
    run(root, snapshot.resolve(), output.resolve())
