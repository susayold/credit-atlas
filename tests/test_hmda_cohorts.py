import copy
import json
from fractions import Fraction

import pytest

from credit_atlas import hmda_cohorts as cohorts
from credit_atlas.hmda_applications import DIMENSIONS, build_case
from credit_atlas.hmda_sources import acquire_hmda_source
from credit_atlas.workspace import read_json, sha256
from tests.test_hmda_sources import fake_network
from tests import test_hmda_sources as fixtures


def cell(year, loan_type, denominator, denied, action=None):
    categories = dict(zip(cohorts.FIELDS, [loan_type, '1', '1', '1', '2', '2']))
    if action: return [{'year': year, 'categories': categories, 'action_code': action, 'records': denominator, 'public_amount_usd': str(denominator * 5000)}]
    return [{'year': year, 'categories': categories, 'action_code': code, 'records': count,
             'public_amount_usd': str(count * 5000)} for code, count in [('1', denominator - denied), ('3', denied)] if count]


def fraction(value):
    return None if value is None else Fraction(int(value['numerator']), int(value['denominator']))


def test_composition_reversal_uses_decided_reference_weights_not_target_mix():
    rows = cell(2023, '1', 90, 9) + cell(2023, '2', 10, 8)
    for year in (2024, 2025): rows += cell(year, '1', 20, 1) + cell(year, '2', 180, 126)
    result = cohorts.compare(rows, [2023, 2024, 2025])
    first, last = result['years'][0], result['years'][-1]
    assert fraction(first['native_rate']) == Fraction(17, 100)
    assert fraction(last['native_rate']) == Fraction(127, 200)
    assert fraction(last['full_reference_standardized_rate']) == Fraction(23, 200)
    assert fraction(last['common_support_standardized_rate']) == Fraction(23, 200)
    assert result['common_support_cells'] == 2


def test_missing_reference_cell_is_unavailable_no_weight_renormalization():
    rows = cell(2023, '1', 1, 0) + cell(2023, '2', 1, 1)
    for year in (2024, 2025): rows += cell(year, '1', 2, 1) + cell(year, '2', 10, 0, action='6')
    result = cohorts.compare(rows, [2023, 2024, 2025]); last = result['years'][-1]
    assert last['full_reference_standardized_rate'] is None and last['full_reference_status'] == 'INCOMPLETE_SUPPORT'
    assert fraction(last['reference_weight_coverage']) == Fraction(1, 2)
    assert fraction(last['common_support_standardized_rate']) == Fraction(1, 2)
    assert result['common_reference_denominator'] == 1
    assert last['native_decision_denominator'] == 2
    assert last['missing_reference_cells'][0]['loan_type'] == '2'


def test_no_reference_decisions_and_target_new_cell_remain_explicit():
    rows = cell(2023, '1', 9, 0, action='6') + cell(2024, '2', 1, 1) + cell(2025, '2', 1, 0)
    result = cohorts.compare(rows, [2023, 2024, 2025])
    assert all(row['full_reference_standardized_rate'] is None for row in result['years'])
    assert all(row['full_reference_status'] == 'NO_REFERENCE_DENOMINATOR' for row in result['years'])
    assert result['years'][0]['native_rate'] is None
    assert result['years'][1]['non_reference_decision_denominator'] == 1


def test_unknown_exempt_and_multifamily_not_coerced_to_owner_1_4_closed_end():
    rows = []
    for year in (2023, 2024, 2025):
        known = cell(year, '1', 1, 0)[0]; rows.append(known)
        exempt = copy.deepcopy(known); exempt['categories']['reverse_mortgage'] = '1111'; rows.append(exempt)
        multifamily = copy.deepcopy(known); multifamily['categories']['total_units'] = '5-24'; rows.append(multifamily)
        investment = copy.deepcopy(known); investment['categories']['occupancy_type'] = '3'; rows.append(investment)
    report = cohorts.project(rows, [2023, 2024, 2025])
    assert [row['years'][0]['records'] for row in report['cohorts']] == [4, 2, 1]
    strict = report['cohorts'][2]
    assert sum(step['years'][0]['excluded']['records'] for step in strict['attrition']) == 3
    assert strict['attrition'][3]['years'][0]['excluded']['records'] == 1
    assert any(row['value'] == '5-24' for row in report['profiles'])


@pytest.fixture
def built(tmp_path, fake_network, monkeypatch):
    fields = set(fixtures.header()) | set(DIMENSIONS) | set(cohorts.FIELDS)
    actual = sorted(name for name in fields if not name.startswith('extra_'))
    actual += ['extra_' + str(i) for i in range(99 - len(actual))]
    monkeypatch.setattr(fixtures, 'header', lambda: actual)
    original = fixtures.records
    def records(year):
        rows = original(year)
        for row in rows: row.update(dict(zip(cohorts.FIELDS, ['1', '1', '1', '1', '2', '2'])))
        rows[1]['reverse_mortgage'] = '1111'
        return rows
    monkeypatch.setattr(fixtures, 'records', records)
    src = acquire_hmda_source(tmp_path); case = build_case(tmp_path, src['source_id'])
    receipt = cohorts.build_cohorts(tmp_path, case['case_id'])
    return tmp_path, receipt


def test_build_and_rederive_exact_marts_attrition_and_rates(built):
    root, receipt = built; _, _, report = cohorts.verify_cohorts(root, receipt['cohort_id'])
    assert len(report['cohorts']) == 3
    assert report['cohorts'][0]['years'][0]['public_amount_sum_usd'] == '20000.00'
    assert report['cohorts'][2]['years'][0]['public_amount_sum_usd'] == '5000.00'
    assert report['cohorts'][2]['years'][0]['descriptive_denial_rate'] == '0'


@pytest.mark.parametrize('change', ['mart', 'rate', 'false_zero'])
def test_forged_outputs_with_updated_digest_rejected(built, change):
    root, receipt = built; folder = root / 'artifacts/private' / receipt['cohort_id']
    name = 'joint-mart.json' if change == 'mart' else 'coverage.json'; payload = read_json(folder / name)
    if change == 'mart': payload[0]['records'] += 1
    elif change == 'rate': payload['cohorts'][0]['comparison']['years'][0]['full_reference_standardized_rate']['decimal'] = '0.999'
    else: payload['contract']['default_pd'] = 0
    (folder / name).write_text(json.dumps(payload), encoding='utf-8')
    receipt['outputs_sha256'][name] = sha256(folder / name)
    (folder / 'cohort-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError, match='raw source projection'): cohorts.verify_cohorts(root, receipt['cohort_id'])
