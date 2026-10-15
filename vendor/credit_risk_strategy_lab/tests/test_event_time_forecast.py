import pytest

from crsl.forecast import naive_last_state, project_state_mass
from crsl.models.event_time import binary_vs_competing, validate_curve


def test_competing_risk_mass_and_monotonicity():
    rows = [
        {'origination_year': 2012, 'segment': 'all', 'observation_age': 6, 'maturity_complete': True, 'ci_status': 'available', 'cif_d3': .01, 'cif_prepayment': .20, 'cif_other_exit': .02},
        {'origination_year': 2012, 'segment': 'all', 'observation_age': 12, 'maturity_complete': True, 'ci_status': 'available', 'cif_d3': .02, 'cif_prepayment': .30, 'cif_other_exit': .03},
    ]
    assert validate_curve(rows)['status'] == 'PASS'
    comparison = binary_vs_competing(at_risk=100, binary_d3_events=5, d3_cif=.02, prepayment_cif=.3, other_exit_cif=.03)
    assert comparison['survival_or_censoring_mass'] == pytest.approx(.65)


def test_transition_scenario_preserves_mass_and_naive_is_explicit():
    transitions = [
        {'origin': 'CURRENT', 'destination': 'CURRENT', 'count_probability': .9},
        {'origin': 'CURRENT', 'destination': 'D3', 'count_probability': .1},
        {'origin': 'D3', 'destination': 'CURRENT', 'count_probability': .2},
        {'origin': 'D3', 'destination': 'D3', 'count_probability': .8},
    ]
    result = project_state_mass({'CURRENT': 100, 'D3': 0}, transitions, states=('CURRENT', 'D3'), horizons=(1, 3))
    assert all(row['total_mass'] == pytest.approx(100) for row in result['horizons'])
    assert naive_last_state({'CURRENT': 100, 'D3': 0})['backtested'] is False
