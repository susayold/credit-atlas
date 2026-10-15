"""Independent saved-score metrics/bootstrap audit; never read final predictors."""
from pathlib import Path
from collections import defaultdict
from itertools import groupby
import json
import math
from uuid import uuid4
import numpy as np
import pyarrow.parquet as pq
from credit_atlas.workspace import read_json, sha256, write_new

ROOT = Path(__file__).resolve().parents[1]
METRICS = ['roc_auc', 'average_precision', 'brier_score', 'log_loss']
ASSESS = ROOT / 'artifacts/private/bankruptcy-assessment-0e7cb5cc894d'
FINAL = ROOT / 'artifacts/private/bankruptcy-holdout-907870affe8d'
COMPARE = ROOT / 'artifacts/private/bankruptcy-comparison-e3ee221ca493'

def metrics(rows):
    pairs = [(r['probability'], r['source_bankruptcy_label']) for r in rows]
    assert all(math.isfinite(p) and 0 <= p <= 1 and y in (0, 1) for p, y in pairs)
    events = sum(y for _, y in pairs)
    negatives = len(pairs) - events
    assert events and negatives
    below = wins = 0
    for _, block in groupby(sorted(pairs), key=lambda x: x[0]):
        group = list(block); pos = sum(y for _, y in group); neg = len(group)-pos
        wins += pos * below + 0.5 * pos * neg; below += neg
    seen = positives = 0; ap = 0.0
    for _, block in groupby(sorted(pairs, reverse=True), key=lambda x: x[0]):
        group = list(block); pos = sum(y for _, y in group)
        seen += len(group); positives += pos; ap += (pos/events)*(positives/seen)
    eps = float(np.finfo(np.float64).eps)
    losses = [-(y*math.log(max(eps,min(1-eps,p)))+(1-y)*math.log1p(-max(eps,min(1-eps,p)))) for p,y in pairs]
    return {'roc_auc': wins/(events*negatives), 'average_precision': ap,
            'brier_score': math.fsum((p-y)**2 for p,y in pairs)/len(pairs),
            'log_loss': math.fsum(losses)/len(pairs)}

def close(a, b):
    assert math.isclose(a, b, abs_tol=2e-12, rel_tol=2e-12), (a, b)

def point_and_bins(rows, saved):
    assert len(rows) == saved['statements'] and sum(r['source_bankruptcy_label'] for r in rows) == saved['events']
    calculated = metrics(rows)
    for key in METRICS: close(calculated[key], saved[key])
    assert len(saved['reliability_bins']) == 10
    for i, bucket in enumerate(saved['reliability_bins']):
        lo, hi = i/10, (i+1)/10
        selected = [r for r in rows if r['probability'] >= lo and (r['probability'] < hi if i<9 else r['probability'] <= hi)]
        assert bucket['lower'] == lo and bucket['upper'] == hi and bucket['statements'] == len(selected)
        assert bucket['events'] == sum(r['source_bankruptcy_label'] for r in selected)
        if not selected: assert bucket['mean_probability'] is bucket['observed_rate'] is None
        else:
            close(bucket['mean_probability'], math.fsum(r['probability'] for r in selected)/len(selected))
            close(bucket['observed_rate'], bucket['events']/len(selected))
    return calculated

def draws(rows, seed, replicates):
    groups = defaultdict(list)
    for row in rows: groups[row['feature_group_id']].append(row)
    members = [groups[g] for g in sorted(groups)]
    rng = np.random.default_rng(seed)
    for number in range(replicates):
        sample = [row for i in rng.integers(0,len(members),size=len(members)) for row in members[i]]
        if len({r['source_bankruptcy_label'] for r in sample}) == 2:
            yield number, sample

def quantile(values, fraction):
    ordered = sorted(values); location = (len(ordered)-1)*fraction
    lower = int(location); upper = min(lower+1,len(ordered)-1); weight = location-lower
    return ordered[lower]*(1-weight)+ordered[upper]*weight

