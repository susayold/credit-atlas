"""Apply the prefit selection rubric and freeze one model per original-source study."""
from __future__ import annotations

import math
import re
import shutil
import uuid
from pathlib import Path

from .bankruptcy_assessment import CANDIDATES, verify_assessment
from .bankruptcy_comparison import verify_comparison
from .bankruptcy_study import PROTOCOL, verify_features
from .workspace import contained, read_json, sha256, timestamp, write_new


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in
            ('bankruptcy_freeze', 'bankruptcy_comparison', 'bankruptcy_assessment', 'bankruptcy_study', 'retail_assessment', 'workspace')}


def select_candidate(metrics):
    if set(metrics) != set(CANDIDATES) or any(type(row[key]) not in (int, float) or not math.isfinite(row[key])
            or row[key] < 0 for row in metrics.values() for key in ('brier_score', 'log_loss')):
        raise ValueError('Complete finite validation probability-quality metrics required')
    tolerance = PROTOCOL['selection']['metric_tie_tolerance']
    brier = min(row['brier_score'] for row in metrics.values())
    eligible = [name for name in CANDIDATES if metrics[name]['brier_score'] <= brier+tolerance]
    loss = min(metrics[name]['log_loss'] for name in eligible)
    finalists = [name for name in eligible if metrics[name]['log_loss'] <= loss+tolerance]
    return next(name for name in PROTOCOL['selection']['tie_preference'] if name in finalists)


