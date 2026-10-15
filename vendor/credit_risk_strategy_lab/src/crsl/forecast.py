"""Scenario-only state-mass projection from an observed transition matrix.

This is a deterministic engineering primitive. It is not a qualified
portfolio forecast until rolling origins, mature targets and naive backtests
exist across additional annual vintages.
"""
from __future__ import annotations

import math

from .evidence_checks import require


def _matrix(states, transitions):
    states = tuple(states)
    require(states and len(set(states)) == len(states), 'Unique forecast states required')
    positions = {state: index for index, state in enumerate(states)}
    matrix = [[0.0 for _ in states] for _ in states]
    for row in transitions:
        origin, destination = row['origin'], row['destination']
        require(origin in positions and destination in positions, 'Transition state missing from state universe')
        value = float(row['count_probability'])
        require(math.isfinite(value) and 0 <= value <= 1, 'Transition probability outside [0,1]')
        matrix[positions[origin]][positions[destination]] = value
    for values in matrix:
        require(abs(math.fsum(values) - 1) <= 1e-9, 'Each origin must have a complete transition distribution')
    return matrix


def project_state_mass(initial, transitions, *, states, horizons=(1, 3, 6, 12)):
    """Project a closed state mass while preserving the total population."""
    states = tuple(states)
    vector = [float(initial.get(state, 0)) for state in states]
    require(all(math.isfinite(value) and value >= 0 for value in vector), 'Initial state mass invalid')
    matrix = _matrix(states, transitions)
    horizons = tuple(sorted(set(horizons)))
    require(horizons and all(type(horizon) is int and horizon > 0 for horizon in horizons), 'Positive horizons required')
    result = []
    target = 0
    for step in range(1, max(horizons) + 1):
        target_vector = [0.0 for _ in states]
        for origin, mass in enumerate(vector):
            for destination, probability in enumerate(matrix[origin]):
                target_vector[destination] += mass * probability
        vector = target_vector
        if step in horizons:
            result.append({'horizon': step, 'state_mass': dict(zip(states, vector)),
                           'total_mass': math.fsum(vector), 'scenario_type': 'descriptive_transition_scenario'})
    initial_total = math.fsum(float(initial.get(state, 0)) for state in states)
    for row in result:
        require(math.isclose(row['total_mass'], initial_total, rel_tol=1e-9, abs_tol=1e-7), 'Forecast mass not conserved')
    return {'status': 'scenario_only', 'states': list(states), 'initial_total_mass': initial_total,
            'horizons': result, 'backtested': False, 'research_ready': False}


def naive_last_state(initial, *, horizons=(1, 3, 6, 12)):
    """Last-state carry-forward baseline for a future backtest harness."""
    vector = {key: float(value) for key, value in initial.items()}
    require(all(math.isfinite(value) and value >= 0 for value in vector.values()), 'Naive state mass invalid')
    return {'status': 'naive_baseline', 'horizons': [
        {'horizon': horizon, 'state_mass': dict(vector), 'total_mass': math.fsum(vector.values())}
        for horizon in sorted(set(horizons))], 'backtested': False}
