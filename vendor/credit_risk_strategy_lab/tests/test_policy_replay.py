"""Synthetic file-level replay tests; these fixtures are not research evidence."""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from crsl.policy.replay import run
from crsl.source import sha256


@pytest.fixture
def inputs(tmp_path):
    config_dir = tmp_path / 'configs'
    config_dir.mkdir()
    config_dir.joinpath('policies.json').write_bytes(
        (Path(__file__).resolve().parents[1] / 'configs/policies.json').read_bytes())
    labels, canonical = tmp_path / 'labels-fixture', tmp_path / 'canonical-fixture'
    labels.mkdir()
    canonical.mkdir()
    rows = [dict(loan_id=f'synthetic-{i}', landmark=date(2020, 1, 1),
                 eligibility_reason='eligible' if i < 3 else 'ineligible',
                 original_upb=Decimal('100000.00'), target=i % 2) for i in range(4)]
    pq.write_table(pa.Table.from_pylist(rows), labels / 'labels.parquet')
    pq.write_table(pa.Table.from_pylist([
        dict(loan_id=r['loan_id'], original_upb=r['original_upb'],
             classic_fico=[680, 679, None, 750][i], occupancy='P')
        for i, r in enumerate(rows)]), canonical / 'dim_loan.parquet')
    (labels / 'run-complete.json').write_text(json.dumps(dict(
        status='LABELS_DEVELOPMENT_COMPLETE', canonical_run=canonical.name,
        outputs_sha256={'labels.parquet': sha256(labels / 'labels.parquet')})))
    (canonical / 'run-complete.json').write_text(json.dumps(dict(
        status='CANONICAL_COMPLETE',
        outputs_sha256={'dim_loan.parquet': sha256(canonical / 'dim_loan.parquet')})))
    return tmp_path, labels, canonical


def test_private_replay_preserves_universe_and_missing_score(inputs):
    output = run(*inputs)
    manifest = json.loads((output / 'run-complete.json').read_text())
    assert not manifest['research_ready'] and not manifest['policy_selection_performed']
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['policies'][0]['decision_counts']['selected'] == 3
    assert summary['policies'][1]['decision_counts'] == {
        'selected': 1, 'review': 1, 'data_ineligible': 2}
    identities = []
    for policy in ('S0', 'S1'):
        table = pq.read_table(output / f'{policy}-decisions.parquet')
        assert table.num_rows == 4
        assert 'target' not in table.column_names
        identities.append(table['record_id'].to_pylist())
    assert identities[0] == identities[1]
    for name, digest in manifest['outputs_sha256'].items():
        assert sha256(output / name) == digest


def test_replay_rejects_changed_input(inputs):
    root, labels, canonical = inputs
    (labels / 'labels.parquet').write_bytes(b'changed fixture')
    with pytest.raises(ValueError, match='hash mismatch'):
        run(root, labels, canonical)


def test_replay_rejects_mixed_lineage(inputs):
    root, labels, canonical = inputs
    path = labels / 'run-complete.json'
    manifest = json.loads(path.read_text())
    manifest['canonical_run'] = 'another-run'
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Mixed canonical'):
        run(root, labels, canonical)
