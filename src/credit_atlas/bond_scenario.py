"""Periodic fixed-coupon educational bond cash flows and analytical sensitivities.

Settlement exactly on a coupon date: regular equal periods, zero accrued
interest, bullet principal, nominal annual yield compounded at coupon frequency.
No call/default/prepay/floating/indexed terms or source quote calibration.
"""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation


def _number(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError('Invalid ' + name)
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Invalid ' + name) from error
    if not result.is_finite() or not lower <= result <= upper:
        raise ValueError('Unsupported ' + name + ' range')
    return result


def terms_from(value):
    if not isinstance(value, dict) or set(value) != {'face_usd', 'coupon_percent', 'yield_percent', 'years', 'frequency'}:
        raise ValueError('Exactly five supported bond terms required')
    face = _number(value['face_usd'], 'face_usd', Decimal('.01'), Decimal('1e12'))
    coupon = _number(value['coupon_percent'], 'coupon_percent', Decimal(0), Decimal(100))
    yield_ = _number(value['yield_percent'], 'yield_percent', Decimal(-20), Decimal(100))
    years = _number(value['years'], 'years', Decimal('.25'), Decimal(60))
    frequency = _number(value['frequency'], 'frequency', Decimal(1), Decimal(4))
    if frequency not in (1, 2, 4):
        raise ValueError('Frequency must be 1, 2 or 4')
    periods = years * frequency
    if periods != periods.to_integral_value():
        raise ValueError('Whole regular coupon periods required')
    return {'face_usd': str(face), 'coupon_percent': str(coupon), 'yield_percent': str(yield_),
            'years': str(years), 'frequency': int(frequency), 'periods': int(periods)}


def _price_derivatives(cashflows, frequency, annual_yield):
    base = 1 + annual_yield / frequency
    if base <= 0:
        raise ValueError('Yield-compounding denominator must be positive')
    prices, first, second = [], [], []
    for k, amount in enumerate(cashflows, 1):
        prices.append(amount * base**(-k))
        first.append(-k / frequency * amount * base**(-k - 1))
        second.append(k * (k + 1) / frequency**2 * amount * base**(-k - 2))
    return math.fsum(prices), math.fsum(first), math.fsum(second)


def bond_scenario(value):
    terms = terms_from(value)
    face, coupon, yield_ = (float(Decimal(terms[key])) for key in ('face_usd', 'coupon_percent', 'yield_percent'))
    frequency, periods = terms['frequency'], terms['periods']
    coupon_cash = face * coupon / 100 / frequency
    cashflows = [coupon_cash] * periods
    cashflows[-1] += face
    annual_yield = yield_ / 100
    price, first, second = _price_derivatives(cashflows, frequency, annual_yield)
    if not (price > 0 and all(math.isfinite(v) for v in (price, first, second))):
        raise ValueError('Nonfinite bond valuation')
    duration = -first / price
    bump = 1e-4
    down = _price_derivatives(cashflows, frequency, annual_yield - bump)[0]
    up = _price_derivatives(cashflows, frequency, annual_yield + bump)[0]
    fd_duration = (down - up) / (2 * bump * price)
    fd_convexity = (down + up - 2 * price) / (bump**2 * price)
    schedule = [{'period': k, 'time_years': k / frequency, 'coupon_usd': coupon_cash,
                 'principal_usd': face if k == periods else 0,
                 'cash_usd': amount, 'discount_factor': (1 + annual_yield / frequency)**(-k),
                 'present_value_usd': amount * (1 + annual_yield / frequency)**(-k)}
                for k, amount in enumerate(cashflows, 1)]
    shocks = []
    for bps in (-100, -50, -1, 0, 1, 50, 100):
        shifted = _price_derivatives(cashflows, frequency, annual_yield + bps * 1e-4)[0]
        shocks.append({'yield_shock_bps': bps, 'shifted_yield_percent': yield_ + bps / 100,
            'price_usd': shifted, 'price_change_usd': shifted - price,
            'duration_convexity_change_usd': price * (-duration * bps * 1e-4 + .5 * second / price * (bps * 1e-4)**2)})
    return {'mode': 'assumption_only_periodic_bond', 'terms': terms,
        'conventions': {'currency': 'USD', 'settlement': 'coupon_date_zero_accrued_interest',
            'timing': 'regular_equal_periods_first_cash_at_1_over_frequency_years',
            'coupon': 'fixed_nominal_annual_rate', 'principal': 'bullet_at_maturity',
            'yield': 'assumed_flat_nominal_annual_yield_compounded_at_coupon_frequency'},
        'market_calibrated': False, 'security_quote_used': False,
        'price_usd': price, 'price_per_100_face': price / face * 100,
        'modified_duration_years': duration,
        'macaulay_duration_years': duration * (1 + annual_yield / frequency),
        'convexity_years_squared': second / price, 'dv01_usd': -first * 1e-4,
        'bump_validation': {'annual_yield_bump_decimal': bump,
            'finite_difference_duration': fd_duration, 'finite_difference_convexity': fd_convexity,
            'duration_abs_residual': abs(duration - fd_duration),
            'convexity_abs_residual': abs(second / price - fd_convexity)},
        'schedule': schedule, 'yield_shocks': shocks,
        'limitations': ['Educational assumed instrument; no observed security quotes or deal cash flows.',
            'No settlement date/day-count/stub/accrued-interest calculation beyond coupon-date convention.',
            'No credit default/recovery, embedded options, floating coupons or market-calibrated OAS.',
            'Duration/convexity shock approximation differs from exact repricing for large shocks.']}
