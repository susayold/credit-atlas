"""Independent weighted-threshold metrics; saved validation scores only, no scoring."""
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import numpy as np
import pyarrow.parquet as pq
from credit_atlas.workspace import sha256,timestamp

METRICS=['roc_auc','average_precision','brier_score','log_loss']

def prepare(y,p):
    y=np.asarray(y,dtype=float);p=np.asarray(p,dtype=float)
    if y.ndim!=1 or p.shape!=y.shape or set(y)!={0.,1.} or not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Binary cohort and finite probabilities required')
    levels,group=np.unique(p,return_inverse=True)
    clipped=np.clip(p,np.finfo(float).eps,1-np.finfo(float).eps)
    return y,p,levels,group,(p-y)**2,-y*np.log(clipped)-(1-y)*np.log1p(-clipped)

def weighted_metrics(prepared,weights=None):
    y,p,levels,group,squared,logs=prepared
    weights=np.ones(len(y)) if weights is None else np.asarray(weights,dtype=float)
    if weights.shape!=y.shape or not np.isfinite(weights).all() or np.any(weights<0):raise ValueError('Finite nonnegative row weights required')
    positive=np.bincount(group,weights=weights*y,minlength=len(levels));negative=np.bincount(group,weights=weights*(1-y),minlength=len(levels))
    P,N=positive.sum(),negative.sum()
    if min(P,N)<=0:raise ValueError('Both classes must have weighted support')
    auc=np.sum(positive*(np.cumsum(negative)-negative+negative/2))/(P*N)
    tp=np.cumsum(positive[::-1]);total=np.cumsum((positive+negative)[::-1])
    precision=np.divide(tp,total,out=np.zeros_like(tp),where=total>0)
    ap=np.dot(positive[::-1],precision)/P
    return np.array([auc,ap,np.dot(weights,squared)/(P+N),np.dot(weights,logs)/(P+N)])

