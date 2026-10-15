"""Private common-cohort builder for existing S0/S1 descriptive decisions."""
import argparse
import json
import uuid
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .engine import amount, day
from ..evidence_checks import require, require_hash
from ..source import sha256, utc_now, write_json_new


def _index(rows, key):
    result = {}
    for row in rows:
        identity = row.get(key)
        require(isinstance(identity, str) and identity and identity not in result, 'Missing or duplicate loan key')
        result[identity] = row
    return result


def common_cohort(labels, baseline, candidate, *, evaluation_cutoff):
    cutoff = day(evaluation_cutoff)
    require(cutoff is not None, 'Date-only cutoff required')
    source, base, alternative = _index(labels, 'loan_id'), _index(baseline, 'record_id'), _index(candidate, 'record_id')
    require(bool(source) and source.keys() == base.keys() == alternative.keys(), 'Decision universe differs from labels')
    included = []
    exclusions = Counter()
    for identity, label in sorted(source.items()):
        b, c = base[identity], alternative[identity]
        require(day(b['as_of']) == day(c['as_of']) == day(label['landmark']) is not None,
                'Decision landmark differs from label')
        eligible = label['eligibility_reason'] == 'eligible'
        require(type(b['base_eligible']) is bool and type(c['base_eligible']) is bool
                and b['base_eligible'] == c['base_eligible'] == eligible, 'Common base eligibility differs')
        for record in (b, c):
            require(record['decision'] in ('selected', 'review', 'data_ineligible'), 'Invalid decision state')
            require(amount(record['original_upb']) == amount(label['original_upb']), 'Principal differs across sources')
        require(b['decision'] == ('selected' if eligible else 'data_ineligible'), 'S0 baseline does not reconcile')
        if not eligible:
            exclusions['entry_ineligible'] += 1
            continue
        target = label['target']
        if target is None:
            exclusions['endpoint_unavailable'] += 1
            continue
        require(type(target) is int and target in (0, 1), 'Invalid binary endpoint')
        known = day(label['label_known_month'])
        require(known is not None and day(label['landmark']) <= known, 'Invalid endpoint availability')
        if known >= cutoff:
            exclusions['not_known_before_cutoff'] += 1
            continue
        principal = amount(label['original_upb'])
        require(principal is not None and principal > 0, 'Invalid comparison principal')
        included.append(dict(loan_id=identity, landmark=str(day(label['landmark'])),
            label_known_at=str(known), principal=str(principal), target=target,
            horizon_months=12, estimand='numeric_d3_before_prepayment',
            baseline_selected=True, candidate_selected=c['decision'] == 'selected'))
    require(len(included) + sum(exclusions.values()) == len(source), 'Attrition does not reconcile')
    return included, {'input_loans': len(source), 'included_loans': len(included),
                      'exclusions': dict(sorted(exclusions.items())), 'evaluation_cutoff': str(cutoff)}


def run(root, label_run, replay_run, *, evaluation_cutoff):
    labels_manifest = json.loads((label_run / 'run-complete.json').read_text())
    replay_manifest = json.loads((replay_run / 'run-complete.json').read_text())
    require(labels_manifest['status'] == 'LABELS_DEVELOPMENT_COMPLETE', 'Completed labels required')
    contract = labels_manifest['config']
    require(contract['horizon_months'] == 12 and contract['landmark'] == 'first_observed_month'
            and contract['endpoint'] == 'numeric_delinquency_03_through_99'
            and contract['prepayment_estimand'] == 'event_before_prepayment',
            'Comparison requires the documented 12-month origination endpoint')
    require(replay_manifest['status'] == 'POLICY_DESCRIPTIVE_REPLAY_COMPLETE', 'Completed descriptive replay required')
    require(replay_manifest['label_run'] == label_run.name, 'Mixed label lineage')
    label_path = label_run / 'labels.parquet'
    require_hash(label_path, labels_manifest['outputs_sha256']['labels.parquet'])
    require_hash(label_path, replay_manifest['inputs_sha256']['labels'])
    decisions = []
    for policy in ('S0', 'S1'):
        path = replay_run / f'{policy}-decisions.parquet'
        require_hash(path, replay_manifest['outputs_sha256'][path.name])
        records = pq.read_table(path).to_pylist()
        require(all(r['policy_id'] == policy and r['policy_sha256'] == replay_manifest['policy_sha256']
                    for r in records), 'Decision policy lineage differs')
        decisions.append(records)
    rows, attrition = common_cohort(pq.read_table(label_path).to_pylist(), *decisions,
                                  evaluation_cutoff=evaluation_cutoff)
    require(bool(rows), 'No endpoint-available comparison cohort')
    output = root / 'artifacts/private' / ('policy-cohort-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    manifest = dict(started_at=utc_now(), label_run=label_run.name, replay_run=replay_run.name,
        inputs_sha256={'label_receipt': sha256(label_run / 'run-complete.json'),
                       'replay_receipt': sha256(replay_run / 'run-complete.json')},
        research_ready=False, policy_selection_performed=False, visibility='private',
        strict_historical_publication_pit=False, evidence_class='retrospective_observed')
    write_json_new(output / 'run-start.json', manifest)
    pq.write_table(pa.Table.from_pylist(rows), output / 'comparison.parquet', compression='zstd')
    write_json_new(output / 'attrition.json', attrition)
    manifest.update(status='DESCRIPTIVE_COMPARISON_COHORT_COMPLETE', completed_at=utc_now(),
        outputs_sha256={name: sha256(output / name) for name in ('comparison.parquet', 'attrition.json')})
    write_json_new(output / 'run-complete.json', manifest)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label-run', type=Path, required=True)
    parser.add_argument('--replay-run', type=Path, required=True)
    parser.add_argument('--evaluation-cutoff', required=True)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[3], args.label_run.resolve(), args.replay_run.resolve(),
              evaluation_cutoff=args.evaluation_cutoff))
