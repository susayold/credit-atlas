"""Policy UAT uses synthetic loans and hypothetical thresholds, not model findings."""
import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from crsl.policy.engine import ScreeningEngine, demo_records, fingerprint

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'configs/policies.json').read_text())


def screen(rows=None, policy='S1', config=None):
    return ScreeningEngine(CONFIG if config is None else config).screen(
        demo_records() if rows is None else rows, policy, 'synthetic_demo')


def row(**changes):
    return {**demo_records()[0], **changes}


def test_s0_reconciles_eligible_baseline_t23():
    result = screen(policy='S0')
    assert result['summary']['base_eligible_rows'] == 6
    assert result['summary']['decision_counts'] == {'selected': 6, 'review': 0, 'data_ineligible': 2}
    assert Decimal(result['summary']['base_eligible_principal']) == 365000
    assert result['summary']['principal_retention'] == '1'


@pytest.mark.parametrize('fico,expected', [(679,'review'), (680,'selected'), (681,'selected')])
def test_fico_boundary(fico, expected):
    assert screen([row(classic_fico=fico)])['decisions'][0]['decision'] == expected


@pytest.mark.parametrize('pd,expected', [('0.019999','selected'), ('0.02','selected'), ('0.020001','review')])
def test_pd_boundary(pd, expected):
    item = row()
    item['risk']['pd'] = pd
    assert screen([item], 'S2')['decisions'][0]['decision'] == expected


@pytest.mark.parametrize('fico', [None, True, 'NaN', 9999, 299, 851, 680.5])
def test_missing_invalid_critical_score_never_passes_t22(fico):
    decision = screen([row(classic_fico=fico)])['decisions'][0]
    assert decision['decision'] == 'data_ineligible'
    assert decision['reason_codes'] == ['D_FICO_MISSING_OR_INVALID']


def test_s0_does_not_require_fields_its_rule_does_not_use():
    result = screen([row(classic_fico=None, risk=None, occupancy=None)], 'S0')
    assert result['decisions'][0]['decision'] == 'selected'


def test_hard_data_gate_precedes_good_model_score():
    decision = screen([row(data_eligible=False)], 'S2')['decisions'][0]
    assert decision['decision'] == 'data_ineligible'
    assert decision['reason_codes'] == ['D_COHORT_INELIGIBLE']
    assert all(t['stage'] == 'data' for t in decision['trace'])


def test_missing_model_routes_to_review_not_fake_zero_risk():
    result = screen([row(risk=None)], 'S2')
    assert result['decisions'][0]['reason_codes'] == ['R_MODEL_INPUT_UNAVAILABLE']
    assert result['decisions'][0]['decision'] == 'review'


@pytest.mark.parametrize('pd', [None, True, '-0.01', '1.01', 'NaN', 'Infinity'])
def test_invalid_pd_never_selected(pd):
    item = row()
    item['risk']['pd'] = pd
    assert screen([item], 'S2')['decisions'][0]['decision'] == 'data_ineligible'


@pytest.mark.parametrize('field,value,code', [
    ('as_of','2020-02-01','R_RISK_LANDMARK_MISMATCH'),
    ('as_of','2019-12-01','R_RISK_LANDMARK_MISMATCH'),
    ('horizon_months',24,'R_RISK_HORIZON_MISMATCH'),
    ('estimand','credit_loss','R_RISK_ESTIMAND_MISMATCH'),
    ('model_id',None,'R_MODEL_LINEAGE_UNAVAILABLE'),
    ('calibration_id',None,'R_CALIBRATION_UNAVAILABLE'),
    ('model_available_at','2020-01-02','R_MODEL_NOT_AVAILABLE'),
    ('calibration_available_at','2020-01-02','R_CALIBRATION_NOT_AVAILABLE'),
    ('evidence_class','validated_model','R_RISK_EVIDENCE_MISMATCH'),
])
def test_risk_contract_mismatch_routes_to_review(field, value, code):
    item = row()
    item['risk'][field] = value
    decision = screen([item], 'S2')['decisions'][0]
    assert decision['decision'] == 'review' and code in decision['reason_codes']


