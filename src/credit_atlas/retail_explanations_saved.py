"""Read previously audited explanation artifacts without model inference."""
import hashlib,itertools,math
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from . import retail_explanations as base
from . import retail_cohort_explanations as cohort
from .retail_subgroups_saved import LEGACY_POLICY_SERVING_SHA256
from .workspace import contained,read_json,sha256

# These certificates were produced by exhaustive independent model/coalition
# audits before serving. Their exact digests, receipt bindings and all study
# inputs/outputs must remain unchanged. New unaudited studies fail closed.
CERTIFICATES={
 'retail-explanations-84b3ac3bab6e':('retail-explanations-audit-d4c7f6227d3d.json','3c41a98f50b523dc4ab8c8c8f55faba8a496c18f30518f6232b14379ac3637a9'),
 'retail-cohort-explanations-02487bb9d1a2':('retail-cohort-explanations-audit-a441ed7a5c48.json','b39e76b683caa4408eeebf524f02266fc681f694064dd71f30e2981e4ea69a9c'),
}

def certificate(root,identifier,receipt_path):
    if identifier not in CERTIFICATES:raise ValueError('Independent explanation audit certificate required')
    name,digest=CERTIFICATES[identifier];path=contained(root,'artifacts/private/'+name)
    if sha256(path)!=digest:raise ValueError('Explanation audit certificate changed')
    proof=read_json(path)
    if proof['status']!='PASS' or proof['study_receipt_sha256']!=sha256(receipt_path) or not proof['holdout_ledger_unchanged']:raise ValueError('Audit/study binding changed')
    methods=proof.get('methods_sha256',{'audit_retail_explanations':proof.get('method_sha256')})
    for name,h in methods.items():
        if name not in {'audit_retail_explanations','audit_retail_cohort_explanations'} or sha256(root/'scripts'/(name+'.py'))!=h:raise ValueError('Independent audit method changed')
    return proof

def certificate_pins(root,identifier):
    name,digest=CERTIFICATES[identifier]
    proof=read_json(contained(root,'artifacts/private/'+name))
    pins={'artifacts/private/'+name:digest}
    for method,h in proof.get('methods_sha256',{'audit_retail_explanations':proof.get('method_sha256')}).items():pins['scripts/'+method+'.py']=h
    return pins

def check_study(root,identifier,receipt_name,status,methods,outputs):
    folder=contained(root,'artifacts/private/'+identifier);path=folder/receipt_name;r=read_json(path)
    certificate(root,identifier,path)
    declared=r.get('methods');legacy={**methods,'retail_policy_views':LEGACY_POLICY_SERVING_SHA256}
    if r.get('schema_version')!=1 or r.get('status')!=status or declared not in (methods,legacy) or r.get('visibility')!='private' or r.get('public_release_approved') is not False or any(r.get(k) is not v for k,v in base.FLAGS.items()):raise ValueError('Saved explanation contract changed')
    if set(r['outputs_sha256'])!=set(outputs):raise ValueError('Complete audited explanation outputs required')
    base.guard(root,r['inputs_sha256']|{str((folder/n).relative_to(root)):h for n,h in r['outputs_sha256'].items()})
    return folder,r

def near(a,b):
    if not math.isfinite(float(a)) or not math.isclose(float(a),float(b),rel_tol=0,abs_tol=1e-12):raise ValueError('Saved contribution arithmetic mismatch')

