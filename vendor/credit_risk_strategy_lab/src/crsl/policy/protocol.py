"""Exclusive-write development protocol receipts, externally pinned on read.

Local hashes detect changed contents relative to a retained receipt digest.
They are not trusted timestamps, approval signatures or proof of no prior peeking.
"""
import copy
import json
import re
from pathlib import Path

from .engine import ScreeningEngine, amount, day, fingerprint
from .optimize import validation_frontier
from .uncertainty import paired_bootstrap
from .retention import fixed_retention
from ..evidence_checks import require, require_hash
from ..source import sha256, utc_now, write_json_new


def validate_protocol(config):
    required = {'version', 'status', 'policy_config', 'candidate_ids',
        'retention_floors', 'bootstrap', 'selection_partition', 'evaluation_cutoff',
        'split_manifest_sha256', 'model_manifest_sha256', 'code_sha256'}
    require(required <= set(config) <= required | {'retention_candidates'}, 'Unsupported protocol fields')
    require(isinstance(config['version'], str) and bool(config['version']), 'Protocol version required')
    require(config['status'] == 'development', 'Only development protocols supported')
    engine = ScreeningEngine(config['policy_config'])
    retention = config.get('retention_candidates', [])
    require(isinstance(retention, list), 'Retention candidates must be a list')
    retention_ids = set()
    for rule in retention:
        require(isinstance(rule, dict) and set(rule) == {'candidate_id', 'basis', 'target', 'tie_rule'},
                'Unsupported retention rule fields')
        identity = rule['candidate_id']
        require(isinstance(identity, str) and bool(identity) and identity not in engine.policies
                and identity not in retention_ids, 'Duplicate or invalid retention candidate ID')
        retention_ids.add(identity)
        target = amount(rule['target'])
        require(target is not None and 0 <= target <= 1, 'Invalid retention target')
        require(rule['basis'] in ('count', 'principal'), 'Invalid retention basis')
        require(rule['tie_rule'] == 'include_whole_boundary_group', 'Unsupported tie rule')
    require(config['selection_partition'] == 'validation', 'Selection partition must be validation')
    require(day(config['evaluation_cutoff']) is not None, 'Date-only evaluation cutoff required')
    ids = config['candidate_ids']
    require(isinstance(ids, list) and bool(ids) and all(isinstance(i, str) for i in ids), 'Candidate IDs required')
    require(len(set(ids)) == len(ids) and set(ids) <= set(engine.policies) | retention_ids,
            'Invalid candidate menu')
    require(retention_ids <= set(ids), 'Retention rule missing from candidate menu')
    floors = config['retention_floors']
    require(isinstance(floors, list) and bool(floors), 'Retention floors required')
    parsed = [amount(v) for v in floors]
    require(all(v is not None and 0 <= v <= 1 for v in parsed), 'Invalid retention floor')
    require(len(set(parsed)) == len(parsed), 'Duplicate retention floor')
    boot = config['bootstrap']
    require(set(boot) == {'seed', 'resamples', 'confidence', 'minimum_events'}, 'Unsupported bootstrap settings')
    require(type(boot['seed']) is int and boot['seed'] >= 0, 'Invalid seed')
    require(type(boot['resamples']) is int and boot['resamples'] >= 100, 'Invalid resample count')
    require(type(boot['minimum_events']) is int and boot['minimum_events'] > 0, 'Invalid event support')
    confidence = amount(boot['confidence'])
    require(confidence is not None and 0 < confidence < 1, 'Invalid confidence level')
    for key in ('split_manifest_sha256', 'model_manifest_sha256', 'code_sha256'):
        require(isinstance(config[key], str) and re.fullmatch('[0-9a-f]{64}', config[key]), 'SHA256 lineage required')
    return copy.deepcopy(config)


def freeze_protocol(path, config):
    """Create once; never overwrite an earlier receipt, even with identical data."""
    frozen = validate_protocol(config)
    payload = {'schema_version': 1, 'created_at': utc_now(), 'config': frozen,
               'config_sha256': fingerprint(frozen), 'research_approved': False,
               'trusted_timestamp': False}
    write_json_new(Path(path), payload)
    return {'path': str(Path(path).resolve()), 'receipt_sha256': sha256(Path(path)),
            'config_sha256': payload['config_sha256']}


def load_protocol(path, *, expected_receipt_sha256):
    """Digest must come from the previously retained receipt, not this file."""
    path = Path(path)
    require(isinstance(expected_receipt_sha256, str)
            and re.fullmatch('[0-9a-f]{64}', expected_receipt_sha256), 'Pinned receipt SHA256 required')
    require_hash(path, expected_receipt_sha256)
    payload = json.loads(path.read_text(encoding='utf-8'))
    require(payload['schema_version'] == 1 and payload['research_approved'] is False,
            'Unsupported development receipt')
    config = validate_protocol(payload['config'])
    require(fingerprint(config) == payload['config_sha256'], 'Protocol config hash mismatch')
    return config


def compare_locked(path, *, expected_receipt_sha256, candidates, retention_floor,
                   split_manifest_sha256, model_manifest_sha256, code_sha256):
    """Run validation frontier with no caller override of menu/support settings."""
    config = load_protocol(path, expected_receipt_sha256=expected_receipt_sha256)
    for key, actual in (('split_manifest_sha256', split_manifest_sha256),
                        ('model_manifest_sha256', model_manifest_sha256), ('code_sha256', code_sha256)):
        require(actual == config[key], 'Evaluation lineage differs from frozen protocol')
    require(amount(retention_floor) in [amount(v) for v in config['retention_floors']],
            'Retention floor was not predeclared')
    result = validation_frontier(candidates, partition=config['selection_partition'],
        minimum_principal_retention=retention_floor, candidate_ids=config['candidate_ids'],
        minimum_events=config['bootstrap']['minimum_events'])
    result['protocol_receipt_sha256'] = expected_receipt_sha256
    result['research_approved'] = False
    return result


def bootstrap_locked(path, *, expected_receipt_sha256, records, evidence_class):
    """Use receipt settings verbatim; source-integrated score checks remain upstream."""
    config = load_protocol(path, expected_receipt_sha256=expected_receipt_sha256)
    result = paired_bootstrap(records, **config['bootstrap'],
                              evaluation_cutoff=config['evaluation_cutoff'], evidence_class=evidence_class)
    result['protocol_receipt_sha256'] = expected_receipt_sha256
    result['research_approved'] = False
    return result


def retention_locked(path, *, expected_receipt_sha256, candidate_id, records, evidence_class):
    """Apply the frozen target/basis/tie rule without a caller cutoff override."""
    config = load_protocol(path, expected_receipt_sha256=expected_receipt_sha256)
    rule = next((r for r in config.get('retention_candidates', []) if r['candidate_id'] == candidate_id), None)
    require(rule is not None, 'Retention candidate was not predeclared')
    result = fixed_retention(records, target=rule['target'], basis=rule['basis'], evidence_class=evidence_class)
    result.update(candidate_id=candidate_id, protocol_receipt_sha256=expected_receipt_sha256,
                  research_approved=False)
    return result
