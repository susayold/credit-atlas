"""Label-aware data/model monitoring primitives for research releases."""
from __future__ import annotations

import datetime as dt
import math
from collections import Counter

from .evidence_checks import require


def freshness(last_available, as_of, *, max_age_days):
    """Check source freshness without treating a stale source as current."""
    last = dt.date.fromisoformat(str(last_available)[:10])
    current = dt.date.fromisoformat(str(as_of)[:10])
    require(type(max_age_days) is int and max_age_days >= 0, 'Non-negative freshness limit required')
    age_days = (current - last).days
    require(age_days >= 0, 'Source date cannot be after monitoring as-of')
    return {'status': 'block' if age_days > max_age_days else 'pass',
            'last_available': last.isoformat(), 'as_of': current.isoformat(),
            'age_days': age_days, 'max_age_days': max_age_days}


def missingness(values, *, field, minimum_support=100, warning_rate=0.05, block_rate=0.20):
    """Classify missingness with explicit support and caller-owned thresholds."""
    values = list(values)
    require(values and 0 <= warning_rate <= block_rate <= 1, 'Invalid missingness thresholds')
    missing = sum(value is None for value in values)
    rate = missing / len(values)
    support = len(values) >= minimum_support
    state = 'insufficient_support' if not support else 'block' if rate >= block_rate else 'warning' if rate >= warning_rate else 'pass'
    return {'field': field, 'status': state, 'rows': len(values), 'missing_rows': missing,
            'missing_rate': rate, 'minimum_support': minimum_support,
            'warning_rate': warning_rate, 'block_rate': block_rate}


def categorical_drift(reference, current, *, minimum_support=100, warning_score=0.10, block_score=0.25):
    """Calculate an explicitly configured PSI-like distribution divergence.

    Thresholds are inputs to the research protocol, not universal magic
    values. Insufficient support is reported instead of creating an alert.
    """
    reference, current = list(reference), list(current)
    require(reference and current, 'Drift samples cannot be empty')
    require(0 <= warning_score <= block_score, 'Invalid drift thresholds')
    if min(len(reference), len(current)) < minimum_support:
        return {'status': 'insufficient_support', 'reference_rows': len(reference), 'current_rows': len(current),
                'score': None, 'minimum_support': minimum_support}
    categories = sorted(set(reference) | set(current), key=str)
    ref_counts, cur_counts = Counter(reference), Counter(current)
    epsilon = 1e-12
    score = 0.0
    for category in categories:
        p = max(ref_counts[category] / len(reference), epsilon)
        q = max(cur_counts[category] / len(current), epsilon)
        score += (q - p) * math.log(q / p)
    state = 'block' if score >= block_score else 'warning' if score >= warning_score else 'pass'
    return {'status': state, 'reference_rows': len(reference), 'current_rows': len(current),
            'score': score, 'warning_score': warning_score, 'block_score': block_score,
            'categories': categories, 'minimum_support': minimum_support}


def mature_label_rate(rows, *, minimum_support=100):
    """Compute outcome metrics only on rows explicitly marked mature."""
    rows = list(rows)
    mature = [row for row in rows if row.get('mature') is True and type(row.get('target')) is int]
    require(all(row.get('target') in (0, 1) for row in mature), 'Mature target must be binary')
    events = sum(row['target'] for row in mature)
    return {'status': 'available' if len(mature) >= minimum_support else 'insufficient_support',
            'mature_rows': len(mature), 'events': events,
            'event_rate': events / len(mature) if mature else None,
            'immature_or_unavailable_excluded': len(rows) - len(mature),
            'minimum_support': minimum_support}


def triage_incident(*, incident_type, current_config_hash, previous_config_hash, checks):
    """Return a deterministic research rollback decision for a synthetic incident."""
    require(isinstance(current_config_hash, str) and current_config_hash, 'Current config hash required')
    require(isinstance(previous_config_hash, str) and previous_config_hash, 'Previous config hash required')
    failed = [name for name, result in checks.items() if result is not True]
    action = 'rollback_to_previous_config' if failed else 'continue_monitoring'
    return {'status': 'incident' if failed else 'clear', 'incident_type': incident_type,
            'failed_checks': failed, 'action': action,
            'selected_config_hash': previous_config_hash if failed else current_config_hash,
            'synthetic': True, 'production_incident': False}