def freeze_model(root, comparison_id):
    comparison_folder, comparison, summary = verify_comparison(root, comparison_id)
    assessment_folder, assessment, metrics = verify_assessment(root, comparison['assessment_id'])
    feature_folder, _, study_folder, study = verify_features(root, assessment['feature_id'])
    registry = contained(root, 'artifacts/private/bankruptcy-study-registry/' + study['lineage_key'])
    index = registry / 'model-freeze.json'
    if index.exists():
        previous = read_json(index)
        _, frozen = verify_freeze(root, previous['freeze_id'])
        if frozen['comparison_id'] != comparison_id:
            raise ValueError('Study model already frozen; cannot reselect using another comparison')
        return frozen
    candidate = select_candidate(metrics)
    name, variant = candidate.split('_')
    output = contained(root, 'artifacts/private/bankruptcy-freeze-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    frozen_methods = methods()
    provenance = {'freeze_id': output.name, 'study_id': study['study_id'], 'lineage_key': study['lineage_key'],
        'assessment_id': assessment['assessment_id'], 'assessment_receipt_sha256': sha256(assessment_folder / 'assessment-complete.json'),
        'comparison_id': comparison_id, 'comparison_receipt_sha256': sha256(comparison_folder / 'comparison-complete.json'),
        'feature_id': assessment['feature_id'], 'feature_receipt_sha256': sha256(feature_folder / 'features-complete.json'),
        'study_receipt_sha256': sha256(study_folder / 'study-complete.json'), 'candidate': candidate, 'methods': frozen_methods,
        'visibility': 'private', 'public_release_approved': False, 'final_test_scored': False,
        'production_qualified': False, 'temporal_out_of_time': False, 'entity_disjointness_verified': False}
    write_new(output / 'freeze-start.json', {**provenance, 'started_at': timestamp()})
    shutil.copyfile(feature_folder / 'encoder.json', output / 'encoder.json')
    shutil.copyfile(assessment_folder / (name + '-model.json'), output / 'model.json')
    if variant == 'platt':
        shutil.copyfile(assessment_folder / (name + '-platt.json'), output / 'platt.json')
    write_new(output / 'protocol.json', PROTOCOL)
    write_new(output / 'selection.json', {'candidate': candidate, 'rule': PROTOCOL['selection'],
        'validation_metrics': metrics, 'uncertainty_used_as_selection_gate': False,
        'uncertainty_scope': 'paired group intervals are supporting evidence; frozen rubric selects from point metrics',
        'selected_validation_intervals': summary['intervals'][candidate], 'final_test_used_for_selection': False})
    verify_comparison(root, comparison_id)
    if methods() != frozen_methods or sha256(assessment_folder / 'assessment-complete.json') != provenance['assessment_receipt_sha256']:
        raise ValueError('Freeze model/comparison lineage changed')
    receipt = {**provenance, 'status': 'BANKRUPTCY_RESEARCH_MODEL_FROZEN', 'completed_at': timestamp(),
        'champion_selected': True, 'files': {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
    write_new(output / 'freeze-complete.json', receipt)
    write_new(index, {'freeze_id': output.name, 'study_id': study['study_id'], 'lineage_key': study['lineage_key'],
        'freeze_receipt_sha256': sha256(output / 'freeze-complete.json')})
    verify_freeze(root, output.name)
    return receipt


def verify_freeze(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-freeze-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bankruptcy freeze identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'freeze-complete.json')
    if (receipt['freeze_id'] != identifier or receipt['status'] != 'BANKRUPTCY_RESEARCH_MODEL_FROZEN'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private' or receipt['champion_selected'] is not True
            or any(receipt[key] is not False for key in ('public_release_approved', 'final_test_scored', 'production_qualified',
                                                        'temporal_out_of_time', 'entity_disjointness_verified'))):
        raise ValueError('Bankruptcy freeze method/qualification changed')
    comparison_folder, comparison, summary = verify_comparison(root, receipt['comparison_id'])
    assessment_folder, assessment, metrics = verify_assessment(root, receipt['assessment_id'])
    feature_folder, _, study_folder, study = verify_features(root, receipt['feature_id'])
    if (comparison['assessment_id'] != receipt['assessment_id'] or assessment['feature_id'] != receipt['feature_id']
            or study['study_id'] != receipt['study_id'] or study['lineage_key'] != receipt['lineage_key']
            or select_candidate(metrics) != receipt['candidate']):
        raise ValueError('Bankruptcy frozen selection/input lineage changed')
    for source_folder, filename, key in ((comparison_folder, 'comparison-complete.json', 'comparison_receipt_sha256'),
            (assessment_folder, 'assessment-complete.json', 'assessment_receipt_sha256'),
            (feature_folder, 'features-complete.json', 'feature_receipt_sha256'),
            (study_folder, 'study-complete.json', 'study_receipt_sha256')):
        if sha256(source_folder / filename) != receipt[key]:
            raise ValueError('Bankruptcy freeze input receipt changed')
    index = read_json(contained(root, 'artifacts/private/bankruptcy-study-registry/' + receipt['lineage_key'] + '/model-freeze.json'))
    if index != {'freeze_id': identifier, 'study_id': receipt['study_id'], 'lineage_key': receipt['lineage_key'],
                 'freeze_receipt_sha256': sha256(folder / 'freeze-complete.json')}:
        raise ValueError('Bankruptcy authoritative model freeze registry changed')
    name, variant = receipt['candidate'].split('_')
    expected = {'freeze-start.json', 'encoder.json', 'model.json', 'protocol.json', 'selection.json'}
    if variant == 'platt':
        expected.add('platt.json')
    if set(receipt['files']) != expected:
        raise ValueError('Bankruptcy freeze file population changed')
    for filename, digest in receipt['files'].items():
        if sha256(contained(folder, filename)) != digest:
            raise ValueError('Bankruptcy frozen model evidence bytes changed')
    if (sha256(folder / 'encoder.json') != sha256(feature_folder / 'encoder.json')
            or sha256(folder / 'model.json') != sha256(assessment_folder / (name + '-model.json'))
            or variant == 'platt' and sha256(folder / 'platt.json') != sha256(assessment_folder / (name + '-platt.json'))
            or read_json(folder / 'protocol.json') != PROTOCOL):
        raise ValueError('Bankruptcy frozen model/transform differs from selected development model')
    selection = read_json(folder / 'selection.json')
    if (selection['candidate'] != receipt['candidate'] or selection['rule'] != PROTOCOL['selection']
            or selection['validation_metrics'] != metrics or selection['selected_validation_intervals'] != summary['intervals'][receipt['candidate']]
            or selection['final_test_used_for_selection'] is not False):
        raise ValueError('Bankruptcy frozen selection evidence differs')
    return folder, receipt