def verify_base_saved(root,identifier):
    folder,r=check_study(root,identifier,'explanations-complete.json','RETAIL_VALIDATION_EXPLANATIONS_COMPLETE',base.methods(),{'assumptions.json','report.json','private-reference-and-coalitions.json'})
    if r['explanations_id']!=identifier:raise ValueError('Explanation identity changed')
    plan=base.validate(read_json(folder/'assumptions.json'));report=read_json(folder/'report.json');private=read_json(folder/'private-reference-and-coalitions.json')
    if plan!=report['assumptions'] or plan['freeze_id']!=r['freeze_id'] or plan['freeze_id']!=report['freeze_id']:raise ValueError('Explanation scope changed')
    groups=list(report['feature_groups'])
    if len(groups)!=4 or len(private['background_source_ids'])!=32 or len(set(private['background_source_ids']))!=32:raise ValueError('Audited reference/group scope changed')
    locals={x['case']:x for x in report['local_explanations']}
    for row in private['cases']:
        v=row['coalition_probabilities'];local=locals[row['case']]
        if len(v)!=16 or any(not math.isfinite(p) or not 0<=p<=1 for p in v):raise ValueError('Invalid saved coalition values')
        contributions=[[] for _ in range(4)]
        for order in itertools.permutations(range(4)):
            mask=0
            for player in order:
                nxt=mask|(1<<player);contributions[player].append(v[nxt]-v[mask]);mask=nxt
        expected={g:math.fsum(values)/24 for g,values in zip(groups,contributions)}
        for c in local['contributions']:near(c['probability_contribution'],expected[c['group']])
        near(local['reference_probability'],v[0]);near(local['predicted_probability'],v[15]);near(v[0]+math.fsum(expected.values()),v[15])
    return folder,r,report

def verify_cohort_saved(root,identifier):
    folder,r=check_study(root,identifier,'cohort-explanations-complete.json','RETAIL_COMPLETE_VALIDATION_EXPLANATIONS',cohort.methods(),cohort.OUTPUTS)
    if r['cohort_id']!=identifier:raise ValueError('Cohort identity changed')
    plan=cohort.validate(read_json(folder/'assumptions.json'));report=read_json(folder/'report.json')
    _,_,parent=verify_base_saved(root,plan['explanations_id'])
    if plan!=report['assumptions'] or any(report[k]!=plan[k] for k in ['freeze_id','explanations_id']):raise ValueError('Cohort scope changed')
    rows=pq.read_table(folder/'private-client-explanations.parquet').to_pylist();groups=list(report['feature_groups'])
    frozen=read_json(contained(root,'artifacts/private/'+plan['freeze_id'])/'freeze-complete.json')
    scores=pq.read_table(contained(root,'artifacts/private/'+frozen['assessment_id'])/'private-validation-scores.parquet').to_pylist()
    scores={x['source_client_id']:x for x in scores if x['model']==report['selected_model']}
    if len(rows)!=report['records'] or len({x['source_client_id'] for x in rows})!=len(rows) or set(scores)!={x['source_client_id'] for x in rows}:raise ValueError('Saved explanation validation population changed')
    ranks={key:i for i,key in enumerate(sorted(scores,key=lambda k:(scores[k][report['selected_variant']+'_probability'],k)),1)}
    for row in rows:
        key=row['source_client_id'];near(row['predicted_probability'],scores[key][report['selected_variant']+'_probability'])
        token='client-'+hashlib.sha256(f"{plan['explanations_id']}:{key}".encode('ascii')).hexdigest()[:24]
        if row['client_token']!=token or row['score_rank']!=ranks[key]:raise ValueError('Saved token/rank scope changed')
        near(row['reference_probability']+math.fsum(row[g] for g in groups),row['predicted_probability']);near(row['reconstruction_residual'],0)
    if len({x['client_token'] for x in rows})!=len(rows):raise ValueError('Duplicate private client token')
    for summary in report['global_group_contributions']:
        values=np.array([row[summary['group']] for row in rows])
        for key,value in [('mean_absolute_probability_contribution',np.abs(values).mean()),('mean_probability_contribution',values.mean()),('minimum',values.min()),('maximum',values.max())]:near(summary[key],value)
        if summary['records']!=len(rows) or summary['positive_records']!=int((values>0).sum()) or summary['negative_records']!=int((values<0).sum()) or summary['zero_records']!=int((values==0).sum()):raise ValueError('Global contribution population changed')
    by_rank={row['score_rank']:row for row in rows}
    for local in parent['local_explanations']:
        row=by_rank[local['selection_score_rank']];near(row['predicted_probability'],local['predicted_probability']);near(row['reference_probability'],local['reference_probability'])
        for c in local['contributions']:near(row[c['group']],c['probability_contribution'])
    return folder,r,report,rows