def run():
    out = ROOT / 'artifacts/private' / ('bankruptcy-saved-metrics-audit-'+uuid4().hex[:12]); out.mkdir()
    ledgers = [ROOT / ('artifacts/private/'+name+'-holdout-access.sqlite') for name in ['bankruptcy','retail']]
    before = {str(p.relative_to(ROOT)):sha256(p) for p in ledgers}
    graph = {}
    for folder, name in [(ASSESS,'assessment-complete.json'),(COMPARE,'comparison-complete.json'),(FINAL,'evaluation-complete.json')]:
        receipt = read_json(folder/name);graph[str((folder/name).relative_to(ROOT))]=sha256(folder/name)
        for filename, expected in receipt['files'].items():
            assert sha256(folder/filename)==expected;graph[str((folder/filename).relative_to(ROOT))]=expected
        for method, expected in receipt['methods'].items():
            p=ROOT/'src/credit_atlas'/(method+'.py');assert sha256(p)==expected;graph[str(p.relative_to(ROOT))]=expected
    validation = pq.read_table(ASSESS/'private-validation-scores.parquet').to_pylist()
    saved_validation = read_json(ASSESS/'validation-metrics.json');points={}
    candidates=list(saved_validation)
    candidate_rows={name:[r for r in validation if r['candidate']==name] for name in candidates}
    reference=candidate_rows[candidates[0]]
    order=[(r['source_row_ordinal'],r['feature_group_id'],r['source_bankruptcy_label']) for r in reference]
    for name, rows in candidate_rows.items():
        assert order==[(r['source_row_ordinal'],r['feature_group_id'],r['source_bankruptcy_label']) for r in rows]
        points[name]=point_and_bins(rows,saved_validation[name])
    final = pq.read_table(FINAL/'private-final-scores.parquet').to_pylist()
    point=point_and_bins(final,read_json(FINAL/'final-metrics.json'))
    assert len(final)==591 and len({r['feature_group_id'] for r in final})==585
    assert not set(r['feature_group_id'] for r in final)&set(r['feature_group_id'] for r in reference)
    settings=read_json(FINAL/'settings.json'); saved_draws=pq.read_table(FINAL/'bootstrap-draws.parquet').to_pylist()
    calculated=[];counts=[]
    for number, sample in draws(final,settings['seed'],settings['replicates']):
        result=metrics(sample);saved=saved_draws[len(calculated)];assert saved['draw']==number
        for name in METRICS:close(result[name],saved[name])
        calculated.append(result);counts.append(len(sample))
    uncertainty=read_json(FINAL/'uncertainty.json');assert len(calculated)==uncertainty['valid_replicates']==1000
    assert min(counts)==uncertainty['min_draw_rows'] and max(counts)==uncertainty['max_draw_rows']
    for name in METRICS:
        interval=uncertainty['intervals'][name];close(point[name],interval['point'])
        close(quantile([v[name] for v in calculated],.025),interval['lower'])
        close(quantile([v[name] for v in calculated],.975),interval['upper'])
    paired=pq.read_table(COMPARE/'paired-replicates.parquet').to_pylist();index={(r['draw'],r['candidate']):r for r in paired}
    assert len(index)==len(paired)==5000
    settings=read_json(COMPARE/'bootstrap-settings.json');valid=0
    score_by_name={name:{r['source_row_ordinal']:r for r in rows} for name,rows in candidate_rows.items()}
    for number,sample in draws(reference,settings['seed'],settings['replicates']):
        valid+=1
        for name in candidates:
            result=metrics([score_by_name[name][r['source_row_ordinal']] for r in sample])
            for key in METRICS:close(result[key],index[(number,name)][key])
    assert valid==1000
    paired_summary=read_json(COMPARE/'uncertainty.json');interval_cells=0
    assert paired_summary['valid_replicates']==valid and paired_summary['validation_rows']==len(reference)
    assert paired_summary['validation_groups']==len({r['feature_group_id'] for r in reference})
    for name in candidates:
        for key in METRICS:
            interval=paired_summary['intervals'][name][key]
            values=[index[(number,name)][key] for number in range(1000)]
            for actual,expected in [(points[name][key],interval['point']),(quantile(values,.025),interval['lower']),(quantile(values,.975),interval['upper'])]:
                close(actual,expected);interval_cells+=1
    for pair,intervals in paired_summary['paired_deltas'].items():
        first,second=pair.split('_minus_')
        assert first in candidates and second in candidates
        for key in METRICS:
            values=[index[(number,first)][key]-index[(number,second)][key] for number in range(1000)]
            interval=intervals[key]
            for actual,expected in [(points[first][key]-points[second][key],interval['point']),(quantile(values,.025),interval['lower']),(quantile(values,.975),interval['upper'])]:
                close(actual,expected);interval_cells+=1
    assert len(paired_summary['paired_deltas'])==10 and interval_cells==180
    assert all(sha256(ROOT/p)==h for p,h in before.items())
    write_new(out/'receipt.json',{'status':'PASS','validation_candidates':len(candidates),'validation_score_rows':len(validation),
        'final_score_rows':len(final),'reliability_bins_checked':60,'final_bootstrap_draws':len(calculated),
        'paired_candidate_draws_checked':len(paired),'metric_draw_cells_checked':24000,
        'paired_point_and_percentile_cells_checked':interval_cells,
        'final_metrics':point,'inputs_sha256':graph,'method_sha256':sha256(Path(__file__)),
        'ledger_sha256_unchanged':before,'final_predictor_reads':False,'model_training':False,'model_inference':False,
        'remaining':'Full freeze/source/split/selection lineage and actual current browser/model-card acceptance remain to audit.'})
    print(out)

if __name__=='__main__':run()
