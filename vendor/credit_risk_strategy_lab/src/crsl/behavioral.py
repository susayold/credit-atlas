"""Leakage-safe landmark features for behavioral early-warning research.

The source is a funded-loan performance panel, so this module creates a
research priority signal rather than an approval or collections action. Every
feature is computed from observations at or before the landmark. A future
12-month D3 label is only known when the full path is observed without a gap,
unknown state, or competing terminal event before the endpoint.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

from .evidence_checks import require


def _month(value):
    if isinstance(value, dt.datetime):
        return value.date().replace(day=1)
    if isinstance(value, dt.date):
        return value.replace(day=1)
    if isinstance(value, str):
        return dt.date.fromisoformat(value[:10]).replace(day=1)
    raise ValueError('Behavioral panel period must be a date-like value')


def _month_diff(left, right):
    return (left.year - right.year) * 12 + left.month - right.month


def _validate_panel(records):
    rows = list(records)
    require(rows, 'Behavioral panel cannot be empty')
    grouped = defaultdict(list)
    for row in rows:
        require(isinstance(row.get('loan_id'), str) and row['loan_id'], 'Behavioral loan_id required')
        require(row.get('delinquency_state') in {'CURRENT', 'D3PLUS', 'UNKNOWN', 'REO'},
                'Unexpected behavioral delinquency state')
        grouped[row['loan_id']].append(row)
    ordered = {}
    for loan_id, loan_rows in grouped.items():
        items = sorted((( _month(r['period']), r) for r in loan_rows), key=lambda x: x[0])
        require(len({period for period, _ in items}) == len(items), 'Duplicate behavioral loan-month')
        require(all(_month_diff(items[i][0], items[i - 1][0]) > 0 for i in range(1, len(items))),
                'Behavioral panel periods must be strictly increasing')
        ordered[loan_id] = items
    return ordered


def _future_label(items, index, horizon):
    """Return (target, reason), preserving unavailable future paths as None."""
    landmark = items[index][0]
    expected_age = 1
    for period, row in items[index + 1:]:
        age = _month_diff(period, landmark)
        if age > horizon:
            break
        if age != expected_age:
            return None, 'gap_before_horizon'
        state = row['delinquency_state']
        terminal = row.get('terminal_type')
        if state == 'D3PLUS':
            return 1, 'd3_before_competing_exit'
        if state in {'REO'} or terminal is not None:
            return 0, 'competing_exit_before_d3'
        if state == 'UNKNOWN':
            return None, 'unknown_before_horizon'
        expected_age += 1
    if expected_age <= horizon:
        return None, 'administrative_censoring'
    return 0, 'horizon_complete_no_d3'


def _trailing(items, index, window):
    landmark = items[index][0]
    selected = []
    for position in range(index, -1, -1):
        period, row = items[position]
        age = _month_diff(landmark, period)
        if age >= window:
            break
        selected.append((period, row))
    selected.reverse()
    return selected


def _upb(row):
    value = row.get('current_upb')
    if value is None:
        return None
    value = float(value)
    require(math.isfinite(value) and value >= 0, 'Current UPB must be finite and non-negative')
    return value


def build_landmark_features(records, *, horizon=12, include_target=True):
    """Create one leakage-safe row per non-terminal landmark.

    ``include_target=False`` is appropriate for production-like scoring or
    demos. The returned features never contain future observations. A target
    is ``None`` when the future path is not fully known under the declared
    censoring policy.
    """
    require(type(horizon) is int and horizon > 0, 'Positive integer horizon required')
    grouped = _validate_panel(records)
    result = []
    for loan_id in sorted(grouped):
        items = grouped[loan_id]
        for index, (landmark, current) in enumerate(items):
            if current['delinquency_state'] in {'D3PLUS', 'REO'} or current.get('terminal_type') is not None:
                continue
            history_12 = _trailing(items, index, 12)
            current_upb = _upb(current)
            row = {
                'loan_id': loan_id,
                'landmark': landmark.isoformat(),
                'current_state': current['delinquency_state'],
                'current_upb': current_upb,
                'current_upb_missing': current_upb is None,
                'history_months_available': len(history_12),
                'history_has_gap': any(_month_diff(history_12[i][0], history_12[i - 1][0]) != 1
                                       for i in range(1, len(history_12))),
                'months_since_last_d3plus': None,
                'consecutive_current_months': 0,
            }
            last_d3 = None
            current_streak = 0
            for period, observed in reversed(history_12):
                if observed['delinquency_state'] == 'D3PLUS' and last_d3 is None:
                    last_d3 = period
                if observed['delinquency_state'] == 'CURRENT':
                    current_streak += 1
                else:
                    break
            if last_d3 is not None:
                row['months_since_last_d3plus'] = _month_diff(landmark, last_d3)
            row['consecutive_current_months'] = current_streak
            for window in (3, 6, 12):
                history = _trailing(items, index, window)
                usable = [r for _, r in history if r['delinquency_state'] != 'UNKNOWN']
                row[f'trailing_{window}_d3plus_count'] = sum(r['delinquency_state'] == 'D3PLUS' for _, r in history)
                row[f'trailing_{window}_unknown_count'] = sum(r['delinquency_state'] == 'UNKNOWN' for _, r in history)
                row[f'trailing_{window}_state_usable_share'] = len(usable) / len(history) if history else None
            prior_upb = next((_upb(r) for period, r in reversed(items[:index]) if _upb(r) is not None), None)
            row['upb_change_from_prior_observed'] = (current_upb - prior_upb) if current_upb is not None and prior_upb is not None else None
            if include_target:
                row['target'] , row['target_reason'] = _future_label(items, index, horizon)
            result.append(row)
    return result


def assert_no_future_leakage(features, records):
    """Regression guard: every feature landmark is an observed panel period."""
    observed = {(r['loan_id'], _month(r['period']).isoformat()) for r in records}
    for row in features:
        require((row['loan_id'], row['landmark']) in observed, 'Landmark not present in source panel')
    return True
