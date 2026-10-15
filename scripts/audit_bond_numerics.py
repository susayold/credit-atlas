"""Saved independent annuity-price and sensitivity checks on 180 assumed bonds."""
import itertools
import json
import math
import uuid
from pathlib import Path

from credit_atlas.bond_scenario import bond_scenario
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def run(root):
    output = root / 'artifacts/private' / ('bond-numerics-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    results = []
    for frequency, years, coupon, yield_ in itertools.product((1, 2, 4), (1, 5, 10, 30), (0, 3, 5), (-1, 0, 2, 5, 8)):
        terms = {'face_usd': 100, 'frequency': frequency, 'years': years,
                 'coupon_percent': coupon, 'yield_percent': yield_}
        scenario = bond_scenario(terms)
        count, r, cash = frequency * years, yield_ / 100 / frequency, coupon / frequency
        # Closed-form annuity + bullet, independent of the engine's per-flow sum.
        expected = 100 + cash * count if r == 0 else cash * (1 - (1 + r)**(-count)) / r + 100 * (1 + r)**(-count)
        price_error = abs(scenario['price_usd'] - expected) / expected
        duration_error = scenario['bump_validation']['duration_abs_residual'] / scenario['modified_duration_years']
        convexity_error = scenario['bump_validation']['convexity_abs_residual'] / scenario['convexity_years_squared']
        principal_error = abs(math.fsum(row['principal_usd'] for row in scenario['schedule']) - 100)
        coupon_error = abs(math.fsum(row['coupon_usd'] for row in scenario['schedule']) - coupon * years)
        shock_prices = [row['price_usd'] for row in scenario['yield_shocks']]
        monotonic = all(left > right for left, right in zip(shock_prices, shock_prices[1:]))
        results.append({'terms': terms, 'relative_price_error': price_error,
            'relative_duration_bump_error': duration_error, 'relative_convexity_bump_error': convexity_error,
            'principal_cash_residual_usd': principal_error, 'coupon_cash_residual_usd': coupon_error,
            'yield_shocks_strictly_monotonic': monotonic,
            'passed': price_error < 1e-12 and duration_error < 2e-5 and convexity_error < 2e-5
                and principal_error < 1e-12 and coupon_error < 1e-12 and monotonic})
    summary = {'audit_id': output.name, 'status': 'PASS' if all(row['passed'] for row in results) else 'FAIL',
        'completed_at': timestamp(), 'instruments': len(results),
        'max_relative_price_error': max(row['relative_price_error'] for row in results),
        'max_relative_duration_bump_error': max(row['relative_duration_bump_error'] for row in results),
        'max_relative_convexity_bump_error': max(row['relative_convexity_bump_error'] for row in results),
        'convention': 'regular periodic fixed coupons, coupon-date settlement, flat nominal annual yield',
        'market_calibration_performed': False, 'observed_security_prices_used': False,
        'engine_sha256': sha256(root / 'src/credit_atlas/bond_scenario.py'),
        'audit_script_sha256': sha256(Path(__file__)), 'visibility': 'private',
        'public_release_approved': False, 'results': results}
    write_new(output / 'receipt.json', summary)
    if summary['status'] != 'PASS':
        raise ValueError('Bond numerical acceptance failed; inspect retained receipt')
    return {key: value for key, value in summary.items() if key != 'results'}


if __name__ == '__main__':
    print(json.dumps(run(app_root()), indent=2))
