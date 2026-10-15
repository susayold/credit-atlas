"""Deterministic S0-S3 funded-loan screening with ordered, auditable reasons."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..evidence_checks import require
from ..source import write_json_new

DECISIONS = ('selected', 'review', 'data_ineligible')
OCCUPANCIES = {'P', 'I', 'S'}
KINDS = {'S0': 'retain_all', 'S1': 'fico_threshold', 'S2': 'pd_threshold', 'S3': 'pd_concentration'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def amount(value):
    if isinstance(value, bool) or value is None or not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def day(value):
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return None


def trace_value(value):
    if isinstance(value, (Decimal, date)):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: trace_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [trace_value(item) for item in value]
    return value


def reason(code, field, actual, expected, passed, stage='data'):
    return {'code': code, 'stage': stage, 'field': field, 'actual': trace_value(actual),
            'expected': trace_value(expected), 'passed': passed}


class ScreeningEngine:
    def __init__(self, config):
        self.config = copy.deepcopy(config)
        require(set(config) == {'version', 'status', 'purpose', 'threshold_basis', 'horizon_months', 'risk_estimand', 'policies'}, 'Unsupported policy configuration fields')
        require(config['threshold_basis'] == 'synthetic_demonstration_not_lender_risk_appetite', 'Threshold basis must remain illustrative until validation')
        require(config.get('purpose') == 'retrospective_funded_loan_screening', 'Unsupported decision purpose')
        require(config.get('status') == 'development_not_selected_on_validation', 'Only development policies supported by this runner')
        require(isinstance(config.get('version'), str) and bool(config['version']), 'Policy version required')
        require(config.get('horizon_months') == 12 and type(config['horizon_months']) is int, 'Unsupported risk horizon')
        require(config.get('risk_estimand') == 'numeric_d3_before_prepayment', 'Unsupported risk estimand')
        self.policies = {}
        for spec in config['policies']:
            policy_id = spec['policy_id']
            require(policy_id in KINDS and spec['kind'] == KINDS[policy_id], 'Unknown policy kind')
            require(policy_id not in self.policies, 'Duplicate policy identifier')
            allowed = {'policy_id', 'kind'}
            if policy_id == 'S1':
                allowed.add('minimum_fico')
                require(type(spec.get('minimum_fico')) is int and 300 <= spec['minimum_fico'] <= 850, 'Invalid FICO cutoff')
            if policy_id in ('S2', 'S3'):
                allowed.add('maximum_pd')
                limit = amount(spec.get('maximum_pd'))
                require(limit is not None and 0 <= limit <= 1, 'Invalid PD cutoff')
            if policy_id == 'S3':
                allowed.add('concentration')
                concentration = spec['concentration']
                require(set(concentration) == {'field', 'maximum_principal_share'}, 'Unsupported concentration fields')
                require(concentration['field'] == 'occupancy', 'Only reviewed occupancy segments supported')
                limits = concentration['maximum_principal_share']
                require(bool(limits) and set(limits) <= OCCUPANCIES, 'Invalid concentration segments')
                require(all(amount(v) is not None and 0 <= amount(v) <= 1 for v in limits.values()), 'Invalid concentration cap')
            require(set(spec) == allowed, 'Unsupported or missing policy parameters')
            self.policies[policy_id] = copy.deepcopy(spec)
        require(bool(self.policies), 'Empty policy menu')
        self.policy_hash = fingerprint(self.config)

    @staticmethod
    def _base(row):
        principal = amount(row.get('original_upb'))
        snapshot, as_of = day(row.get('features_as_of')), day(row.get('as_of'))
        tests = [
            reason('D_NOT_FUNDED', 'funded', row.get('funded'), True, row.get('funded') is True),
            reason('D_COHORT_INELIGIBLE', 'data_eligible', row.get('data_eligible'), True, row.get('data_eligible') is True),
            reason('D_INVALID_PRINCIPAL', 'original_upb', row.get('original_upb'), 'finite > 0 USD', principal is not None and principal > 0),
            reason('D_INVALID_SNAPSHOT_DATE', 'features_as_of', row.get('features_as_of'), 'date <= as_of', snapshot is not None and as_of is not None and snapshot <= as_of),
        ]
        return tests, principal

    def _decision(self, row, policy_id, evidence_class):
        spec = self.policies[policy_id]
        trace, principal = self._base(row)
        failures = [r['code'] for r in trace if not r['passed']]
        result = {'record_id': row['record_id'], 'as_of': str(row['as_of']), 'policy_id': policy_id,
                  'policy_version': self.config['version'], 'policy_sha256': self.policy_hash,
                  'evidence_class': evidence_class, 'decision': 'data_ineligible',
                  'reason_codes': failures, 'trace': trace, 'base_eligible': not failures,
                  'original_upb': None if principal is None else str(principal)}
        if failures:
            return result
        if policy_id == 'S1':
            score = amount(row.get('classic_fico'))
            valid = score is not None and score == score.to_integral_value() and 300 <= score <= 850
            trace.append(reason('D_FICO_MISSING_OR_INVALID', 'classic_fico', row.get('classic_fico'), 'integer 300..850', valid))
            if not valid:
                result['reason_codes'] = ['D_FICO_MISSING_OR_INVALID']
                return result
            passed = score >= spec['minimum_fico']
            trace.append(reason('R_FICO_BELOW_CUTOFF', 'classic_fico', str(score), f">= {spec['minimum_fico']}", passed, 'risk'))
            result.update(decision='selected' if passed else 'review',
                          reason_codes=['S_FICO_AT_OR_ABOVE_CUTOFF' if passed else 'R_FICO_BELOW_CUTOFF'])
            return result
        if policy_id in ('S2', 'S3'):
            if policy_id == 'S3':
                valid = isinstance(row.get('occupancy'), str) and row['occupancy'] in OCCUPANCIES
                trace.append(reason('D_OCCUPANCY_MISSING_OR_INVALID', 'occupancy', row.get('occupancy'), 'P, I or S', valid))
                if not valid:
                    result['reason_codes'] = ['D_OCCUPANCY_MISSING_OR_INVALID']
                    return result
            risk = row.get('risk')
            if risk is None:
                trace.append(reason('R_MODEL_INPUT_UNAVAILABLE', 'risk', None, 'calibrated same-horizon risk record', False, 'model'))
                result.update(decision='review', reason_codes=['R_MODEL_INPUT_UNAVAILABLE'])
                return result
            require(isinstance(risk, dict), 'Risk input must be an object or null')
            probability = amount(risk.get('pd'))
            valid = probability is not None and 0 <= probability <= 1
            trace.append(reason('D_PD_MISSING_OR_INVALID', 'risk.pd', risk.get('pd'), 'finite fraction 0..1', valid))
            if not valid:
                result['reason_codes'] = ['D_PD_MISSING_OR_INVALID']
                return result
            risk_date = day(risk.get('as_of'))
            # Predictions must refer to this exact decision landmark, not an old score.
            checks = [
                ('R_RISK_LANDMARK_MISMATCH', 'as_of', risk_date is not None and risk_date == day(row['as_of']), row['as_of']),
                ('R_RISK_HORIZON_MISMATCH', 'horizon_months', type(risk.get('horizon_months')) is int and risk.get('horizon_months') == self.config['horizon_months'], self.config['horizon_months']),
                ('R_RISK_ESTIMAND_MISMATCH', 'estimand', risk.get('estimand') == self.config['risk_estimand'], self.config['risk_estimand']),
                ('R_MODEL_LINEAGE_UNAVAILABLE', 'model_id', isinstance(risk.get('model_id'), str) and bool(risk['model_id']), 'nonempty model identifier'),
                ('R_CALIBRATION_UNAVAILABLE', 'calibration_id', isinstance(risk.get('calibration_id'), str) and bool(risk['calibration_id']), 'nonempty calibration identifier'),
                ('R_MODEL_NOT_AVAILABLE', 'model_available_at', day(risk.get('model_available_at')) is not None and day(risk['model_available_at']) <= day(row['as_of']), 'date <= decision landmark'),
                ('R_CALIBRATION_NOT_AVAILABLE', 'calibration_available_at', day(risk.get('calibration_available_at')) is not None and day(risk['calibration_available_at']) <= day(row['as_of']), 'date <= decision landmark'),
                ('R_RISK_EVIDENCE_MISMATCH', 'evidence_class', risk.get('evidence_class') == ('synthetic_demo' if evidence_class == 'synthetic_demo' else 'validated_model'), 'same evidence context'),
            ]
            model_failures = []
            for code, field, passed, expected in checks:
                trace.append(reason(code, 'risk.' + field, risk.get(field), expected, passed, 'model'))
                if not passed:
                    model_failures.append(code)
            if model_failures:
                result.update(decision='review', reason_codes=model_failures)
                return result
            passed = probability <= amount(spec['maximum_pd'])
            trace.append(reason('R_PD_ABOVE_CUTOFF', 'risk.pd', str(probability), f"<= {spec['maximum_pd']}", passed, 'risk'))
            result.update(decision='selected' if passed else 'review',
                          reason_codes=['S_PD_AT_OR_BELOW_CUTOFF' if passed else 'R_PD_ABOVE_CUTOFF'])
            return result
        result.update(decision='selected', reason_codes=['S_RETAIN_ALL_ELIGIBLE'])
        return result

    def screen(self, records, policy_id, evidence_class):
        require(policy_id in self.policies, 'Policy not configured')
        require(evidence_class in ('synthetic_demo', 'retrospective_observed'), 'Invalid screening evidence class')
        rows = list(records)
        require(bool(rows), 'Empty screening universe')
        identities = set()
        for row in rows:
            require(isinstance(row.get('record_id'), str) and bool(row['record_id']), 'Stable record identifier required')
            require(day(row.get('as_of')) is not None, 'Valid decision date required')
            key = (row['record_id'], day(row['as_of']))
            require(key not in identities, 'Duplicate record landmark')
            identities.add(key)
        decisions = [self._decision(row, policy_id, evidence_class) for row in rows]
        status = 'evaluated'
        guardrail = []
        if policy_id == 'S3':
            limits = self.policies['S3']['concentration']['maximum_principal_share']
            selected = [(r, d) for r, d in zip(rows, decisions) if d['decision'] == 'selected']
            total = sum((amount(d['original_upb']) for _, d in selected), Decimal(0))
            if total == 0:
                status = 'no_selected_loans'
            else:
                for segment, cap in sorted(limits.items()):
                    segment_total = sum((amount(d['original_upb']) for r, d in selected if r['occupancy'] == segment), Decimal(0))
                    passed = segment_total <= amount(cap) * total
                    guardrail.append({'segment': segment, 'principal': str(segment_total),
                                      'candidate_selected_principal': str(total), 'maximum_share': cap,
                                      'actual_share': str(segment_total / total), 'passed': passed})
                if any(not g['passed'] for g in guardrail):
                    status = 'infeasible_concentration'
                    for _, decision in selected:
                        decision['trace'].append(reason('R_CONCENTRATION_INFEASIBLE', 'candidate_portfolio', guardrail,
                                                        'all configured segment caps satisfied', False, 'portfolio'))
                        decision.update(decision='review', reason_codes=['R_CONCENTRATION_INFEASIBLE'])
        base = [d for d in decisions if d['base_eligible']]
        denominator = sum((amount(d['original_upb']) for d in base), Decimal(0))
        selected_principal = sum((amount(d['original_upb']) for d in decisions if d['decision'] == 'selected'), Decimal(0))
        summary = {'policy_id': policy_id, 'status': status, 'evidence_class': evidence_class,
                   'universe_rows': len(rows), 'base_eligible_rows': len(base),
                   'decision_counts': {name: sum(d['decision'] == name for d in decisions) for name in DECISIONS},
                   'base_eligible_principal': str(denominator), 'selected_principal': str(selected_principal),
                   'principal_retention': str(selected_principal / denominator) if denominator else None,
                   'guardrails': guardrail, 'policy_sha256': self.policy_hash}
        require(sum(summary['decision_counts'].values()) == len(rows), 'Decision partition does not reconcile')
        return {'summary': summary, 'decisions': decisions}


def demo_records():
    rows = []
    examples = [(720, '0.008', 'P', 50000), (680, '0.02', 'I', 90000),
                (640, '0.03', 'P', 80000), (None, '0.012', 'S', 40000),
                (710, None, 'P', 60000), (750, '0.002', 'P', 50000),
                (700, '0.006', 'P', 30000), (760, '0.025', 'P', 45000)]
    for i, (score, pd, occupancy, principal) in enumerate(examples, 1):
        row = {'record_id': f'synthetic-loan-{i:03}', 'as_of': '2020-01-01', 'features_as_of': '2020-01-01',
               'funded': True, 'data_eligible': i != 6, 'original_upb': principal,
               'classic_fico': score, 'occupancy': occupancy, 'risk': None}
        if i == 7:
            row['features_as_of'] = '2020-02-01'
        if pd is not None:
            row['risk'] = {'pd': pd, 'as_of': row['as_of'], 'horizon_months': 12,
                           'estimand': 'numeric_d3_before_prepayment', 'model_id': 'synthetic-model',
                           'calibration_id': 'synthetic-calibration', 'evidence_class': 'synthetic_demo',
                           'model_available_at': '2019-12-31', 'calibration_available_at': '2019-12-31'}
        rows.append(row)
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo'])
    parser.add_argument('--minimum-fico', type=int)
    parser.add_argument('--maximum-pd')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    config = json.loads((root / 'configs/policies.json').read_text())
    if args.minimum_fico is not None or args.maximum_pd is not None:
        for policy in config['policies']:
            if policy['policy_id'] == 'S1' and args.minimum_fico is not None:
                policy['minimum_fico'] = args.minimum_fico
            if policy['policy_id'] in ('S2', 'S3') and args.maximum_pd is not None:
                policy['maximum_pd'] = args.maximum_pd
        config['version'] += '-override-' + fingerprint(config)[:8]
    engine = ScreeningEngine(config)
    output = root / 'artifacts/private' / ('policy-demo-' + uuid.uuid4().hex[:12])
    payload = {'evidence_class': 'synthetic_demo', 'not_real_lending_decisions': True, 'config': config,
               'policies': [engine.screen(demo_records(), key, 'synthetic_demo') for key in engine.policies]}
    write_json_new(output / 'demo.json', payload)
    print(output)
