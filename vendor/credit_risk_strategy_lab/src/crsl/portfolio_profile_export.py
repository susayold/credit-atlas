"""Read the verified portfolio anatomy mart as bounded aggregate evidence."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from .evidence_checks import require, require_hash
from .source import sha256


FIELDS = (
    'segment', 'dimension_order', 'dimension', 'bucket', 'loans',
    'known_upb_loans', 'missing_upb_loans', 'opening_upb', 'segment_loans',
    'segment_known_upb_loans', 'segment_opening_upb', 'count_share',
    'balance_share',
)


def _number(value):
    return None if value is None else float(value)


def load(root: Path, canonical_run: Path, profile_run: Path):
    """Return only allowlisted, denominator-checked profile rows."""
    root, canonical_run, profile_run = (p.resolve() for p in (root, canonical_run, profile_run))
    canonical_receipt = json.loads((canonical_run / 'run-complete.json').read_text())
    receipt = json.loads((profile_run / 'run-complete.json').read_text())
    require(canonical_receipt.get('status') == 'CANONICAL_COMPLETE',
            'Canonical evidence incomplete')
    require(receipt.get('status') == 'PORTFOLIO_PROFILE_COMPLETE',
            'Portfolio profile evidence incomplete')
    require(receipt.get('canonical_run') == canonical_run.name,
            'Portfolio profile uses a different canonical run')
    require(receipt.get('canonical_sha256') == sha256(canonical_run / 'run-complete.json'),
            'Portfolio profile canonical receipt changed')
    path = profile_run / 'profile.parquet'
    require_hash(path, receipt['outputs_sha256']['profile.parquet'])
    with duckdb.connect() as db:
        raw = db.execute('SELECT * FROM read_parquet(?) ORDER BY segment,dimension_order,bucket',
                         [str(path)]).fetchall()
    rows = []
    for item in raw:
        row = dict(zip(FIELDS, item))
        row.update(
            loans=int(row['loans']), known_upb_loans=int(row['known_upb_loans']),
            missing_upb_loans=int(row['missing_upb_loans']),
            segment_loans=int(row['segment_loans']),
            segment_known_upb_loans=int(row['segment_known_upb_loans']),
            opening_upb=_number(row['opening_upb']),
            segment_opening_upb=_number(row['segment_opening_upb']),
            count_share=_number(row['count_share']),
            balance_share=_number(row['balance_share']),
        )
        rows.append(row)
    keys = [(r['segment'], r['dimension'], r['bucket']) for r in rows]
    require(len(keys) == len(set(keys)), 'Duplicate portfolio profile bucket')
    for segment, dimension in sorted({(r['segment'], r['dimension']) for r in rows}):
        cells = [r for r in rows if (r['segment'], r['dimension']) == (segment, dimension)]
        require(sum(r['loans'] for r in cells) == cells[0]['segment_loans'],
                'Portfolio profile count denominator mismatch')
        require(abs(sum(r['count_share'] for r in cells) - 1) <= 1e-10,
                'Portfolio profile count shares do not sum to one')
        require(all(r['known_upb_loans'] + r['missing_upb_loans'] == r['loans'] for r in cells),
                'Portfolio profile balance availability mismatch')
        if cells[0]['segment_opening_upb'] is not None and cells[0]['segment_opening_upb'] > 0:
            require(abs(sum(r['balance_share'] or 0 for r in cells) - 1) <= 1e-10,
                    'Portfolio profile balance shares do not sum to one')
    return {
        'status': 'verified_development', 'visibility': 'private',
        'public_release_approved': False, 'profile_run': profile_run.name,
        'canonical_run': canonical_run.name,
        'run_complete_sha256': sha256(profile_run / 'run-complete.json'),
        'rows': rows,
        'dimensions': sorted({r['dimension'] for r in rows}),
        'segments': sorted({r['segment'] for r in rows}),
        'limitation': 'Count and opening-principal mix of the observed 2012 sample; not a population or customer profile.',
    }
