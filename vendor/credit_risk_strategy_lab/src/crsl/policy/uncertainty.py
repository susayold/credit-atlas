"""Paired loan bootstrap for fixed, already-scored origination policies.

Conditional descriptive uncertainty, not causal uplift, time-shock uncertainty,
or model-refitting uncertainty. No policy selection occurs here.
"""
import random
from decimal import Decimal

from .engine import amount, day, fingerprint
from ..evidence_checks import require

METRICS = ('selected_event_rate', 'count_retention', 'principal_retention')


def _metrics(rows, indexes, field):
    total = Decimal(0)
    retained = Decimal(0)
    count = events = 0
    for i in indexes:
        row = rows[i]
        total += row['principal']
        if row[field]:
            retained += row['principal']
            count += 1
            events += row['target']
    return {'selected_event_rate': Decimal(events) / count if count else None,
            'count_retention': Decimal(count) / len(indexes),
            'principal_retention': retained / total}


def _quantile(values, probability):
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def paired_bootstrap(records, *, seed, resamples, confidence, evaluation_cutoff,
                     evidence_class, minimum_events=50):
    """Require one row per loan, known labels, explicit locked sampling settings.

    The caller supplies the common eligible, endpoint-available cohort. Null or
    immature outcomes are rejected, never silently dropped or made negative.
    `baseline_selected` and `candidate_selected` are fixed before resampling.
    """
    require(type(seed) is int and seed >= 0, 'Nonnegative integer seed required')
    require(type(resamples) is int and resamples >= 100, 'At least 100 resamples required')
    level = amount(confidence)
    require(level is not None and 0 < level < 1, 'Invalid confidence level')
    cutoff = day(evaluation_cutoff)
    require(cutoff is not None, 'Date-only evaluation cutoff required')
    require(evidence_class in ('synthetic_demo', 'retrospective_observed'), 'Explicit evidence class required')
    require(type(minimum_events) is int and minimum_events > 0, 'Positive event support threshold required')
    rows = []
    seen = set()
    for source in records:
        identity = source.get('loan_id')
        require(isinstance(identity, str) and bool(identity), 'Loan identifier required')
        require(identity not in seen, 'One origination record per loan required')
        seen.add(identity)
        require(type(source.get('target')) is int and source['target'] in (0, 1), 'Known binary target required')
        known = day(source.get('label_known_at'))
        landmark = day(source.get('landmark'))
        require(known is not None and landmark is not None and landmark <= known < cutoff,
                'Label must be known before evaluation cutoff and after landmark')
        require(source.get('estimand') == 'numeric_d3_before_prepayment'
                and type(source.get('horizon_months')) is int and source['horizon_months'] == 12,
                'Common 12-month D3 estimand required')
        principal = amount(source.get('principal'))
        require(principal is not None and principal > 0, 'Positive finite principal required')
        for field in ('baseline_selected', 'candidate_selected'):
            require(type(source.get(field)) is bool, 'Explicit boolean selection required')
        rows.append({**source, 'principal': principal})
    require(len(rows) >= 2, 'At least two loans required')
    rows.sort(key=lambda r: r['loan_id'])
    indexes = list(range(len(rows)))
    baseline = _metrics(rows, indexes, 'baseline_selected')
    candidate = _metrics(rows, indexes, 'candidate_selected')
    differences = {key: [] for key in METRICS}
    rng = random.Random(seed)
    for _ in range(resamples):
        # The SAME indexes and multiplicities are used for both policies.
        draw = [rng.randrange(len(rows)) for _ in rows]
        base_draw = _metrics(rows, draw, 'baseline_selected')
        candidate_draw = _metrics(rows, draw, 'candidate_selected')
        for key in METRICS:
            if base_draw[key] is not None and candidate_draw[key] is not None:
                differences[key].append(candidate_draw[key] - base_draw[key])
    event_support = {field: sum(r['target'] for r in rows if r[field])
                     for field in ('baseline_selected', 'candidate_selected')}
    output = {}
    tail = (1 - level) / 2
    for key, draws in differences.items():
        reasons = []
        if len(draws) * 100 < resamples * 95:
            reasons.append('less_than_95_percent_defined_resamples')
        if key == 'selected_event_rate' and min(event_support.values()) < minimum_events:
            reasons.append('insufficient_selected_events')
        estimate = candidate[key] - baseline[key] if candidate[key] is not None and baseline[key] is not None else None
        if estimate is None:
            reasons.append('undefined_point_estimate')
        interval = None if reasons else [str(_quantile(draws, tail)), str(_quantile(draws, 1 - tail))]
        output[key] = {'baseline': None if baseline[key] is None else str(baseline[key]),
                       'candidate': None if candidate[key] is None else str(candidate[key]),
                       'candidate_minus_baseline': None if estimate is None else str(estimate),
                       'percentile_interval': interval, 'defined_resamples': len(draws),
                       'undefined_resamples': resamples - len(draws), 'suppression_reasons': reasons}
    cohort = [{key: str(r[key]) if key in ('principal', 'landmark', 'label_known_at') else r[key]
               for key in ('loan_id', 'principal', 'target', 'baseline_selected', 'candidate_selected',
                           'landmark', 'label_known_at', 'estimand', 'horizon_months')}
              for r in rows]
    return {'evidence_class': evidence_class, 'status': 'descriptive_conditional_bootstrap',
            'cohort_sha256': fingerprint(cohort), 'loans': len(rows),
            'settings': {'seed': seed, 'resamples': resamples, 'confidence': str(level),
                         'minimum_events': minimum_events, 'evaluation_cutoff': str(cutoff),
                         'sampling_unit': 'loan', 'interval_method': 'percentile_linear_interpolation'},
            'selected_event_support': event_support, 'metrics': output,
            'policy_selection_performed': False, 'causal_interpretation_permitted': False}
