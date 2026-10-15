"""Finite-grid logistic regularization selection inside outer training only."""
import math
import copy

from .baseline import Baseline, training_rows
from ..evidence_checks import require
from ..policy.engine import amount, day, fingerprint


class TuningFailed(ValueError):
    """Carry the complete finite-grid result through the fail-closed runner."""
    def __init__(self, result):
        super().__init__('Tuning failed; no default-C fallback')
        self.result = copy.deepcopy(result)


def tune_logistic(records, feature_config, *, outer_fit_cutoff, folds, C_grid,
                  evidence_class, minimum_train_class=200, minimum_holdout_class=50):
    rows = training_rows(records, outer_fit_cutoff)
    require(evidence_class in ('synthetic_demo', 'retrospective_development'), 'Tuning evidence required')
    require(all(type(v) is int and v > 0 for v in (minimum_train_class, minimum_holdout_class)),
            'Positive fold support settings required')
    grid = [amount(value) for value in C_grid]
    require(bool(grid) and all(v is not None and v > 0 and math.isfinite(float(v)) for v in grid), 'Invalid C grid')
    require(len(set(grid)) == len(grid), 'Duplicate regularization candidate')
    require(isinstance(folds, list) and len(folds) >= 2, 'At least two predeclared temporal folds required')
    prepared, held_ids = [], set()
    previous_fit = None
    for index, spec in enumerate(folds):
        require(set(spec) == {'fit_cutoff', 'holdout_landmark_end', 'evaluation_cutoff'}, 'Unsupported fold definition')
        fit, end, evaluation = [day(spec[k]) for k in ('fit_cutoff', 'holdout_landmark_end', 'evaluation_cutoff')]
        require(all(v is not None for v in (fit, end, evaluation)) and fit < end <= evaluation <= day(outer_fit_cutoff),
                'Invalid fold chronology')
        require(previous_fit is None or previous_fit < fit, 'Fold fit cutoffs must increase')
        previous_fit = fit
        train = [r for r in rows if day(r['label_known_month']) < fit]
        holdout = [r for r in rows if fit <= day(r['landmark']) < end and day(r['label_known_month']) < evaluation]
        identities = {r['loan_id'] for r in holdout}
        require(not identities & held_ids, 'Internal holdout loans overlap across folds')
        held_ids.update(identities)
        counts = {}
        for role, data, threshold in (('train', train, minimum_train_class), ('holdout', holdout, minimum_holdout_class)):
            positive = sum(r['target'] for r in data)
            counts[role] = {'loans': len(data), 'events': positive, 'nonevents': len(data)-positive}
            require(min(positive, len(data)-positive) >= threshold, 'Insufficient internal fold support: ' + role)
        prepared.append((spec, train, holdout, counts))
    candidates = []
    for candidate in sorted(grid):
        results, failures = [], []
        for index, (spec, train, holdout, counts) in enumerate(prepared):
            try:
                model = Baseline(feature_config, kind='logistic', C=float(candidate)).fit(
                    train, fit_cutoff=spec['fit_cutoff'], evidence_class=evidence_class)
                # Temporary role is solely for the model's chronological scoring
                # guard; original outer-training rows are never mutated.
                predictions = model.predict([{**r, 'partition': 'validation'} for r in holdout])
                clipped = [min(1-1e-15, max(1e-15, p)) for p in predictions]
                loss_sum = -math.fsum(r['target']*math.log(p)+(1-r['target'])*math.log1p(-p)
                                      for r, p in zip(holdout, clipped, strict=True))
                results.append({'fold': index, 'counts': counts, 'log_loss_sum': loss_sum,
                                'log_loss': loss_sum / len(holdout),
                                'encoder_fit_rows': model.encoder.state['fit_rows']})
            except (ValueError, RuntimeError, Warning) as error:
                failures.append({'fold': index, 'exception_type': type(error).__name__, 'message': str(error)})
        pooled = None if failures else sum(r['log_loss_sum'] for r in results) / sum(r['counts']['holdout']['loans'] for r in results)
        candidates.append({'C': str(candidate), 'status': 'failed' if failures else 'evaluated',
                           'pooled_holdout_log_loss': pooled, 'folds': results, 'failures': failures})
    eligible = [r for r in candidates if r['status'] == 'evaluated']
    selected = min(eligible, key=lambda r: (r['pooled_holdout_log_loss'], amount(r['C']))) if eligible else None
    settings = dict(outer_fit_cutoff=str(day(outer_fit_cutoff)), folds=folds, C_grid=[str(v) for v in sorted(grid)],
                    minimum_train_class=minimum_train_class, minimum_holdout_class=minimum_holdout_class)
    return {'status': 'training_selection_complete' if selected else 'all_candidates_failed',
            'selected_C': selected['C'] if selected else None, 'candidates': candidates,
            'settings': settings, 'settings_sha256': fingerprint(settings), 'evidence_class': evidence_class,
            'objective': 'pooled_internal_holdout_log_loss', 'tie_break': 'smaller_C',
            'calibration_data_used': False, 'outer_validation_data_used': False,
            'final_test_access': False, 'research_ready': False}
