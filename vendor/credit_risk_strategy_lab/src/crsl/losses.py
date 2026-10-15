"""Loss accounting bridge and resolved-cohort diagnostics.

This module keeps reported source signs and component availability intact. It
selects one terminal record per loan before summing, so cumulative terminal
rows cannot be counted repeatedly. It does not estimate lender P&L, recovery
cashflow, LGD, or expected loss when the source does not support those claims.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

from .evidence_checks import require

COMPONENTS = (
    'removal_upb', 'net_sales_proceeds', 'delinquent_accrued_interest',
    'total_expenses', 'mi_recoveries', 'non_mi_recoveries',
)
EXPENSE_COMPONENTS = ('legal_costs', 'maintenance_costs', 'taxes_insurance', 'misc_expenses')
LOSS_CODES = {'02', '03', '09', '15'}


def _date(value):
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _number(value):
    if value is None or value == '':
        return None
    value = float(value)
    require(math.isfinite(value), 'Loss amount must be finite')
    return value


def _record_sort_key(row):
    return (_date(row.get('zero_balance_date')) or _date(row.get('period')) or dt.date.max,
            _date(row.get('period')) or dt.date.max)


def first_terminal_records(rows):
    """Return exactly one earliest loss-code terminal row per loan."""
    groups = defaultdict(list)
    for row in rows:
        loan_id = row.get('loan_id')
        require(isinstance(loan_id, str) and loan_id, 'Loss row requires loan_id')
        if row.get('zero_balance_code') in LOSS_CODES:
            groups[loan_id].append(row)
    selected = []
    for loan_id, candidates in groups.items():
        ordered = sorted(candidates, key=_record_sort_key)
        first = dict(ordered[0])
        first['terminal_row_count'] = len(candidates)
        first['duplicate_terminal_rows'] = max(0, len(candidates) - 1)
        selected.append(first)
    return sorted(selected, key=lambda row: row['loan_id'])


def component_residual(row):
    """Reconcile actual_loss only when every signed component is present."""
    actual = _number(row.get('actual_loss'))
    components = [_number(row.get(name)) for name in COMPONENTS]
    if actual is None or any(value is None for value in components):
        return None
    return actual - math.fsum(components)


def expense_residual(row):
    total = _number(row.get('total_expenses'))
    components = [_number(row.get(name)) for name in EXPENSE_COMPONENTS]
    if total is None or any(value is None for value in components):
        return None
    return total - math.fsum(components)


def _availability(row, recent_start):
    actual = _number(row.get('actual_loss'))
    if actual is not None:
        return 'reported'
    if row.get('defect_settlement_date') is not None:
        return 'withheld_defect'
    zero_date = _date(row.get('zero_balance_date'))
    if zero_date is not None and zero_date >= recent_start:
        return 'recent_disposition'
    return 'unexplained_missing'


def summarize(rows, *, recent_start='2026-01-01', severity_denominator='removal_upb'):
    """Produce aggregate-only resolved loss evidence and an explicit gate."""
    recent_start = _date(recent_start)
    require(recent_start is not None, 'Loss recent_start required')
    require(severity_denominator in {'removal_upb', 'original_upb'}, 'Unsupported severity denominator')
    selected = first_terminal_records(rows)
    availability = defaultdict(int)
    resolved_amounts = []
    severities = []
    bridge = {name: 0.0 for name in COMPONENTS}
    bridge_rows = 0
    missing_component_rows = 0
    loss_residuals = []
    expense_residuals = []
    zero_denominator_rows = 0
    for row in selected:
        reason = _availability(row, recent_start)
        availability[reason] += 1
        actual = _number(row.get('actual_loss'))
        if actual is not None:
            resolved_amounts.append(actual)
            denominator = _number(row.get(severity_denominator))
            if denominator is None or denominator == 0:
                zero_denominator_rows += 1
            else:
                # Release components can be signed. Severity uses the positive
                # exposure magnitude while the raw bridge retains its signs.
                severities.append(abs(actual) / abs(denominator))
        values = [_number(row.get(name)) for name in COMPONENTS]
        if all(value is not None for value in values):
            bridge_rows += 1
            for name, value in zip(COMPONENTS, values):
                bridge[name] += value
        else:
            missing_component_rows += 1
        residual = component_residual(row)
        if residual is not None:
            loss_residuals.append(residual)
        residual = expense_residual(row)
        if residual is not None:
            expense_residuals.append(residual)
    resolved = len(resolved_amounts)
    denominator_rows = len(severities)
    gate_reasons = []
    if resolved < 1000:
        gate_reasons.append('resolved_support_below_1000')
    if denominator_rows < 1000:
        gate_reasons.append('severity_denominator_support_below_1000')
    if missing_component_rows:
        gate_reasons.append('partial_component_coverage')
    return {
        'status': 'observed_loss_descriptive',
        'terminal_loans': len(selected),
        'reported_loss_loans': resolved,
        'unresolved_terminal_loans': len(selected) - resolved,
        'availability': dict(sorted(availability.items())),
        'severity_denominator': severity_denominator,
        'severity_uses_absolute_denominator': True,
        'severity_observation_loans': denominator_rows,
        'zero_or_missing_denominator_loans': zero_denominator_rows,
        'reported_loss_sum_usd': math.fsum(resolved_amounts) if resolved_amounts else None,
        'reported_loss_mean_usd': math.fsum(resolved_amounts) / resolved if resolved else None,
        'reported_loss_min_usd': min(resolved_amounts) if resolved_amounts else None,
        'reported_loss_max_usd': max(resolved_amounts) if resolved_amounts else None,
        'severity_mean_uncapped': math.fsum(severities) / denominator_rows if severities else None,
        'severity_min_uncapped': min(severities) if severities else None,
        'severity_max_uncapped': max(severities) if severities else None,
        'component_bridge': bridge if bridge_rows else None,
        'component_bridge_complete_rows': bridge_rows,
        'partial_component_rows': missing_component_rows,
        'loss_formula_checked_rows': len(loss_residuals),
        'loss_formula_max_abs_residual_usd': max((abs(v) for v in loss_residuals), default=None),
        'expense_formula_checked_rows': len(expense_residuals),
        'expense_formula_max_abs_residual_usd': max((abs(v) for v in expense_residuals), default=None),
        'duplicate_terminal_rows_removed': sum(r['duplicate_terminal_rows'] for r in selected),
        'gate_status': 'blocked' if gate_reasons else 'eligible_for_loss_model_review',
        'gate_reasons': gate_reasons,
        'expected_loss_dollars': None,
        'research_ready': False,
    }
