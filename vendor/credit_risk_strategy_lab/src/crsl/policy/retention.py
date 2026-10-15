"""Whole-loan, whole-tie fixed-retention ranking primitive.

Requires an upstream qualified, completely scored cohort. This is not a model
qualification gate or permission to remove unscored loans from the denominator.
"""
from decimal import Decimal

from .engine import amount, fingerprint
from ..evidence_checks import require


def fixed_retention(records, *, target, basis, evidence_class):
    """Select ascending risk groups until at least target volume is retained.

    Include the entire boundary score group. Report any overshoot explicitly.
    Scores are ranking values in [0,1], not certified calibrated probabilities.
    The frozen rule may be applied to a new cohort without its outcomes, but its
    realized boundary score is cohort-specific, not a frozen absolute cutoff.
    """
    threshold = amount(target)
    require(threshold is not None and 0 <= threshold <= 1, 'Target must be a fraction 0..1')
    require(basis in ('count', 'principal'), 'Unknown retention basis')
    require(evidence_class in ('synthetic_demo', 'retrospective_observed'), 'Explicit evidence class required')
    groups = {}
    seen = set()
    total_principal = Decimal(0)
    inputs = []
    for row in records:
        identity = row.get('loan_id')
        require(isinstance(identity, str) and bool(identity) and identity not in seen,
                'Unique nonempty loan identifier required')
        seen.add(identity)
        principal, score = amount(row.get('principal')), amount(row.get('risk_score'))
        require(principal is not None and principal > 0, 'Positive finite principal required')
        require(score is not None and 0 <= score <= 1, 'Complete finite risk scores required; do not drop missing')
        groups.setdefault(score, []).append((identity, principal))
        total_principal += principal
        inputs.append({'loan_id': identity, 'principal': str(principal), 'risk_score': str(score)})
    require(bool(seen), 'Empty qualified cohort')
    denominator = Decimal(len(seen)) if basis == 'count' else total_principal
    required = threshold * denominator
    selected = set()
    selected_principal = Decimal(0)
    volume = Decimal(0)
    boundary = None
    boundary_size = 0
    for score, loans in sorted(groups.items()):
        if volume >= required:
            break
        selected.update(identity for identity, _ in loans)
        selected_principal += sum((principal for _, principal in loans), Decimal(0))
        volume = Decimal(len(selected)) if basis == 'count' else selected_principal
        boundary, boundary_size = score, len(loans)
    settings = {'method': 'ascending_risk_whole_boundary_tie', 'target': str(threshold), 'basis': basis}
    return {'evidence_class': evidence_class, 'settings': settings, 'rule_sha256': fingerprint(settings),
            'cohort_sha256': fingerprint(sorted(inputs, key=lambda r: r['loan_id'])),
            'universe_count': len(seen), 'selected_count': len(selected),
            'base_principal': str(total_principal), 'selected_principal': str(selected_principal),
            'count_retention': str(Decimal(len(selected)) / len(seen)),
            'principal_retention': str(selected_principal / total_principal),
            'boundary_score': None if boundary is None else str(boundary),
            'boundary_group_count': boundary_size,
            'target_overshoot_fraction': str(volume / denominator - threshold),
            'decisions': [{'loan_id': identity, 'decision': 'selected' if identity in selected else 'review'}
                          for identity in sorted(seen)],
            'outcomes_used': False, 'model_qualification_performed': False}
