"""Train-only constant/logistic components with JSON-only scoring persistence.

No final-test access or claim of qualified real model training in this module.
"""
import copy
import json
import math
import warnings
from pathlib import Path

from ..features import OriginationEncoder
from ..policy.engine import day
from ..evidence_checks import require, require_hash
from ..source import sha256, write_json_new


def training_rows(records, fit_cutoff):
    cutoff = day(fit_cutoff)
    require(cutoff is not None, 'Date-only fit cutoff required')
    rows = list(records)
    require(bool(rows), 'Empty training data')
    seen = set()
    for row in rows:
        identity = row.get('loan_id')
        require(isinstance(identity, str) and identity and identity not in seen, 'Unique training loan required')
        seen.add(identity)
        require(row.get('partition') == 'train' and row.get('included') is True, 'Fit only included train rows')
        require(type(row.get('target')) is int and row['target'] in (0, 1), 'Binary training target required')
        known, landmark = day(row.get('label_known_month')), day(row.get('landmark'))
        require(known is not None and landmark is not None and landmark <= known < cutoff,
                'Training labels must precede fit cutoff')
    return sorted(rows, key=lambda r: r['loan_id'])


def scoring_rows(records):
    rows = list(records)
    for row in rows:
        require(row.get('partition') in ('train', 'calibration', 'validation'),
                'Baseline development scorer never opens final test')
        require(row.get('included') is True, 'Only included scoring rows supported')
    return rows


def sigmoid(value):
    require(math.isfinite(value), 'Nonfinite linear score')
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1 + exponential)


class Baseline:
    def __init__(self, feature_config, *, kind, C=1.0):
        require(kind in ('constant', 'logistic'), 'Unsupported baseline kind')
        require(type(C) in (int, float) and math.isfinite(C) and C > 0, 'Positive finite regularization C required')
        self.feature_config = copy.deepcopy(feature_config)
        self.encoder = OriginationEncoder(feature_config)
        self.kind, self.C = kind, C
        self.state = None

    def fit(self, records, *, fit_cutoff, evidence_class):
        require(self.state is None, 'Create a new model for each fit')
        require(evidence_class in ('synthetic_demo', 'retrospective_development'), 'Explicit model evidence required')
        rows = training_rows(records, fit_cutoff)
        labels = [r['target'] for r in rows]
        self.encoder.fit(rows)
        state = dict(kind=self.kind, C=self.C, fit_cutoff=str(day(fit_cutoff)),
                     evidence_class=evidence_class, training_rows=len(rows),
                     training_events=sum(labels), prevalence=sum(labels) / len(labels),
                     calibration_status='not_calibrated', final_test_access=False)
        if self.kind == 'logistic':
            require(set(labels) == {0, 1}, 'Logistic training requires both classes')
            import numpy as np
            import sklearn
            from sklearn.exceptions import ConvergenceWarning
            from sklearn.linear_model import LogisticRegression
            matrix = np.asarray(self.encoder.transform(rows), dtype=float)
            require(matrix.ndim == 2 and matrix.shape[1] > 0 and np.isfinite(matrix).all(), 'Invalid training matrix')
            with warnings.catch_warnings():
                warnings.simplefilter('error', ConvergenceWarning)
                estimator = LogisticRegression(C=self.C, solver='lbfgs', max_iter=2000,
                                               tol=1e-8, class_weight=None).fit(matrix, labels)
            state.update(coefficients=estimator.coef_[0].tolist(), intercept=float(estimator.intercept_[0]),
                         sklearn_version=sklearn.__version__, iterations=int(estimator.n_iter_[0]))
            require(all(math.isfinite(v) for v in state['coefficients'] + [state['intercept']]),
                    'Nonfinite fitted parameters')
        self.state = state
        return self

    def predict(self, records):
        require(self.state is not None, 'Model must be fitted')
        rows = scoring_rows(records)
        for row in rows:
            if row['partition'] != 'train':
                landmark = day(row.get('landmark'))
                require(landmark is not None and landmark >= day(self.state['fit_cutoff']),
                        'Evaluation landmark precedes model fit cutoff')
        # Enforce column/schema and numeric validity for both baseline kinds.
        matrix = self.encoder.transform(rows)
        if self.kind == 'constant':
            return [self.state['prevalence']] * len(rows)
        return [sigmoid(math.fsum(a * b for a, b in zip(vector, self.state['coefficients'], strict=True))
                        + self.state['intercept']) for vector in matrix]

    def save(self, path):
        require(self.state is not None, 'Cannot persist an unfitted model')
        payload = dict(schema_version=1, feature_config=self.feature_config, model=self.state,
                       encoder=self.encoder.state)
        write_json_new(Path(path), payload)
        return sha256(Path(path))

    @classmethod
    def load(cls, path, *, expected_sha256):
        require_hash(Path(path), expected_sha256)
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        return cls.from_payload(payload)

    @classmethod
    def from_payload(cls, payload):
        """Validate a decoded JSON payload; callers handle its external hash pin."""
        require(payload['schema_version'] == 1, 'Unsupported model schema')
        state, encoder = payload['model'], payload['encoder']
        model = cls(payload['feature_config'], kind=state['kind'], C=state['C'])
        require(encoder['fit_partition'] == 'train' and state['final_test_access'] is False,
                'Invalid model fit provenance')
        require(state['calibration_status'] == 'not_calibrated', 'Unexpected calibration state')
        require(type(state['training_rows']) is int and state['training_rows'] > 0
                and type(state['training_events']) is int
                and 0 <= state['training_events'] <= state['training_rows'], 'Invalid training support')
        require(state['prevalence'] == state['training_events'] / state['training_rows'], 'Invalid constant prevalence')
        require(encoder['fit_rows'] == state['training_rows'], 'Encoder fit population mismatch')
        require(set(encoder['numeric']) == set(model.encoder.numeric)
                and set(encoder['categorical']) == set(model.encoder.categorical), 'Encoder feature mismatch')
        names = []
        for field in model.encoder.numeric:
            stats = encoder['numeric'][field]
            require(all(type(stats[k]) in (int, float) and math.isfinite(stats[k]) for k in ('median', 'mean', 'scale'))
                    and stats['scale'] > 0, 'Invalid encoder numeric state')
            names.extend([field, field + '__missing'])
        for field in model.encoder.categorical:
            categories = encoder['categorical'][field]
            require(isinstance(categories, list) and all(isinstance(c, str) for c in categories)
                    and categories[:2] == ['__missing__', '__unseen__']
                    and len(set(categories)) == len(categories), 'Invalid encoder categories')
            names.extend(field + '=' + c for c in categories)
        require(names == encoder['feature_names'], 'Encoder schema order mismatch')
        if model.kind == 'logistic':
            require(len(state['coefficients']) == len(names)
                    and all(type(v) in (int, float) and math.isfinite(v)
                            for v in state['coefficients'] + [state['intercept']]), 'Invalid logistic dimensions/parameters')
        model.state, model.encoder.state = state, encoder
        return model
