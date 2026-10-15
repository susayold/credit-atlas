"""Behavioral early-warning baseline and strictly gated logistic challenger."""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

from ..evidence_checks import require

NUMERIC_FEATURES = (
    'current_upb', 'current_upb_missing', 'history_months_available', 'history_has_gap',
    'months_since_last_d3plus', 'consecutive_current_months',
    'trailing_3_d3plus_count', 'trailing_3_unknown_count', 'trailing_3_state_usable_share',
    'trailing_6_d3plus_count', 'trailing_6_unknown_count', 'trailing_6_state_usable_share',
    'trailing_12_d3plus_count', 'trailing_12_unknown_count', 'trailing_12_state_usable_share',
    'upb_change_from_prior_observed',
)
STATES = ('CURRENT', 'UNKNOWN')


def _date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _known_rows(rows):
    result = []
    keys = set()
    for row in rows:
        key = (row.get('loan_id'), row.get('landmark'))
        require(key[0] and key not in keys, 'Behavioral rows need unique loan-landmark keys')
        keys.add(key)
        require(row.get('current_state') in STATES, 'Behavioral endpoint excludes event states')
        target = row.get('target')
        if target is not None:
            require(type(target) is int and target in (0, 1), 'Behavioral target must be binary or unavailable')
            result.append(row)
    return result


def current_state_baseline(rows, *, minimum_support=30):
    """Return an observed risk table, never assigning unavailable targets to 0."""
    require(type(minimum_support) is int and minimum_support > 0, 'Positive minimum support required')
    rows = list(rows)
    known = _known_rows(rows)
    groups = defaultdict(lambda: [0, 0])
    for row in known:
        group = groups[row['current_state']]
        group[0] += 1
        group[1] += row['target']
    output = []
    for state in STATES:
        loans, events = groups[state]
        output.append({'current_state': state, 'loans': loans, 'events': events,
                       'event_rate': events / loans if loans else None,
                       'support_sufficient': loans >= minimum_support,
                       'status': 'available' if loans else 'unavailable'})
    total_loans = sum(r['loans'] for r in output)
    total_events = sum(r['events'] for r in output)
    return {'status': 'descriptive_baseline', 'rows': output, 'loans': total_loans, 'events': total_events,
            'event_rate': total_events / total_loans if total_loans else None,
            'minimum_support': minimum_support, 'unavailable_targets_excluded': len(rows) - total_loans,
            'causal_effect': False, 'research_ready': False}


def _matrix(rows):
    matrix = []
    targets = []
    for row in rows:
        values = []
        for name in NUMERIC_FEATURES:
            value = row.get(name)
            if value is None:
                values.append(0.0)
            else:
                value = float(value)
                require(math.isfinite(value), 'Nonfinite behavioral feature')
                values.append(value)
        state = row['current_state']
        values.extend(float(state == expected) for expected in STATES)
        matrix.append(values)
        targets.append(row['target'])
    return matrix, targets


class BehavioralLogistic:
    """Optional scored challenger; fit requires one landmark per train loan.

    This object is deliberately not wired into the real 2012 pipeline because
    the available source does not provide the required temporal evaluation
    vintages. It is still useful as a tested, reproducible research component.
    """

    def __init__(self, C=1.0):
        require(type(C) in (int, float) and math.isfinite(C) and C > 0, 'Positive finite C required')
        self.C = float(C)
        self.state = None

    def fit(self, rows, *, fit_cutoff, evidence_class='synthetic_demo'):
        cutoff = _date(fit_cutoff)
        known = _known_rows(rows)
        require(known and all(row.get('partition') == 'train' for row in known), 'Behavioral fit uses train rows only')
        require(len({row['loan_id'] for row in known}) == len(known), 'Train landmarks must be one per loan')
        require(all(_date(row['landmark']) < cutoff for row in known), 'Train landmarks must precede fit cutoff')
        require(set(row['target'] for row in known) == {0, 1}, 'Both behavioral classes required')
        require(evidence_class in {'synthetic_demo', 'retrospective_development'}, 'Explicit evidence class required')
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        matrix, targets = _matrix(known)
        estimator = LogisticRegression(C=self.C, solver='lbfgs', max_iter=2000, random_state=0).fit(matrix, targets)
        self.state = {'schema_version': 1, 'C': self.C, 'evidence_class': evidence_class,
                      'training_rows': len(known), 'training_events': sum(targets),
                      'fit_cutoff': cutoff.isoformat(), 'final_test_access': False,
                      'feature_names': list(NUMERIC_FEATURES) + [f'current_state={s}' for s in STATES],
                      'coefficients': estimator.coef_[0].tolist(), 'intercept': float(estimator.intercept_[0])}
        require(all(math.isfinite(float(v)) for v in self.state['coefficients'] + [self.state['intercept']]),
                'Nonfinite behavioral model parameter')
        return self

    def predict(self, rows):
        require(self.state is not None, 'Behavioral model must be fitted')
        rows = list(rows)
        require(all(row.get('partition') in {'train', 'calibration', 'validation'} for row in rows),
                'Behavioral scorer never opens final test')
        import numpy as np
        matrix, _ = _matrix([{**row, 'target': 0 if row.get('target') is None else row['target']} for row in rows])
        probabilities = 1 / (1 + np.exp(-(
            np.asarray(matrix).dot(np.asarray(self.state['coefficients'])) + self.state['intercept'])))
        return [float(min(1.0, max(0.0, value))) for value in probabilities]
