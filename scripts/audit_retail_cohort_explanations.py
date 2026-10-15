"""Exhaustive independent tree traversal and24-order contribution verification."""
import argparse
import hashlib
import itertools
import json
import math
import uuid
from pathlib import Path
import duckdb
import numpy as np
from audit_retail_explanations import independent_predict
from credit_atlas.retail_cohort_explanations import verify
from credit_atlas.retail_explanations import guard
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new


def run(root,identifier):
    method={name:sha256(Path(__file__).with_name(name+'.py')) for name in ('audit_retail_cohort_explanations','audit_retail_explanations')}
    ledger=root/'artifacts/private/retail-holdout-access.sqlite'; before=sha256(ledger)
    assert before==read_json(root/'artifacts/private/retail-cohort-explanations-holdout-before-20261010.json')['sha256']
    print('Replaying complete primary cohort study',flush=True)
    folder,receipt,report,saved=verify(root,identifier)
    bundle=root/'artifacts/private'/report['freeze_id']; frozen=read_json(bundle/'freeze-complete.json'); model=read_json(bundle/'model.json'); encoder=read_json(bundle/'encoder.json')
    calibration=read_json(bundle/'calibration.json') if report['selected_variant']=='calibrated' else None
    parent=root/'artifacts/private'/report['explanations_id']; original=read_json(parent/'private-reference-and-coalitions.json'); recipe=read_json(parent/'assumptions.json')
    with duckdb.connect(config={'threads':2,'memory_limit':'256MB'}) as db:
        rows=db.execute("SELECT * FROM read_parquet(?) WHERE partition IN ('train','validation') ORDER BY partition,source_client_id",[str(root/'artifacts/private'/frozen['feature_id']/'development.parquet')]).to_arrow_table().to_pylist()
    train=[r for r in rows if r['partition']=='train']; validation=[r for r in rows if r['partition']=='validation']
    selected=sorted(train,key=lambda r:hashlib.sha256(f"{recipe['background_seed']}:{r['source_client_id']}".encode('ascii')).hexdigest())[:32]
    assert [r['source_client_id'] for r in selected]==original['background_source_ids']
    reference=np.asarray([r['features'] for r in selected]); matrix=np.asarray([r['features'] for r in validation]); predict=lambda x:independent_predict(model,x,calibration)
    baseline=predict(matrix); ranks={index:rank for rank,index in enumerate(sorted(range(len(validation)),key=lambda i:(baseline[i],validation[i]['source_client_id'])),1)}
    columns={'credit_limit':[0],'repayment_status':list(range(13,len(encoder['feature_names']))),'bill_history':list(range(1,7)),'payment_history':list(range(7,13))}
    checks=0; derived=[]
    def equal(a,b):
        nonlocal checks
        assert math.isfinite(float(a)) and math.isclose(float(a),float(b),rel_tol=0,abs_tol=1e-12),(a,b)
        checks+=1
    assert len(saved)==len(validation)==report['records']
    assert [r['source_client_id'] for r in saved]==[r['source_client_id'] for r in validation]
    assert {r['score_rank'] for r in saved}==set(range(1,len(validation)+1));checks+=3
    print('Independent exhaustive coalition audit',flush=True)
    # Smaller audit chunks avoid transient allocations on memory-constrained hosts.
    for start in range(0,len(validation),8):
        current=matrix[start:start+8]; count=len(current)
        game=np.tile(reference,(count,16,1,1))
        for i,x in enumerate(current):
            for mask in range(16):
                for player,fields in enumerate(columns.values()):
                    if mask&(1<<player):game[i,mask,:,fields]=np.repeat(x[fields,None],32,axis=1)
        values=predict(game.reshape(-1,matrix.shape[1])).reshape(count,16,32).mean(axis=2)
        for offset,v in enumerate(values):
            index=start+offset; row=saved[index]; contributions=[[] for _ in range(4)]
            for order in itertools.permutations(range(4)):
                mask=0
                for player in order:
                    next_mask=mask|(1<<player);contributions[player].append(v[next_mask]-v[mask]);mask=next_mask
            result={g:math.fsum(c)/24 for g,c in zip(columns,contributions,strict=True)};derived.append(result)
            for g,c in result.items():equal(row[g],c)
            equal(row['predicted_probability'],baseline[index]);equal(row['reference_probability'],v[0]);equal(row['score_rank'],ranks[index])
            equal(v[0]+math.fsum(result.values()),baseline[index]);equal(row['reconstruction_residual'],0)
            token='client-'+hashlib.sha256(f"{report['explanations_id']}:{validation[index]['source_client_id']}".encode('ascii')).hexdigest()[:24]
            assert row['client_token']==token;checks+=1
        if start%512==0:print(f'Audited {min(start+count,len(validation))}/{len(validation)} clients',flush=True)
    for row in report['global_group_contributions']:
        values=[r[row['group']] for r in derived]
        equal(row['mean_absolute_probability_contribution'],math.fsum(abs(v) for v in values)/len(values))
        equal(row['mean_probability_contribution'],math.fsum(values)/len(values));equal(row['minimum'],min(values));equal(row['maximum'],max(values))
        equal(row['positive_records'],sum(v>0 for v in values));equal(row['negative_records'],sum(v<0 for v in values));equal(row['zero_records'],sum(v==0 for v in values))
    assert not any(report['qualification'].values()) and report['original_example_parity_records']==12 and 'source_client_id' not in json.dumps(report)
    guard(root,receipt['inputs_sha256']); assert sha256(ledger)==before
    assert method=={name:sha256(Path(__file__).with_name(name+'.py')) for name in method}
    output=root/'artifacts/private'/('retail-cohort-explanations-audit-'+uuid.uuid4().hex[:12]+'.json')
    write_new(output,{'status':'PASS','checks':checks,'records':len(saved),'cohort_id':identifier,'completed_at':timestamp(),
                      'methods_sha256':method,'study_receipt_sha256':sha256(folder/'cohort-explanations-complete.json'),
                      'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False})
    return {'status':'PASS','checks':checks,'receipt':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cohort-id',required=True);args=parser.parse_args()
    print(json.dumps(run(app_root(),args.cohort_id),indent=2))
