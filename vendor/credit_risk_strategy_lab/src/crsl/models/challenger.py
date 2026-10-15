"""Bounded histogram boosting component with shared baseline data contracts."""
import copy
import math
import json
from pathlib import Path

from .baseline import Baseline, training_rows, scoring_rows, sigmoid
from ..features import OriginationEncoder
from ..evidence_checks import require
from ..policy.engine import day, fingerprint
from ..evidence_checks import require_hash
from ..source import sha256, write_json_new


class BoostingChallenger:
    def __init__(self, feature_config, parameters):
        require(set(parameters) == {'learning_rate', 'max_iter', 'max_leaf_nodes',
            'min_samples_leaf', 'l2_regularization', 'random_state'}, 'Unsupported boosting parameters')
        for name, lower, upper in (('max_iter',1,500),('max_leaf_nodes',2,63),
                                   ('min_samples_leaf',2,1000),('random_state',0,2**32-1)):
            require(type(parameters[name]) is int and lower <= parameters[name] <= upper,
                    'Invalid bounded boosting parameter: ' + name)
        for name in ('learning_rate','l2_regularization'):
            require(type(parameters[name]) in (int,float) and math.isfinite(parameters[name]), 'Finite boosting parameter required')
        require(0 < parameters['learning_rate'] <= 1 and parameters['l2_regularization'] >= 0,
                'Invalid learning rate or regularization')
        self.parameters = copy.deepcopy(parameters)
        self.feature_config = copy.deepcopy(feature_config)
        self.encoder = OriginationEncoder(feature_config)
        self.estimator = self.state = None

    def fit(self, records, *, fit_cutoff, evidence_class):
        require(self.state is None, 'Create a new challenger for each fit')
        require(evidence_class in ('synthetic_demo','retrospective_development'), 'Explicit challenger evidence required')
        rows = training_rows(records, fit_cutoff)
        targets = [r['target'] for r in rows]
        require(set(targets) == {0,1}, 'Challenger requires both training classes')
        self.encoder.fit(rows)
        import numpy as np
        import sklearn
        from sklearn.ensemble import HistGradientBoostingClassifier
        from threadpoolctl import threadpool_limits
        matrix = np.asarray(self.encoder.transform(rows), dtype=float)
        require(matrix.ndim == 2 and matrix.shape[1] > 0 and np.isfinite(matrix).all(), 'Invalid challenger matrix')
        estimator = HistGradientBoostingClassifier(**self.parameters, loss='log_loss',
            early_stopping=False, validation_fraction=None, categorical_features=None,
            class_weight=None, warm_start=False)
        with threadpool_limits(limits=1):
            estimator.fit(matrix, targets)
        require(estimator.do_early_stopping_ is False and len(estimator.validation_score_) == 0,
                'Unexpected internal validation split')
        require(estimator.n_iter_ == self.parameters['max_iter'], 'Unexpected boosting iteration count')
        require(sklearn.__version__ == '1.8.0', 'Tree JSON exporter requires reviewed sklearn 1.8.0')
        trees = []
        for iteration in estimator._predictors:
            require(len(iteration) == 1, 'Binary numeric tree export only')
            nodes = []
            for node in iteration[0].nodes:
                require(not node['is_categorical'], 'Categorical tree export not supported')
                nodes.append(dict(value=float(node['value']), feature=int(node['feature_idx']),
                    threshold=float(node['num_threshold']), left=int(node['left']), right=int(node['right']),
                    is_leaf=bool(node['is_leaf'])))
            trees.append(nodes)
        self.estimator = estimator
        self.state = dict(kind='histogram_gradient_boosting', parameters=self.parameters,
            parameter_sha256=fingerprint(self.parameters), fit_cutoff=str(day(fit_cutoff)),
            training_rows=len(rows), training_events=sum(targets), evidence_class=evidence_class,
            sklearn_version=sklearn.__version__, actual_iterations=int(estimator.n_iter_),
            internal_random_validation=False, calibrated=False, final_test_access=False,
            research_ready=False, persistence_implemented=True,
            initial_raw_score=float(estimator._baseline_prediction[0,0]), trees=trees)
        self._validate_trees()
        with threadpool_limits(limits=1):
            native = estimator.predict_proba(matrix)[:,1].tolist()
        exported = self.predict(rows)
        require(max(abs(a-b) for a,b in zip(native,exported,strict=True)) <= 1e-12,
                'Exported tree scoring differs from training library')
        return self

    def predict(self, records):
        require(self.state is not None, 'Fit challenger first')
        rows = scoring_rows(records)
        for row in rows:
            if row['partition'] != 'train':
                landmark = day(row.get('landmark'))
                require(landmark is not None and landmark >= day(self.state['fit_cutoff']),
                        'Scoring precedes challenger fit cutoff')
        if not rows:
            return []
        probabilities = []
        for vector in self.encoder.transform(rows):
            raw = self.state['initial_raw_score']
            for tree in self.state['trees']:
                index = 0
                while not tree[index]['is_leaf']:
                    node = tree[index]
                    index = node['left'] if vector[node['feature']] <= node['threshold'] else node['right']
                # Histogram predictor leaf values already include learning rate.
                raw += tree[index]['value']
            probabilities.append(sigmoid(raw))
        require(all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities), 'Invalid challenger probabilities')
        return probabilities

    def _validate_trees(self):
        state = self.state
        require(type(state['initial_raw_score']) in (int,float) and math.isfinite(state['initial_raw_score']), 'Invalid initial score')
        require(isinstance(state['trees'],list) and len(state['trees']) == self.parameters['max_iter'], 'Tree count mismatch')
        for tree in state['trees']:
            require(isinstance(tree,list) and 1 <= len(tree) <= 2*self.parameters['max_leaf_nodes']-1, 'Invalid tree size')
            visited, pending = set(), [0]
            while pending:
                index = pending.pop()
                require(type(index) is int and 0 <= index < len(tree) and index not in visited, 'Invalid tree graph')
                visited.add(index)
                node = tree[index]
                require(set(node) == {'value','feature','threshold','left','right','is_leaf'}, 'Unknown tree fields')
                require(type(node['is_leaf']) is bool and all(type(node[k]) in (int,float)
                    and math.isfinite(node[k]) for k in ('value','threshold')), 'Invalid tree values')
                if not node['is_leaf']:
                    require(type(node['feature']) is int and 0 <= node['feature'] < len(self.encoder.state['feature_names']), 'Invalid tree feature')
                    pending.extend([node['left'],node['right']])
            require(len(visited) == len(tree), 'Unreachable tree nodes')

    def to_payload(self):
        require(self.state is not None, 'Cannot save unfitted challenger')
        return copy.deepcopy(dict(schema_version=1, feature_config=self.feature_config,
                                  encoder=self.encoder.state, model=self.state))

    def save(self, path):
        write_json_new(Path(path), self.to_payload())
        return sha256(Path(path))

    @classmethod
    def load(cls, path, *, expected_sha256):
        require_hash(Path(path), expected_sha256)
        return cls.from_payload(json.loads(Path(path).read_text(encoding='utf-8')))

    @classmethod
    def from_payload(cls, payload):
        require(payload['schema_version'] == 1, 'Unsupported challenger schema')
        state = copy.deepcopy(payload['model'])
        require(state['kind'] == 'histogram_gradient_boosting' and state['sklearn_version'] == '1.8.0', 'Unsupported tree exporter version')
        require(state['internal_random_validation'] is False and state['final_test_access'] is False
                and state['research_ready'] is False and state['calibrated'] is False, 'Invalid challenger provenance')
        require(day(state['fit_cutoff']) is not None and state['evidence_class'] in ('synthetic_demo','retrospective_development'), 'Invalid fit context')
        model = cls(payload['feature_config'], state['parameters'])
        require(fingerprint(model.parameters) == state['parameter_sha256'] and state['actual_iterations'] == model.parameters['max_iter'], 'Parameter state mismatch')
        # Reuse the validated common encoder JSON codec through a constant
        # scoring payload. This neither fits nor creates a baseline artifact.
        require(type(state['training_rows']) is int and state['training_rows'] > 0
                and type(state['training_events']) is int and 0 < state['training_events'] < state['training_rows'], 'Invalid training support')
        encoder_codec = Baseline.from_payload(dict(schema_version=1, feature_config=payload['feature_config'],
            encoder=payload['encoder'], model=dict(kind='constant', C=1, training_rows=state['training_rows'],
                training_events=state['training_events'], prevalence=state['training_events']/state['training_rows'],
                final_test_access=False, calibration_status='not_calibrated')))
        model.encoder, model.state = encoder_codec.encoder, state
        model._validate_trees()
        return model
