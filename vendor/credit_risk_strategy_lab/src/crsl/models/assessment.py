"""Compose baseline, calibration and validation with disjoint loan cohorts.

In-memory development orchestration; file-backed score/source integration and
final research approvals are deliberately separate.
"""
from .baseline import Baseline
from .calibration import SigmoidCalibration
from .evaluation import evaluate_probabilities
from .train import require_training_gate
from .tuning import tune_logistic, TuningFailed
from .challenger import BoostingChallenger
from ..evidence_checks import require
from ..policy.engine import day, fingerprint


def assess(records, feature_config, settings, *, evidence_class, split_manifest=None, split_audit=None):
    required = {'train_cutoff', 'calibration_cutoff', 'evaluation_cutoff',
                'logistic_C', 'calibration_C', 'minimum_events', 'bin_edges'}
    require(required <= set(settings) <= required | {'logistic_tuning','challenger_parameters'}, 'Unsupported assessment settings')
    dates = [day(settings[k]) for k in ('train_cutoff', 'calibration_cutoff', 'evaluation_cutoff')]
    require(all(d is not None for d in dates) and dates[0] < dates[1] < dates[2], 'Assessment cutoffs must increase')
    require(evidence_class in ('synthetic_demo', 'retrospective_development'), 'Explicit assessment evidence required')
    if evidence_class == 'retrospective_development':
        require(split_manifest is not None and split_audit is not None, 'Real assessment requires qualified split evidence')
        require_training_gate(split_manifest, split_audit)
        config = split_manifest['config']
        require([config[k] for k in ('train_fit_month', 'calibration_fit_month', 'selection_freeze_month')]
                == [str(d) for d in dates], 'Assessment cutoffs differ from split protocol')
    cohorts = {role: [] for role in ('train', 'calibration', 'validation')}
    seen = set()
    for row in records:
        role, identity = row.get('partition'), row.get('loan_id')
        require(role in cohorts, 'Assessment never accepts final test or unused partitions')
        require(row.get('included') is True, 'Assessment requires explicit included rows')
        require(isinstance(identity, str) and identity and identity not in seen, 'Loan overlap across assessment cohorts')
        seen.add(identity)
        cohorts[role].append(row)
    require(all(cohorts.values()), 'Train, calibration and validation cohorts all required')
    for role in cohorts:
        cohorts[role].sort(key=lambda r: r['loan_id'])
    tuning = settings.get('logistic_tuning')
    tuning_result = None
    chosen_C = settings['logistic_C']
    if tuning is not None:
        require(chosen_C is None, 'Specify either fixed C or tuning, not both')
        require(isinstance(tuning, dict) and set(tuning) == {'folds', 'C_grid', 'minimum_train_class', 'minimum_holdout_class'},
                'Unsupported tuning configuration')
        tuning_result = tune_logistic(cohorts['train'], feature_config,
            outer_fit_cutoff=settings['train_cutoff'], evidence_class=evidence_class, **tuning)
        if tuning_result['status'] != 'training_selection_complete':
            raise TuningFailed(tuning_result)
        chosen_C = float(tuning_result['selected_C'])
    results = {}
    challenger_parameters = settings.get('challenger_parameters')
    kinds = ['constant', 'logistic'] + (['challenger'] if challenger_parameters is not None else [])
    for kind in kinds:
        component = (BoostingChallenger(feature_config, challenger_parameters) if kind == 'challenger'
                     else Baseline(feature_config, kind=kind, C=chosen_C))
        baseline = component.fit(
            cohorts['train'], fit_cutoff=settings['train_cutoff'], evidence_class=evidence_class)
        model_payload = {'state': baseline.state, 'encoder': baseline.encoder.state, 'features': feature_config}
        digest = fingerprint(model_payload)
        calibration_rows = [{**row, 'raw_pd': pd, 'model_sha256': digest,
            'model_available_at': settings['train_cutoff'], 'evidence_class': evidence_class}
            for row, pd in zip(cohorts['calibration'], baseline.predict(cohorts['calibration']), strict=True)]
        calibrator = SigmoidCalibration(C=settings['calibration_C'], minimum_events=settings['minimum_events']).fit(
            calibration_rows, fit_cutoff=settings['calibration_cutoff'], model_sha256=digest, evidence_class=evidence_class)
        validation_rows = [{**row, 'raw_pd': pd, 'model_sha256': digest, 'evidence_class': evidence_class}
            for row, pd in zip(cohorts['validation'], baseline.predict(cohorts['validation']), strict=True)]
        calibrated = calibrator.predict(validation_rows)
        metrics = {}
        score_payloads = {}
        for version, values, available in (
            ('raw', [r['raw_pd'] for r in validation_rows], settings['train_cutoff']),
            ('calibrated', calibrated, settings['calibration_cutoff'])):
            scores = [{'loan_id': row['loan_id'], 'pd': pd} for row, pd in zip(validation_rows, values, strict=True)]
            score_digest = fingerprint({'model_sha256': digest, 'version': version,
                'calibration': calibrator.state if version == 'calibrated' else None, 'scores': scores})
            evaluation_rows = [{**row, 'pd': pd, 'score_sha256': score_digest, 'score_available_at': available}
                for row, pd in zip(validation_rows, values, strict=True)]
            metrics[version] = evaluate_probabilities(evaluation_rows,
                evaluation_cutoff=settings['evaluation_cutoff'], bin_edges=settings['bin_edges'],
                minimum_events=settings['minimum_events'])
            score_payloads[version] = scores
        results[kind] = {'model': model_payload, 'model_content_sha256': digest,
                         'calibration': calibrator.state, 'validation_metrics': metrics,
                         'private_validation_scores': score_payloads}
    return {'status': 'development_assessment_complete', 'evidence_class': evidence_class,
            'settings': settings, 'cohort_counts': {role: len(rows) for role, rows in cohorts.items()},
            'models': results, 'logistic_tuning': tuning_result, 'selected_logistic_C': chosen_C,
            'champion_selected': False, 'final_test_access': False,
            'public_release_approved': False, 'research_ready': False}
