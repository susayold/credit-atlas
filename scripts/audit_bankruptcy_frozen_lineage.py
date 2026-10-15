"""Hash/metadata/selection audit; no final predictors or model inference."""
from collections import Counter, defaultdict
import hashlib
import sqlite3
from pathlib import Path
from uuid import uuid4
import pyarrow.parquet as pq
from credit_atlas.workspace import read_json, sha256, write_new

ROOT = Path(__file__).resolve().parents[1]
ids = {'case':'bankruptcy-case-e1e67482a2b4','study':'bankruptcy-study-e0c65ad465e3',
       'features':'bankruptcy-features-fc51ea164f93','assessment':'bankruptcy-assessment-0e7cb5cc894d',
       'comparison':'bankruptcy-comparison-e3ee221ca493','freeze':'bankruptcy-freeze-cebc982ca176',
       'evaluation':'bankruptcy-holdout-907870affe8d'}
names = dict(zip(ids,['bankruptcy-complete.json','study-complete.json','features-complete.json',
                    'assessment-complete.json','comparison-complete.json','freeze-complete.json','evaluation-complete.json']))
graph = {}
def keep(path, expected=None):
    actual = sha256(path)
    if expected is not None: assert actual == expected, path.name
    graph[str(path.relative_to(ROOT))] = actual
    return actual

ledgers = [ROOT/('artifacts/private/'+n+'-holdout-access.sqlite') for n in ['bankruptcy','retail']]
before = {str(p.relative_to(ROOT)):sha256(p) for p in ledgers}
receipts = {}
for role, identifier in ids.items():
    folder=ROOT/'artifacts/private'/identifier;p=folder/names[role];keep(p);r=read_json(p);receipts[role]=r
    files = r['files']
    entries = files.items() if isinstance(files,dict) else [(x['file'],x['sha256']) for x in files]
    for filename,digest in entries: keep(folder/filename,digest)
    for name,digest in r['methods'].items():keep(ROOT/'src/credit_atlas'/(name if name.endswith('.py') else name+'.py'),digest)
case,study,features,assessment,comparison,freeze,evaluation = [receipts[k] for k in ids]
for child,parent,key in [('study','case','case_receipt_sha256'),('features','study','study_receipt_sha256'),
                         ('assessment','features','feature_receipt_sha256'),('assessment','study','study_receipt_sha256'),
                         ('comparison','assessment','assessment_receipt_sha256'),('freeze','assessment','assessment_receipt_sha256'),
                         ('freeze','comparison','comparison_receipt_sha256'),('freeze','features','feature_receipt_sha256'),
                         ('freeze','study','study_receipt_sha256'),('evaluation','freeze','freeze_receipt_sha256')]:
    keep(ROOT/'artifacts/private'/ids[parent]/names[parent],receipts[child][key])
reference=ROOT/'data/private'/case['reference_id'];keep(reference/'receipt.json',case['reference_receipt_sha256'])
ref=read_json(reference/'receipt.json');assert ref==case['reference'];keep(reference/ref['file'],ref['sha256'])
source=ROOT/'data/private/public-suite'/case['suite_id'];keep(source/'acquisition-complete.json',case['source_receipt_sha256'])
batch=read_json(source/'acquisition-complete.json')
for item in case['sources']:
    assert item in batch['sources']
    keep(source/(item['source_id']+'-receipt.json'));assert read_json(source/(item['source_id']+'-receipt.json'))==item
    keep(source/item['file'],item['sha256'])
