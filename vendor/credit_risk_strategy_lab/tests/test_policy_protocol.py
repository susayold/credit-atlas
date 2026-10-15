import json
from pathlib import Path

import pytest

from crsl.policy.protocol import freeze_protocol, load_protocol, compare_locked, retention_locked


def config():
    return dict(version='synthetic-v1', status='development',
        policy_config=json.loads((Path(__file__).resolve().parents[1] / 'configs/policies.json').read_text()),
        candidate_ids=['S0', 'S1'], retention_floors=['.7', '.9'],
        bootstrap=dict(seed=22, resamples=100, confidence='.95', minimum_events=50),
        selection_partition='validation', evaluation_cutoff='2018-01-01',
        split_manifest_sha256='a' * 64, model_manifest_sha256='b' * 64, code_sha256='c' * 64)


def test_exclusive_receipt_and_roundtrip(tmp_path):
    path = tmp_path / 'protocol.json'
    receipt = freeze_protocol(path, config())
    assert load_protocol(path, expected_receipt_sha256=receipt['receipt_sha256']) == config()
    with pytest.raises(FileExistsError):
        freeze_protocol(path, config())


def test_mutation_detected_against_external_pin(tmp_path):
    path = tmp_path / 'protocol.json'
    receipt = freeze_protocol(path, config())
    payload = json.loads(path.read_text())
    payload['config']['bootstrap']['seed'] = 999
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='hash mismatch'):
        load_protocol(path, expected_receipt_sha256=receipt['receipt_sha256'])


@pytest.mark.parametrize('change', [dict(selection_partition='test'), dict(status='approved'),
    dict(candidate_ids=['S0', 'S0']), dict(retention_floors=['.7', '.70']),
    dict(code_sha256='unknown')])
def test_invalid_protocol_rejected_before_write(tmp_path, change):
    path = tmp_path / 'protocol.json'
    with pytest.raises(ValueError):
        freeze_protocol(path, config() | change)
    assert not path.exists()


def test_locked_frontier_refuses_unplanned_floor_or_changed_lineage(tmp_path):
    path = tmp_path / 'protocol.json'
    receipt = freeze_protocol(path, config())
    candidates = [dict(candidate_id=i, cohort_sha256='d' * 64, base_count=1000,
                       base_principal=100000, selected_count=1000, selected_principal=100000,
                       selected_events=100, constraints_passed=True) for i in ('S0', 'S1')]
    kwargs = dict(expected_receipt_sha256=receipt['receipt_sha256'], candidates=candidates,
                  retention_floor='.7', split_manifest_sha256='a' * 64,
                  model_manifest_sha256='b' * 64, code_sha256='c' * 64)
    assert compare_locked(path, **kwargs)['status'] == 'frontier_available'
    with pytest.raises(ValueError, match='predeclared'):
        compare_locked(path, **(kwargs | {'retention_floor': '.8'}))
    with pytest.raises(ValueError, match='lineage'):
        compare_locked(path, **(kwargs | {'model_manifest_sha256': 'e' * 64}))


def retention_config():
    return config() | {'candidate_ids': ['S0', 'S1', 'FR70'], 'retention_candidates': [
        dict(candidate_id='FR70', basis='principal', target='.7', tie_rule='include_whole_boundary_group')]}


def test_retention_uses_frozen_rule_and_keeps_ties(tmp_path):
    path = tmp_path / 'protocol.json'
    receipt = freeze_protocol(path, retention_config())
    result = retention_locked(path, expected_receipt_sha256=receipt['receipt_sha256'],
        candidate_id='FR70', evidence_class='synthetic_demo', records=[
            dict(loan_id='a', principal=60, risk_score='.01'),
            dict(loan_id='b', principal=20, risk_score='.02'),
            dict(loan_id='c', principal=20, risk_score='.02')])
    assert result['selected_count'] == 3
    assert result['target_overshoot_fraction'] == '0.3'
    assert result['protocol_receipt_sha256'] == receipt['receipt_sha256']
    with pytest.raises(ValueError, match='predeclared'):
        retention_locked(path, expected_receipt_sha256=receipt['receipt_sha256'],
                         candidate_id='FR80', evidence_class='synthetic_demo', records=[])


@pytest.mark.parametrize('change', [dict(candidate_id='S0'), dict(target='1.1'),
    dict(basis='balance'), dict(tie_rule='break_by_loan_id')])
def test_unreviewed_retention_rules_rejected(tmp_path, change):
    candidate = retention_config()
    candidate['retention_candidates'][0].update(change)
    with pytest.raises(ValueError):
        freeze_protocol(tmp_path / 'protocol.json', candidate)
