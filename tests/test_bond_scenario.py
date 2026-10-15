import math

import pytest

from credit_atlas.bond_scenario import bond_scenario


def terms(**overrides):
    return {'face_usd': 100, 'coupon_percent': 5, 'yield_percent': 5,
            'years': 10, 'frequency': 2, **overrides}


def test_coupon_equals_yield_prices_at_par_and_cashflow_reconciles():
    result = bond_scenario(terms())
    assert result['price_usd'] == pytest.approx(100, abs=1e-12)
    assert sum(row['principal_usd'] for row in result['schedule']) == 100
    assert sum(row['coupon_usd'] for row in result['schedule']) == 50
    assert math.fsum(row['present_value_usd'] for row in result['schedule']) == result['price_usd']
    assert result['market_calibrated'] is False and result['security_quote_used'] is False


def test_zero_coupon_closed_form_duration_and_convexity():
    result = bond_scenario(terms(coupon_percent=0, years=5, yield_percent=4, frequency=2))
    assert result['price_usd'] == pytest.approx(100 / 1.02**10)
    assert result['macaulay_duration_years'] == pytest.approx(5)
    assert result['modified_duration_years'] == pytest.approx(5 / 1.02)
    assert result['convexity_years_squared'] == pytest.approx(10 * 11 / 4 / 1.02**2)


def test_independent_annuity_price_and_finite_difference_sensitivities():
    result = bond_scenario(terms(coupon_percent=3, yield_percent=7))
    per_period, periods, coupon = .07 / 2, 20, 1.5
    expected = coupon * (1 - (1 + per_period)**(-periods)) / per_period + 100 * (1 + per_period)**(-periods)
    assert result['price_usd'] == pytest.approx(expected, abs=1e-12)
    assert result['bump_validation']['duration_abs_residual'] < 2e-6
    assert result['bump_validation']['convexity_abs_residual'] < 2e-5
    assert result['dv01_usd'] == pytest.approx(result['price_usd'] * result['modified_duration_years'] * 1e-4)
    assert result['yield_shocks'][0]['price_usd'] > result['price_usd'] > result['yield_shocks'][-1]['price_usd']


def test_zero_and_negative_yields_remain_valid():
    zero = bond_scenario(terms(yield_percent=0))
    assert zero['price_usd'] == 150
    negative = bond_scenario(terms(yield_percent=-1))
    assert negative['price_usd'] > zero['price_usd']


@pytest.mark.parametrize('changes', [{'face_usd': 0}, {'coupon_percent': -1}, {'yield_percent': 'NaN'},
    {'frequency': 3}, {'years': .75, 'frequency': 2}, {'yield_percent': -30},
    {'yield_percent': True}, {'years': 61}, {'callable': True}])
def test_unsupported_terms_fail_instead_of_silent_approximation(changes):
    with pytest.raises(ValueError):
        bond_scenario(terms(**changes))
