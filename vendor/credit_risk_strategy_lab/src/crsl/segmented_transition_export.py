"""Read a verified aggregate transition mart without exporting loan IDs."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from .evidence_checks import require, require_hash
from .source import sha256


FIELDS = (
    'segment', 'origin', 'destination', 'pairs', 'distinct_loans', 'opening_upb',
    'missing_balance_pairs', 'origin_pairs', 'count_probability',
    'balance_probability', 'sparse_cell',
)


def load(root: Path, segmented_run: Path):
    """Return only allowlisted aggregate fields from a completed segment mart."""
    root, segmented_run = root.resolve(), segmented_run.resolve()
    receipt = json.loads((segmented_run / 'run-complete.json').read_text())
    require(receipt.get('status') == 'SEGMENTED_TRANSITIONS_COMPLETE',
            'Segmented transition evidence incomplete')
    path = segmented_run / 'transitions.parquet'
    require_hash(path, receipt['outputs_sha256']['transitions.parquet'])
    with duckdb.connect() as db:
        rows = db.execute('''SELECT segment,origin,destination,pairs,distinct_loans,
            opening_upb,missing_balance_pairs,origin_pairs,count_probability,
            balance_probability,sparse_cell
            FROM read_parquet(?) ORDER BY segment,origin,destination''', [str(path)]).fetchall()
    projected = []
    for row in rows:
        projected.append(dict(zip(FIELDS, row)))
    keys = [(r['segment'], r['origin'], r['destination']) for r in projected]
    require(len(keys) == len(set(keys)), 'Duplicate segmented transition cell')
    groups = {(r['segment'], r['origin']) for r in projected}
    for segment, origin in groups:
        cells = [r for r in projected if (r['segment'], r['origin']) == (segment, origin)]
        require(abs(sum(r['count_probability'] for r in cells) - 1) <= 1e-10,
                'Segmented count probabilities do not sum to one')
    return {
        'status': 'verified_development', 'visibility': 'private',
        'public_release_approved': False, 'segmented_run': segmented_run.name,
        'canonical_run': receipt['canonical_run'], 'run_complete_sha256': sha256(segmented_run / 'run-complete.json'),
        'adjacent_pairs': receipt['adjacent_pairs'], 'rows': projected,
        'limitation': 'Repeated loan-month pairs are dependent; no causal segment effect is claimed.',
    }
