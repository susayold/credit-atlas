"""Development sigmoid-on-logit recalibration on a separate calibration cohort."""
import math
import re
import warnings
import json
from pathlib import Path

from .baseline import sigmoid
from ..policy.engine import amount, day
from ..evidence_checks import require
from ..evidence_checks import require_hash
from ..source import sha256, write_json_new


def logit(probability):
    parsed = amount(probability)
    require(parsed is not None and 0 <= parsed <= 1, 'Finite probability in [0,1] required')
    # Clip only for finite logit computation, never to silently repair invalid PD.
    bounded = min(1 - 1e-12, max(1e-12, float(parsed)))
    return math.log(bounded) - math.log1p(-bounded)


class SigmoidCalibration:
    def __init__(self, *, C, minimum_events=50):
        require(type(C) in (int, float) and math.isfinite(C) and C > 0, 'Positive calibration C required')
        require(type(minimum_events) is int and minimum_events > 0, 'Positive class support required')
        self.C, self.minimum_events, self.state = C, minimum_events, None

    def fit(self, records, *, fit_cutoff, model_sha256, evidence_class):
        require(self.state is None, 'Calibration is fit once; create a new version for refitting')
        require(isinstance(model_sha256, str) and re.fullmatch('[0-9a-f]{64}', model_sha256), 'Model digest required')
        require(evidence_class in ('synthetic_demo', 'retrospective_development'), 'Calibration evidence required')
        cutoff = day(fit_cutoff)
        require(cutoff is not None, 'Date-only calibration cutoff required')
        rows = list(records)
        require(bool(rows), 'Empty calibration cohort')
        seen = set()
        matrix, targets = [], []
        for row in sorted(rows, key=lambda r: r['loan_id']):
            identity = row['loan_id']
            require(isinstance(identity, str) and identity and identity not in seen, 'Unique calibration loan required')
            seen.add(identity)
            require(row.get('partition') == 'calibration' and row.get('included') is True,
                    'Fit calibration only on included calibration rows')
            require(row.get('model_sha256') == model_sha256, 'Mixed upstream models')
            require(row.get('evidence_class') == evidence_class, 'Mixed calibration evidence')
            landmark, known, model_at = day(row.get('landmark')), day(row.get('label_known_month')), day(row.get('model_available_at'))
            require(all(v is not None for v in (landmark, known, model_at))
                    and model_at <= landmark <= known < cutoff, 'Calibration availability order violated')
            require(type(row.get('target')) is int and row['target'] in (0, 1), 'Binary calibration target required')
            matrix.append([logit(row.get('raw_pd'))])
            targets.append(row['target'])
        events = sum(targets)
        require(min(events, len(rows) - events) >= self.minimum_events, 'Insufficient calibration class support')
        constant_input = len({value[0] for value in matrix}) == 1
        if constant_input:
            # With no score variation the slope is not identifiable from data.
            # The intercept-only MLE is the calibration (not validation) prevalence.
            slope, intercept = 0.0, logit(events / len(rows))
        else:
            from sklearn.exceptions import ConvergenceWarning
            from sklearn.linear_model import LogisticRegression
            with warnings.catch_warnings():
                warnings.simplefilter('error', ConvergenceWarning)
                fitted = LogisticRegression(C=self.C, solver='lbfgs', max_iter=2000, tol=1e-8,
                                             class_weight=None).fit(matrix, targets)
            slope, intercept = float(fitted.coef_[0, 0]), float(fitted.intercept_[0])
        require(math.isfinite(slope) and math.isfinite(intercept), 'Nonfinite calibration parameters')
        # A rank-reversing fit is a model/data investigation, not a hidden repair.
        require(slope >= 0, 'Negative calibration slope: investigate upstream ranking')
        self.state = dict(method='regularized_sigmoid_on_logit', slope=slope, intercept=intercept,
                          C=self.C, minimum_events=self.minimum_events, fit_cutoff=str(cutoff),
                          model_sha256=model_sha256, evidence_class=evidence_class,
                          rows=len(rows), events=events, logit_clip=1e-12,
                          fit_case='constant_input_intercept_only' if constant_input else 'varying_scores',
                          research_ready=False, final_test_access=False)
        return self

    def predict(self, records):
        require(self.state is not None, 'Fit calibration first')
        predictions = []
        for row in records:
            require(row.get('partition') == 'validation' and row.get('included') is True,
                    'Development calibrated scoring supports validation only')
            require(row.get('model_sha256') == self.state['model_sha256'], 'Upstream model changed')
            require(row.get('evidence_class') == self.state['evidence_class'], 'Scoring evidence changed')
            landmark = day(row.get('landmark'))
            require(landmark is not None and landmark >= day(self.state['fit_cutoff']),
                    'Scoring precedes calibration availability')
            predictions.append(sigmoid(self.state['slope'] * logit(row.get('raw_pd')) + self.state['intercept']))
        return predictions

    def save(self, path):
        require(self.state is not None, 'Fit calibration before saving')
        write_json_new(Path(path), {'schema_version': 1, 'state': self.state})
        return sha256(Path(path))

    @classmethod
    def load(cls, path, *, expected_sha256):
        require_hash(Path(path), expected_sha256)
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        require(payload['schema_version'] == 1, 'Unsupported calibration schema')
        state = payload['state']
        require(state['method'] == 'regularized_sigmoid_on_logit' and state['logit_clip'] == 1e-12,
                'Unsupported calibration method')
        require(all(type(state[k]) in (int, float) and math.isfinite(state[k]) for k in ('slope', 'intercept'))
                and state['slope'] >= 0, 'Invalid calibration parameters')
        require(day(state['fit_cutoff']) is not None and re.fullmatch('[0-9a-f]{64}', state['model_sha256']),
                'Invalid calibration lineage')
        require(state['research_ready'] is False and state['final_test_access'] is False
                and state['evidence_class'] in ('synthetic_demo', 'retrospective_development'),
                'Invalid development evidence status')
        model = cls(C=state['C'], minimum_events=state['minimum_events'])
        require(type(state['rows']) is int and type(state['events']) is int
                and min(state['events'], state['rows'] - state['events']) >= model.minimum_events,
                'Invalid calibration support')
        model.state = state
        return model