def main():
    root=Path.cwd();out=root/'artifacts/private'/('retail-validation-acceptance-'+uuid4().hex[:12]);out.mkdir()
    (out/'access-start.json').write_text(json.dumps({'started_at':timestamp(),'purpose':'independent_saved_validation_metrics_and_partition_label_audit','reads':['saved_validation_scores','validation_partition_IDs_labels','saved_aggregate_receipts'],'final_test_predictor_reads':0,'final_test_scoring_performed':False,'actual_model_refit_performed':False},indent=2),encoding='utf-8')
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    folder=root/'artifacts/private/retail-assessment-b8b96f471254';assessment=json.loads((folder/'assessment-complete.json').read_text())
    comparison_dir=root/'artifacts/private/retail-comparison-b560ea676127';comparison_receipt=json.loads((comparison_dir/'comparison-complete.json').read_text())
    freeze_dir=root/'artifacts/private/retail-freeze-3dc86f5afe01';freeze=json.loads((freeze_dir/'freeze-complete.json').read_text())
    sources=[]
    for directory,receipt in [(folder,assessment),(comparison_dir,comparison_receipt),(freeze_dir,freeze)]:
        for name,expected in receipt['outputs_sha256'].items():
            file=directory/name;assert sha256(file)==expected;sources.append({'path':str(file.relative_to(root)),'sha256':expected})
    assert comparison_receipt['assessment_receipt_sha256']==freeze['assessment_receipt_sha256']==sha256(folder/'assessment-complete.json')
    assert freeze['comparison_receipt_sha256']==sha256(comparison_dir/'comparison-complete.json')
    records=pq.read_table(folder/'private-validation-scores.parquet').to_pylist()
    arrays={};ids=None;y=None
    for model in ['constant','logistic','boosting']:
        rows=[r for r in records if r['model']==model];keys=[r['source_client_id'] for r in rows];labels=np.array([r['target'] for r in rows])
        assert len(rows)==len(set(keys))==4499
        if ids is None:ids=keys;y=labels
        else:assert keys==ids and np.array_equal(y,labels)
        for variant in ['raw','calibrated']:arrays[model+'/'+variant]=np.array([r[variant+'_probability'] for r in rows])
    assert len(records)==13497 and int(y.sum())==995
    case_dir=root/'artifacts/private/retail-case-470bdb40682f';case=json.loads((case_dir/'case-complete.json').read_text())
    assert sha256(case_dir/'case-complete.json')==freeze['case_receipt_sha256']
    assert sha256(case_dir/'partitions.parquet')==case['outputs_sha256']['partitions.parquet']
    validation_labels=pq.read_table(case_dir/'partitions.parquet',columns=['source_client_id','target'],filters=[('partition','=','validation')]).to_pylist()
    by_id={r['source_client_id']:r['target'] for r in validation_labels}
    assert len(validation_labels)==len(by_id)==4499 and set(by_id)==set(ids)
    assert all(by_id[key]==int(label) for key,label in zip(ids,y))
    metrics=json.loads((folder/'validation-metrics.json').read_text());comparison=json.loads((comparison_dir/'comparison.json').read_text())
    prepared={name:prepare(y,p) for name,p in arrays.items()};points={name:weighted_metrics(v) for name,v in prepared.items()}
    point_checks=0;bin_checks=0;max_error=0.
    def near(actual,expected,tolerance=1e-12):
        nonlocal max_error
        error=abs(float(actual)-float(expected));max_error=max(max_error,error);assert error<=tolerance,(error,tolerance)
    for name,p in arrays.items():
        model,variant=name.split('/');saved=metrics[model][variant]
        for key,value in zip(METRICS,points[name]):near(value,saved[key]);point_checks+=1
        assert saved['loans']==4499 and saved['events']==995
        for i,b in enumerate(saved['reliability_bins']):
            lower,upper=i/10,(i+1)/10;mask=(p>=lower)&((p<upper) if i<9 else (p<=upper));n=int(mask.sum());events=int(y[mask].sum())
            assert b['lower']==lower and b['upper']==upper and b['loans']==n and b['events']==events
            if n:near(b['mean_probability'],p[mask].mean());near(b['observed_rate'],events/n)
            else:assert b['mean_probability'] is None and b['observed_rate'] is None
            bin_checks+=1
    assert comparison['replicates']==1000 and comparison['seed']==676
    rng=np.random.default_rng(676);classes=[np.flatnonzero(y==t) for t in [0,1]]
    draws={name:np.empty((1000,4)) for name in arrays}
    for i in range(1000):
        indices=np.concatenate([rng.choice(g,size=len(g),replace=True) for g in classes]);weights=np.bincount(indices,minlength=len(y))
        assert np.dot(weights,y)==995 and weights.sum()==4499
        for name,v in prepared.items():draws[name][i]=weighted_metrics(v,weights)
    interval_checks=0
    for name,values in draws.items():
        low,high=np.quantile(values,[.025,.975],axis=0)
        for j,key in enumerate(METRICS):
            for field,value in [('point',points[name][j]),('lower',low[j]),('upper',high[j])]:near(value,comparison['absolute_intervals'][name][key][field]);interval_checks+=1
    orientation=np.array([1,1,-1,-1])
    for pair in comparison['paired_improvements']:
        reference,candidate=pair['reference'],pair['candidate'];diff=(draws[candidate]-draws[reference])*orientation
        low,high=np.quantile(diff,[.025,.975],axis=0);point=(points[candidate]-points[reference])*orientation
        for j,key in enumerate(METRICS):
            for field,value in [('point',point[j]),('lower',low[j]),('upper',high[j])]:near(value,pair['metrics'][key][field]);interval_checks+=1
    assert interval_checks==132
    rubric=json.loads((freeze_dir/'rubric.json').read_text());selection=json.loads((freeze_dir/'selection.json').read_text())
    suite=json.loads((root/'artifacts/private/suite-view-74e07524f6d0/snapshot.json').read_text())['retail']
    assert {(r['model'],r['variant']) for r in suite['validation']}=={(m,v) for m in ['constant','logistic','boosting'] for v in ['raw','calibrated']} and len(suite['validation'])==6
    for row in suite['validation']:
        expected=metrics[row['model']][row['variant']]
        assert all(value==expected[key] for key,value in row.items() if key not in {'model','variant'})
    assert suite['paired_improvements']==comparison['paired_improvements'] and suite['selection']==selection and suite['rubric']==rubric
    rawpair=next(p for p in comparison['paired_improvements'] if p['reference']=='logistic/raw' and p['candidate']=='boosting/raw')
    assert points['logistic/raw'][2]<points['constant/raw'][2] and points['logistic/raw'][3]<points['constant/raw'][3]
    assert rawpair['metrics']['brier_score']['point']>=rubric['minimum_boosting_brier_improvement']
    assert all(rawpair['metrics'][k]['lower']>rubric['required_brier_and_log_loss_bootstrap_lower'] for k in ['brier_score','log_loss'])
    assert rawpair['metrics']['roc_auc']['point']>=-rubric['maximum_auc_point_degradation']
    calibrated=next(p for p in comparison['paired_improvements'] if p['reference']=='boosting/raw' and p['candidate']=='boosting/calibrated')
    qualify_calibration=calibrated['metrics']['brier_score']['point']>=rubric['minimum_calibration_brier_improvement'] and all(calibrated['metrics'][k]['lower']>0 for k in ['brier_score','log_loss'])
    assert not qualify_calibration and selection['model']==freeze['selected_model']=='boosting' and selection['variant']==freeze['selected_variant']=='raw'
    assert selection['selection_partition']=='validation' and not selection['qualified_for_production']
    assert rubric['established_after_development_inspection'] and not rubric['confirmatory_preregistered_test']
    assert not assessment['final_test_scored'] and not comparison_receipt['final_test_scored'] and not freeze['final_test_scored']
    holdout_dir=root/'artifacts/private/retail-holdout-061c440ea867'
    evaluation=json.loads((holdout_dir/'evaluation-complete.json').read_text());access=json.loads((holdout_dir/'access-start.json').read_text())
    assert evaluation['freeze_receipt_sha256']==access['freeze_receipt_sha256']==sha256(freeze_dir/'freeze-complete.json')
    assert access['selected_model']==selection['model'] and access['selected_variant']==selection['variant']
    assert not access['model_selection_performed'] and not access['model_training_performed']
    assert datetime.fromisoformat(freeze['frozen_at'])<datetime.fromisoformat(access['started_at'])<datetime.fromisoformat(evaluation['completed_at'])
    for file in [folder/'assessment-complete.json',comparison_dir/'comparison-complete.json',freeze_dir/'freeze-complete.json',case_dir/'case-complete.json',case_dir/'partitions.parquet',root/'artifacts/private/suite-view-74e07524f6d0/snapshot.json',holdout_dir/'evaluation-complete.json',holdout_dir/'access-start.json']:
        sources.append({'path':str(file.relative_to(root)),'sha256':sha256(file)})
    assert sha256(ledger)==before
    result={'status':'PASS','requirement':'P1.03','validation_clients':4499,'events':995,'saved_score_rows':len(records),'variants':6,'point_metric_checks':point_checks,'reliability_bin_checks':bin_checks,'bootstrap_replicates':1000,'interval_value_checks':interval_checks,'max_abs_numeric_error':max_error,'tolerance':1e-12,'validation_partition_ID_label_parity':True,'selection_rule_parity':True,'suite_projection_parity':True,'freeze_before_final_evaluation_receipt':True,'source_inputs':sources,'method_sha256':sha256(Path(__file__)),'ledger_unchanged':True,'final_test_predictor_reads':0,'model_fit_calls':0,'scoring_calls':0}
    (out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'output':str(out),'status':'PASS','metric_checks':point_checks,'interval_checks':interval_checks,'max_error':max_error}))

if __name__=='__main__':main()
