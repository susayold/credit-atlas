import pytest
from crsl.policy.optimize import validation_frontier


def candidate(name='S0', count=1000, principal=100000, events=100):
    return dict(candidate_id=name, cohort_sha256='a' * 64, base_count=1000,
                base_principal=100000, selected_count=count,
                selected_principal=principal, selected_events=events, constraints_passed=True)


def evaluate(rows, **kwargs):
    return validation_frontier(rows, partition='validation', minimum_principal_retention='0.7',
                               candidate_ids=[r['candidate_id'] for r in rows], **kwargs)


def test_tradeoff_frontier_and_dominated_candidate():
    result = evaluate([candidate(), candidate('A', 800, 80000, 50), candidate('B', 750, 75000, 60)])
    assert {r['candidate_id'] for r in result['candidates'] if r['pareto']} == {'S0', 'A'}
    assert not result['champion_selected']


def test_equal_candidates_both_remain():
    assert all(r['pareto'] for r in evaluate([candidate(), candidate('equal')])['candidates'])


@pytest.mark.parametrize('partition', ['train', 'calibration', 'test', 'final_oot'])
def test_never_select_on_test(partition):
    with pytest.raises(ValueError, match='validation'):
        validation_frontier([candidate()], partition=partition,
                            minimum_principal_retention='.7', candidate_ids=['S0'])


def test_failures_remain_visible_without_relaxing_floor():
    rows = [candidate('low', 600, 60000, 55), candidate('rare', 900, 90000, 3),
            candidate('empty', 0, 0, 0), {**candidate('concentrated'), 'constraints_passed': False}]
    result = evaluate(rows)
    assert result['status'] == 'infeasible_or_unsupported'
    assert len(result['candidates']) == 4
    assert not any(r['pareto'] for r in result['candidates'])


def test_reject_different_cohort():
    with pytest.raises(ValueError, match='share cohort'):
        evaluate([candidate(), {**candidate('A'), 'cohort_sha256': 'b' * 64}])


def test_reject_changed_menu():
    with pytest.raises(ValueError, match='menu changed'):
        validation_frontier([candidate()], partition='validation',
                            minimum_principal_retention='.7', candidate_ids=['A'])


def test_principal_and_count_objectives_are_distinct():
    result = evaluate([candidate('A', 800, 90000, 80), candidate('B', 900, 80000, 90)])
    assert all(r['pareto'] for r in result['candidates'])
