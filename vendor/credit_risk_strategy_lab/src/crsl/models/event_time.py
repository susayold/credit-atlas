"""Validation helpers for descriptive competing-event evidence."""
from __future__ import annotations

import math
from collections import defaultdict

from ..evidence_checks import require

EVENTS = ('d3', 'prepayment', 'other_exit')


def validate_curve(rows):
    """Validate cumulative-incidence rows without filling immature cells."""
    rows = list(rows)
    require(rows, 'Competing-risk curve cannot be empty')
    previous = {}
    for row in rows:
        key = (row.get('origination_year'), row.get('segment'))
        horizon = row.get('observation_age')
        require(type(horizon) is int and horizon > 0, 'Positive horizon required')
        for event in EVENTS:
            value = row.get('cif_' + event)
            if value is None:
                require(row.get('maturity_complete') is False or row.get('ci_status') != 'available',
                        'Mature curve cannot hide a missing incidence')
            else:
                require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1,
                        'Cumulative incidence must be in [0,1]')
                require(sum(row.get('cif_' + other) or 0 for other in EVENTS) <= 1 + 1e-12,
                        'Competing incidence exceeds probability mass')
        total = sum(row.get('cif_' + event) or 0 for event in EVENTS)
        require(total <= 1 + 1e-12, 'Competing-event probability mass exceeded')
        for event in EVENTS:
            value = row.get('cif_' + event)
            if value is not None and key in previous and previous[key][event] is not None:
                require(value + 1e-12 >= previous[key][event], 'Cumulative incidence must be non-decreasing')
        previous[key] = {event: row.get('cif_' + event) for event in EVENTS}
    return {'status': 'PASS', 'rows': len(rows), 'segments': len(previous), 'events': list(EVENTS)}


def binary_vs_competing(*, at_risk, binary_d3_events, d3_cif, prepayment_cif, other_exit_cif):
    """Show how a binary denominator differs from a competing-risk estimand."""
    require(type(at_risk) is int and at_risk > 0, 'Positive at-risk count required')
    require(type(binary_d3_events) is int and 0 <= binary_d3_events <= at_risk, 'Binary event count invalid')
    values = [d3_cif, prepayment_cif, other_exit_cif]
    require(all(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1 for value in values),
            'Incidence values invalid')
    require(sum(values) <= 1 + 1e-12, 'Competing incidence mass invalid')
    return {'binary_d3_rate': binary_d3_events / at_risk, 'd3_cif': d3_cif,
            'competing_exit_cif': prepayment_cif + other_exit_cif,
            'survival_or_censoring_mass': 1 - sum(values),
            'estimands_differ': abs(binary_d3_events / at_risk - d3_cif) > 1e-12,
            'interpretation': 'Binary rate conditions on the declared endpoint denominator; CIF retains competing exits.'}
