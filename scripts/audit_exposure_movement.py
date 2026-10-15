"""Independent original-CSV Fraction reconciliation of snapshot bridge."""
import argparse
import csv
import json
import uuid
from fractions import Fraction
from pathlib import Path

from credit_atlas.exposure_movements import guard, verify
from credit_atlas.workspace import app_root, contained, sha256, timestamp, write_new


def audit(root, identifier):
    folder,receipt,report=verify(root,identifier); pins={**receipt['inputs_sha256'],
        str((folder/'report.json').relative_to(root)):receipt['report_sha256'],
        str((folder/'movement-complete.json').relative_to(root)):sha256(folder/'movement-complete.json')}
    sources=[]
    for key in ('opening_import_id','closing_import_id'):
        path=contained(root,'artifacts/private/'+receipt[key]+'/source.csv')
        with path.open(encoding='utf-8-sig',newline='') as stream:
            rows={r['position_id']:r for r in csv.DictReader(stream)}
        for row in rows.values(): row['amount']=Fraction(row['reported_amount'])*{'major':1,'thousand':1000,'million':1000000}[row['amount_unit']]
        sources.append(rows)
    a,b=sources; checks=[]
    def check(name, actual, expected): checks.append({'name':name,'passed':actual==expected})
    shared=a.keys() & b.keys(); same={k for k in shared if a[k]['currency']==b[k]['currency']}; migrate=shared-same
    check('independent_identity_partition',report['identity_counts'],{'opening_only':len(a.keys()-b.keys()),
        'closing_only':len(b.keys()-a.keys()),'matched_same_currency':len(same),'matched_currency_migration':len(migrate)})
    check('opening_count',report['opening_records'],len(a)); check('closing_count',report['closing_records'],len(b))
    for group in report['currencies']+report['groups']:
        c=group['currency']; dim=group.get('dimension'); bucket=group.get('bucket')
        def includes(row): return row['currency']==c and (dim is None or row[dim]==bucket)
        opening=sum((r['amount'] for r in a.values() if includes(r)),Fraction(0))
        closing=sum((r['amount'] for r in b.values() if includes(r)),Fraction(0))
        removed=sum((a[k]['amount'] for k in a.keys()-same if includes(a[k])),Fraction(0))
        added=sum((b[k]['amount'] for k in b.keys()-same if includes(b[k])),Fraction(0))
        delta=sum((b[k]['amount']-a[k]['amount'] for k in same if includes(a[k])),Fraction(0))
        incoming=sum((b[k]['amount'] for k in same if dim and includes(b[k]) and not includes(a[k])),Fraction(0))
        outgoing=sum((b[k]['amount'] for k in same if dim and includes(a[k]) and not includes(b[k])),Fraction(0))
        expected={'opening_amount':opening,'closing_amount':closing,'removed_amount':removed,'added_amount':added,
            'continuing_amount_change':delta,'transfer_in':incoming,'transfer_out':outgoing,
            'residual':closing-(opening-removed+delta+incoming-outgoing+added)}
        for key,value in expected.items(): check(':'.join([c,dim or 'TOTAL',bucket or 'ALL',key]),Fraction(group[key]),value)
        if dim is None:
            for key,keys,mapping in [('opening_records',a.keys(),a),('closing_records',b.keys(),b),
                ('removed_records',a.keys()-same,a),('added_records',b.keys()-same,b),('continuing_records',same,a),
                ('currency_migration_out_records',migrate,a),('currency_migration_in_records',migrate,b)]:
                check(c+':'+key,group[key],sum(includes(mapping[k]) for k in keys))
    expected_groups={(r['currency'],d,r[d]) for mapping in (a,b) for r in mapping.values() for d in ('region','segment','source_state','representation')}
    check('full_group_keyset',{(r['currency'],r['dimension'],r['bucket']) for r in report['groups']},expected_groups)
    expected_transitions={}
    for k in same:
        for d in ('region','segment','source_state','representation'):
            if a[k][d]!=b[k][d]:
                key=(a[k]['currency'],d,a[k][d],b[k][d]); n,v=expected_transitions.get(key,(0,Fraction(0)))
                expected_transitions[key]=(n+1,v+b[k]['amount'])
    actual_transitions={(r['currency'],r['dimension'],r['from_bucket'],r['to_bucket']):(r['records'],Fraction(r['closing_amount_transferred'])) for r in report['transitions']}
    check('transition_counts_and_closing_amounts',actual_transitions,expected_transitions)
    guard(root,pins)
    audit_id='exposure-movement-audit-'+uuid.uuid4().hex[:12]
    result={'audit_id':audit_id,'movement_id':identifier,'status':'PASS' if all(r['passed'] for r in checks) else 'FAIL',
        'checks':checks,'completed_at':timestamp(),'script_sha256':sha256(Path(__file__)),
        'movement_receipt_sha256':pins[str((folder/'movement-complete.json').relative_to(root))],
        'visibility':'private','public_release_approved':False}
    write_new(contained(root,'artifacts/private/'+audit_id+'/audit-complete.json'),result)
    if result['status']!='PASS': raise ValueError('Independent movement audit failed')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--movement-id',required=True)
    result=audit(app_root(),parser.parse_args().movement_id)
    print(json.dumps({'audit_id':result['audit_id'],'status':result['status'],'checks':len(result['checks'])}))
