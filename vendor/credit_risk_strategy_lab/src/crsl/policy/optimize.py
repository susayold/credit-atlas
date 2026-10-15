"""Validation-only finite candidate frontier; no model or economic claims.

Input measures must be independently computed on a common maturity-aligned
cohort. This primitive does not certify that upstream evidence contract.
"""
from decimal import Decimal

from .engine import amount, fingerprint
from ..evidence_checks import require


def validation_frontier(candidates, *, partition, minimum_principal_retention,
                        candidate_ids, minimum_events=50):
    """Return every candidate, including infeasible/unsupported candidates.

    Both count and principal retention are maximized; observed selected event
    rate is minimized. No champion is automatically chosen from the frontier.
    candidate_ids is the caller's predeclared menu, not a test-derived grid.
    """
    require(partition == 'validation', 'Policy selection requires validation, never test')
    cap = amount(minimum_principal_retention)
    require(cap is not None and 0 <= cap <= 1, 'Invalid retention constraint')
    require(type(minimum_events) is int and minimum_events > 0, 'Invalid support threshold')
    require(isinstance(candidate_ids, (list, tuple)) and bool(candidate_ids), 'Predeclared menu required')
    require(all(isinstance(i, str) and i for i in candidate_ids), 'Invalid candidate ID')
    require(len(set(candidate_ids)) == len(candidate_ids), 'Duplicate menu identifier')
    rows = list(candidates)
    require(len(rows) == len(candidate_ids), 'Candidate menu changed')
    require({r['candidate_id'] for r in rows} == set(candidate_ids), 'Candidate menu changed')
    common = None
    output = []
    for row in rows:
        require(set(row) == {'candidate_id', 'cohort_sha256', 'base_count', 'base_principal',
                            'selected_count', 'selected_principal', 'selected_events',
                            'constraints_passed'}, 'Unsupported candidate fields')
        require(isinstance(row['cohort_sha256'], str) and len(row['cohort_sha256']) == 64,
                'Common cohort fingerprint required')
        for key in ('base_count', 'selected_count', 'selected_events'):
            require(type(row[key]) is int and row[key] >= 0, 'Invalid count')
        require(0 <= row['selected_events'] <= row['selected_count'] <= row['base_count']
                and row['base_count'] > 0, 'Count reconciliation failed')
        base, selected = amount(row['base_principal']), amount(row['selected_principal'])
        require(base is not None and selected is not None and base > 0 and 0 <= selected <= base,
                'Principal reconciliation failed')
        require((row['selected_count'] == 0) == (selected == 0), 'Empty selection principal mismatch')
        require(type(row['constraints_passed']) is bool, 'Explicit constraint status required')
        identity = (row['cohort_sha256'], row['base_count'], base)
        if common is None:
            common = identity
        require(common == identity, 'Candidates must share cohort and denominators')
        principal_retention = selected / base
        count_retention = Decimal(row['selected_count']) / row['base_count']
        risk = Decimal(row['selected_events']) / row['selected_count'] if row['selected_count'] else None
        reasons = []
        if not row['constraints_passed']:
            reasons.append('upstream_constraint_failed')
        if principal_retention < cap:
            reasons.append('below_retention_floor')
        if row['selected_events'] < minimum_events:
            reasons.append('insufficient_selected_events')
        if risk is None:
            reasons.append('empty_selection')
        output.append(dict(candidate_id=row['candidate_id'], principal_retention=principal_retention,
                           count_retention=count_retention, observed_event_rate=risk,
                           eligible_for_frontier=not reasons, exclusion_reasons=reasons,
                           pareto=False))
    feasible = [r for r in output if r['eligible_for_frontier']]
    for row in feasible:
        def dominates(other):
            weak = (other['principal_retention'] >= row['principal_retention'] and
                    other['count_retention'] >= row['count_retention'] and
                    other['observed_event_rate'] <= row['observed_event_rate'])
            strict = (other['principal_retention'] > row['principal_retention'] or
                      other['count_retention'] > row['count_retention'] or
                      other['observed_event_rate'] < row['observed_event_rate'])
            return weak and strict
        row['pareto'] = not any(dominates(other) for other in feasible)
    return {'status': 'frontier_available' if feasible else 'infeasible_or_unsupported',
            'partition': partition, 'champion_selected': False,
            'menu_sha256': fingerprint(sorted(candidate_ids)),
            'minimum_principal_retention': str(cap), 'minimum_events': minimum_events,
            'candidates': [{k: str(v) if isinstance(v, Decimal) else v for k, v in row.items()}
                           for row in sorted(output, key=lambda r: r['candidate_id'])]}
