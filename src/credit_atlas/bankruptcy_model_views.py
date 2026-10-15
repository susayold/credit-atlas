"""Verified aggregate-only P3 model evidence; no final inference endpoints."""
from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path

from .bankruptcy_holdout import verify_holdout
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'bankruptcy-model-view-[0-9a-f]{12}\Z')
METRICS = ('statements', 'events', 'roc_auc', 'average_precision', 'brier_score', 'log_loss', 'reliability_bins')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in
            ('bankruptcy_model_views', 'bankruptcy_holdout', 'bankruptcy_freeze', 'bankruptcy_assessment', 'workspace')}


def aggregate(root, evaluation_id, identifier):
    folder, evaluated, final_metrics, uncertainty = verify_holdout(root, evaluation_id)
    frozen = read_json(contained(root, 'artifacts/private/' + evaluated['freeze_id'] + '/freeze-complete.json'))
    study = read_json(contained(root, 'artifacts/private/' + evaluated['study_id'] + '/study-complete.json'))
    validation = read_json(contained(root, 'artifacts/private/' + frozen['assessment_id'] + '/validation-metrics.json'))
    protocol = read_json(contained(root, 'artifacts/private/' + evaluated['freeze_id'] + '/protocol.json'))
    contract = read_json(contained(root, 'artifacts/private/' + study['case_id'] + '/contract.json'))
    snapshot = {'view_id': identifier, 'case_id': study['case_id'], 'study_id': study['study_id'],
        'freeze_id': evaluated['freeze_id'], 'evaluation_id': evaluation_id, 'candidate': evaluated['candidate'],
        'horizon_years': study['horizon'], 'support': copy.deepcopy(study['support']),
        'validation': {name: {key: copy.deepcopy(values[key]) for key in METRICS} for name, values in validation.items()},
        'final': {key: copy.deepcopy(final_metrics[key]) for key in METRICS},
        'final_uncertainty': copy.deepcopy(uncertainty),
        'selection_rule': copy.deepcopy(protocol['selection']), 'transform': protocol['transform'],
        'fit_settings': copy.deepcopy(protocol['fixed_models']), 'calibration': copy.deepcopy(protocol['calibration']),
        'target': 'Source bankruptcy classification at one-year horizon; not loan-default PD',
        'final_access_status': 'completed', 'final_prediction_access_in_view': False, 'can_rescore': False,
        'scope': 'source-statement-weighted research benchmark; random exact-group partitions',
        'visibility': 'private', 'public_release_approved': False, 'production_qualified': False,
        'entity_disjointness_verified': False, 'temporal_out_of_time': False,
        'limitations': [*contract['warnings'],
            f"Only {final_metrics['events']} final positives; uncertainty conditional on fixed model/exact groups.",
            'Bootstrap exact groups are not identified firms. No firm-independent/OOT/production claim.',
            'Source retrospective sampling and predictor publication availability limit lending interpretation.',
            'No economic threshold, approval policy, subgroup fairness or monitoring qualification.',
            'Final was consumed once. Views/exports read saved metrics and probabilities, not final predictor inference.'],
        'source': {'url': 'https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data',
                   'attribution': contract['attribution']}}
    return snapshot, sha256(folder / 'evaluation-complete.json')


def build_model_view(root, evaluation_id):
    identifier = 'bankruptcy-model-view-' + uuid.uuid4().hex[:12]
    frozen_methods = methods()
    snapshot, digest = aggregate(root, evaluation_id, identifier)
    folder = contained(root, 'artifacts/private/' + identifier)
    folder.mkdir(parents=True)
    write_new(folder / 'snapshot.json', snapshot)
    confirmed, new_digest = aggregate(root, evaluation_id, identifier)
    if new_digest != digest or confirmed != snapshot or methods() != frozen_methods:
        raise ValueError('Model aggregate lineage changed during snapshot build')
    receipt = {'view_id': identifier, 'evaluation_id': evaluation_id, 'evaluation_receipt_sha256': digest,
        'status': 'VERIFIED_BANKRUPTCY_MODEL_AGGREGATES', 'completed_at': timestamp(), 'methods': frozen_methods,
        'snapshot_sha256': sha256(folder / 'snapshot.json'), 'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'view-complete.json', receipt)
    return receipt


class BankruptcyModelViews:
    def __init__(self, root):
        self.root = root.resolve()
        self.methods = methods()

    def view(self, identifier):
        if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
            raise ValueError('Invalid bankruptcy model-view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier)
        receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_BANKRUPTCY_MODEL_AGGREGATES'
                or receipt['methods'] != self.methods or receipt['methods'] != methods()
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False):
            raise ValueError('Model view method/qualification changed')
        path = folder / 'snapshot.json'
        if sha256(path) != receipt['snapshot_sha256']:
            raise ValueError('Model snapshot bytes changed')
        snapshot = read_json(path)
        expected, digest = aggregate(self.root, receipt['evaluation_id'], identifier)
        if expected != snapshot or digest != receipt['evaluation_receipt_sha256']:
            raise ValueError('Model aggregates differ from saved final/development evidence')
        return snapshot

    def catalog(self):
        results = []
        for path in (self.root / 'artifacts/private').glob('bankruptcy-model-view-*/view-complete.json'):
            try:
                snapshot = self.view(path.parent.name)
                results.append({'view_id': snapshot['view_id'], 'status': 'verified',
                    'completed_at': read_json(path)['completed_at'], 'candidate': snapshot['candidate'],
                    'horizon_years': snapshot['horizon_years'], 'final_statements': snapshot['final']['statements']})
            except (ValueError, OSError, KeyError):
                results.append({'view_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(results, key=lambda row: row['completed_at'], reverse=True)}