def test_concentration_failure_is_explicit_not_threshold_relaxation():
    result = screen(policy='S3')
    assert result['summary']['status'] == 'infeasible_concentration'
    assert result['summary']['decision_counts']['selected'] == 0
    assert sum(result['summary']['decision_counts'].values()) == 8
    assert len([d for d in result['decisions'] if d['reason_codes'] == ['R_CONCENTRATION_INFEASIBLE']]) == 3
    assert all(g['maximum_share'] == '0.20' for g in result['summary']['guardrails'])


def test_concentration_uses_principal_and_includes_exact_boundary():
    primary = row(record_id='p', original_upb='80', occupancy='P')
    investor = row(record_id='i', original_upb='20', occupancy='I')
    result = screen([primary, investor], 'S3')
    assert result['summary']['status'] == 'evaluated'
    assert result['summary']['decision_counts']['selected'] == 2
    investor['original_upb'] = '20.01'
    assert screen([primary, investor], 'S3')['summary']['status'] == 'infeasible_concentration'


def test_no_candidate_selected_does_not_divide_by_zero():
    item = row()
    item['risk']['pd'] = '0.9'
    result = screen([item], 'S3')
    assert result['summary']['status'] == 'no_selected_loans'
    assert result['summary']['guardrails'] == []


def test_missing_segment_does_not_pass_s3():
    for value in [None, '9', [], True]:
        result = screen([row(occupancy=value)], 'S3')
        assert result['decisions'][0]['decision'] == 'data_ineligible'


def test_version_and_cutoff_changes_preserve_input_and_outcomes():
    records = demo_records()
    for record in records:
        record['future_target'] = 1
    before = fingerprint(records)
    changed = copy.deepcopy(CONFIG)
    changed['version'] = 'illustrative-v2'
    changed['policies'][1]['minimum_fico'] = 700
    first, second = screen(records), screen(records, config=changed)
    assert fingerprint(records) == before
    assert [d['record_id'] for d in first['decisions']] == [d['record_id'] for d in second['decisions']]
    assert first['summary']['base_eligible_principal'] == second['summary']['base_eligible_principal']
    assert first['summary']['decision_counts']['selected'] == 4
    assert second['summary']['decision_counts']['selected'] == 3
    assert first['summary']['policy_sha256'] != second['summary']['policy_sha256']


def test_future_outcomes_never_drive_screening():
    records = demo_records()
    before = screen(records)
    for record in records:
        record.update(target=1, actual_loss='999999999', label_available=False)
    assert screen(records) == before


def test_reordering_does_not_change_decisions_or_guardrail():
    a, b = screen(policy='S3'), screen(list(reversed(demo_records())), 'S3')
    assert a['summary'] == b['summary']
    assert sorted(a['decisions'], key=lambda d: d['record_id']) == sorted(b['decisions'], key=lambda d: d['record_id'])


def test_duplicate_landmark_and_empty_universe_rejected():
    with pytest.raises(ValueError, match='Duplicate'):
        screen([row(), row()])
    with pytest.raises(ValueError, match='Empty'):
        screen([])


def test_bad_principal_is_auditable_json_without_nan():
    decision = screen([row(original_upb=float('nan'))])['decisions'][0]
    assert decision['decision'] == 'data_ineligible'
    json.dumps(decision, allow_nan=False)
    assert screen([row(original_upb=Decimal('50000'))], 'S0')['decisions'][0]['decision'] == 'selected'


def test_unknown_configuration_not_silently_ignored():
    config = copy.deepcopy(CONFIG)
    config['policies'][1]['ignore_missing'] = True
    with pytest.raises(ValueError, match='Unsupported'):
        ScreeningEngine(config)


def test_config_caller_mutation_does_not_change_engine():
    config = copy.deepcopy(CONFIG)
    engine = ScreeningEngine(config)
    config['policies'][1]['minimum_fico'] = 850
    assert engine.screen([row()], 'S1', 'synthetic_demo')['decisions'][0]['decision'] == 'selected'
