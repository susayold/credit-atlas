"""Independent exact arithmetic on saved validation-score snapshots."""
import argparse
import json
import uuid
from collections import Counter
from fractions import Fraction
from pathlib import Path
import pyarrow.parquet as pq
from credit_atlas.retail_policy_saved import verify_saved as verify
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new

def run(root,identifier):
    folder,receipt,report=verify(root,identifier); pins=dict(receipt['inputs_sha256'])
    pins[str((folder/'policy-complete.json').relative_to(root))]=sha256(folder/'policy-complete.json')
    for name,digest in receipt['outputs_sha256'].items(): pins[str((folder/name).relative_to(root))]=digest
    def guard():
        assert all(sha256(root/path)==digest for path,digest in pins.items()),'Evidence changed during audit'
    guard(); assumptions=report['assumptions']; assessment=root/'artifacts/private'/report['assessment_id']
    raw=pq.read_table(assessment/'private-validation-scores.parquet').to_pylist()
    rows=[r for r in raw if r['model']==report['selected_model']]; column=report['selected_variant']+'_probability'
    checks=0
    def check(condition):
        nonlocal checks
        assert condition,'Independent policy arithmetic mismatch'; checks+=1
    def fraction(value): return Fraction(int(value['numerator']),int(value['denominator']))
    check(len(rows)==report['records']); check(sum(r['target'] for r in rows)==report['events'])
    for case in report['cases']:
        rule=case['rule']; counts=Counter(); events=Counter(); probabilities=Counter(); expected=Counter(); retrospective=Counter()
        for row in rows:
            p=Fraction(str(row[column])); y=row['target']
            if 'constant_action' in rule: action=rule['constant_action']
            elif p>=Fraction(rule['upper_threshold']): action='decline'
            elif p>=Fraction(rule['lower_threshold']): action='review'
            else: action='accept'
            cost=assumptions['cost_matrix'][action]; zero=Fraction(cost['non_event']); one=Fraction(cost['event'])
            counts[action]+=1; events[action]+=y; probabilities[action]+=p
            expected[action]+=zero+p*(one-zero); retrospective[action]+=one if y else zero
        for bucket in case['actions']:
            a=bucket['action']; n=counts[a]
            check(bucket['records']==n); check(bucket['events']==events[a]); check(bucket['non_events']==n-events[a])
            check(fraction(bucket['action_share'])==Fraction(n,len(rows)))
            check(bucket['event_rate'] is None if not n else fraction(bucket['event_rate'])==Fraction(events[a],n))
            check(bucket['mean_probability'] is None if not n else fraction(bucket['mean_probability'])==probabilities[a]/n)
            check(fraction(bucket['expected_declared_cost'])==expected[a]); check(fraction(bucket['retrospective_cost_proxy'])==retrospective[a])
        check(fraction(case['expected_declared_cost'])==sum(expected.values()))
        check(fraction(case['retrospective_cost_proxy'])==sum(retrospective.values()))
        check(fraction(case['expected_minus_retrospective'])==sum(expected.values())-sum(retrospective.values()))
        capacity=assumptions['review_capacity']; check(case['review_records']==counts['review'])
        check(case['review_capacity_exceeded'] is None if capacity is None else case['review_capacity_exceeded']==(counts['review']>capacity))
        check(case['review_overflow_records'] is None if capacity is None else case['review_overflow_records']==max(0,counts['review']-capacity))
    guard(); before=read_json(root/'artifacts/private/retail-policy-holdout-guard-before-20261010.json')
    check(sha256(root/'artifacts/private/retail-holdout-access.sqlite')==before['retail_holdout_ledger_sha256'])
    check(not any(report['qualification'].values()))
    output=root/'artifacts/private'/('retail-policy-audit-'+uuid.uuid4().hex[:12]+'.json')
    write_new(output,{'status':'PASS','policy_id':identifier,'completed_at':timestamp(),'checks':checks,
        'audit_method_sha256':sha256(Path(__file__)),'evidence_sha256':pins,'holdout_ledger_unchanged':True,
        'scope':'Independent aggregate/cost arithmetic from saved validation scores; no counterfactual or production qualification',
        'visibility':'private','public_release_approved':False})
    return {'status':'PASS','checks':checks,'receipt':str(output)}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--policy-id',required=True);args=parser.parse_args()
    print(json.dumps(run(app_root(),args.policy_id),indent=2))