contract=read_json(ROOT/'artifacts/private'/ids['case']/'contract.json')
assert contract['horizon_mapping']=={'1':5,'2':4,'3':3,'4':2,'5':1}
assert not contract['pool_horizons_allowed'] and not contract['bankruptcy_is_loan_default']
assert study['horizon']==1 and study['rows']==5910
lineage=hashlib.sha256(('UCI365:original-arff:'+ref['sha256']+':horizon:1').encode()).hexdigest()
assert study['lineage_key']==freeze['lineage_key']==evaluation['lineage_key']==lineage
partition_path=ROOT/'artifacts/private'/ids['study']/'partitions.parquet'
rows=pq.read_table(partition_path,columns=['source_row_ordinal','feature_group_id','partition','source_bankruptcy_label']).to_pylist()
assert len(rows)==len({r['source_row_ordinal'] for r in rows})==5910
group_roles=defaultdict(set)
for r in rows:group_roles[r['feature_group_id']].add(r['partition'])
assert all(len(roles)==1 for roles in group_roles.values()) and len(group_roles)==5850
for role,support in study['support'].items():
    selected=[r for r in rows if r['partition']==role]
    assert len(selected)==support['rows'] and sum(r['source_bankruptcy_label'] for r in selected)==support['positive']
    assert len(selected)-support['positive']==support['negative']
    assert len({r['feature_group_id'] for r in selected})==support['exact_feature_groups']
assert assessment['support']==study['support']
assert features['coverage']['development_rows']==5319 and features['coverage']['dimension']==128
protocol=read_json(ROOT/'artifacts/private'/ids['freeze']/'protocol.json')
assert protocol['features']==protocol['missing_indicators']==['A'+str(i) for i in range(1,65)]
assert not protocol['pool_horizons'] and not protocol['temporal_out_of_time'] and not protocol['entity_disjointness_verified']
selection=read_json(ROOT/'artifacts/private'/ids['freeze']/'selection.json')
metrics=read_json(ROOT/'artifacts/private'/ids['assessment']/'validation-metrics.json')
assert selection['validation_metrics']==metrics and selection['rule']==protocol['selection']
tolerance=protocol['selection']['metric_tie_tolerance'];best=min(m['brier_score'] for m in metrics.values())
eligible=[n for n in protocol['selection']['candidates'] if metrics[n]['brier_score']<=best+tolerance]
loss=min(metrics[n]['log_loss'] for n in eligible);finalists=[n for n in eligible if metrics[n]['log_loss']<=loss+tolerance]
chosen=next(n for n in protocol['selection']['tie_preference'] if n in finalists)
assert chosen==selection['candidate']==freeze['candidate']==evaluation['candidate']=='boosting_platt'
assert not selection['final_test_used_for_selection']
assert evaluation['model_training_performed'] is evaluation['model_selection_performed'] is evaluation['threshold_selection_performed'] is False
assert all(receipts[r]['completed_at']<evaluation['completed_at'] for r in ['study','features','assessment','comparison','freeze'])
with sqlite3.connect(ledgers[0].as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    records=[dict(row) for row in db.execute('SELECT * FROM evaluations WHERE lineage_key=?',(lineage,))]
assert len(records)==1 and records[0]['status']=='completed'
assert records[0]['evaluation_id']==ids['evaluation'] and records[0]['freeze_id']==ids['freeze']
assert records[0]['freeze_digest']==graph[str((ROOT/'artifacts/private'/ids['freeze']/names['freeze']).relative_to(ROOT))]
assert all(sha256(ROOT/p)==h for p,h in before.items())
out=ROOT/'artifacts/private'/('bankruptcy-frozen-lineage-audit-'+uuid4().hex[:12]);out.mkdir()
write_new(out/'receipt.json',{'status':'PASS','ids':ids,'source_rows_in_one_year_study':5910,'exact_groups':5850,
          'partition_support':study['support'],'selected_candidate':chosen,'ledger_completed_once':True,
          'original_arff_identity_hash_checked':True,'final_predictor_reads':False,'model_inference':False,
          'ledger_sha256_unchanged':before,'inputs_sha256':graph,'method_sha256':sha256(Path(__file__)),
          'limitation':'No new raw final-feature comparison or refit; original preparation evidence is hash-verified. Group separation does not establish firm separation or OOT.'})
print(out)
