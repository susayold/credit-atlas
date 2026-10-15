"""Independent aggregate/footer evidence; no client/history predictor row reads."""
import json
import math
from pathlib import Path
from uuid import uuid4
import pyarrow.parquet as pq
from credit_atlas.workspace import sha256,contained

ROOT=Path.cwd();VIEW='suite-view-74e07524f6d0';CASE='retail-case-470bdb40682f'
out=ROOT/'artifacts/private'/('retail-data-contract-audit-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
base=ROOT/'artifacts/private'/CASE;case=json.loads((base/'case-complete.json').read_text())
quality=json.loads((base/'quality.json').read_text());protocol=json.loads((base/'protocol.json').read_text());recon=json.loads((base/'reconciliation.json').read_text())
view=json.loads((ROOT/f'artifacts/private/{VIEW}/snapshot.json').read_text());anchor=json.loads((ROOT/f'artifacts/private/{VIEW}/view-complete.json').read_text())
sourcebase=ROOT/'data/private/public-suite'/case['suite_id'];source=json.loads((sourcebase/'uci-retail-receipt.json').read_text());meta=json.loads((sourcebase/'uci-retail-metadata.json').read_text())['data']
pins={k.replace('\\','/'):h for k,h in anchor['inputs_sha256'].items()}
files=[]
for file in [base/'case-complete.json',sourcebase/'uci-retail-receipt.json',sourcebase/'uci-retail-metadata.json',sourcebase/'uci-retail.csv']+[base/name for name in case['outputs_sha256']]:
    rel=file.relative_to(ROOT).as_posix();digest=sha256(file);assert pins[rel]==digest
    if file.parent==base and file.name in case['outputs_sha256']:assert digest==case['outputs_sha256'][file.name]
    files.append({'path':rel,'sha256':digest})
assert case['metadata_sha256']==sha256(sourcebase/'uci-retail-metadata.json')
assert sha256(sourcebase/'uci-retail.csv')==source['sha256']==case['source_sha256']
assert sha256(ROOT/'src/credit_atlas/retail.py')==case['method_source_sha256']
assert source['profile']['rows']==quality['clients']==case['clients']==30000
assert source['profile']['duplicate_source_ids']==0 and quality['primary_key_unique'] is True
footer_clients=pq.ParquetFile(base/'clients.parquet').metadata.num_rows
footer_history=pq.ParquetFile(base/'six_month_history.parquet').metadata.num_rows
assert footer_clients==30000 and footer_history==quality['history_rows']==case['history_rows']==180000==6*footer_clients
assert recon=={'status':'PASS','method':'bidirectional_full_row_SQL_except_all','source_clients':30000,'source_history_rows':180000,'differing_rows':{'clients':0,'history':0}}
support={role:{'positive':0,'negative':0} for role in ['train','calibration','validation','final_test']}
for label,kind in [('1','positive'),('0','negative')]:
    n=source['profile']['target_counts'][label];boundaries=[0,math.floor(n*.60),math.floor(n*.75),math.floor(n*.90),n]
    for i,role in enumerate(support):support[role][kind]=boundaries[i+1]-boundaries[i]
assert support==quality['support']==case['support']==view['retail']['support']
assert quality['target_counts']==source['profile']['target_counts']=={'0':23364,'1':6636}
mapping={v['name']:v['description'] for v in meta['variables'] if v['role']=='Feature'}
expected=['LIMIT_BAL','SEX','EDUCATION','MARRIAGE','AGE','PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6']+[f'BILL_AMT{i}' for i in range(1,7)]+[f'PAY_AMT{i}' for i in range(1,7)]
assert mapping=={f'X{i+1}':name for i,name in enumerate(expected)}
allowed=set(protocol['feature_allowlist']['numeric']+protocol['feature_allowlist']['categorical']);assert len(allowed)==19
assert allowed==set(expected)-{'SEX','EDUCATION','MARRIAGE','AGE'}
assert not allowed&set(protocol['excluded_predictors']) and {'source_client_id','target'}<=set(protocol['excluded_predictors'])
assert meta['uci_id']==350 and meta['target_col']==['Y'] and meta['index_col']==['ID']
assert not protocol['temporal_out_of_time'] and not view['retail']['qualified_for_production']
category_cells=sum(len(counts) for counts in quality['source_category_counts'].values())
for counts in quality['source_category_counts'].values():assert sum(counts.values())==30000
assert category_cells==133 and quality['negative_statement_values_retained']==3932
assert sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P1.01','source_inputs':files,'clients':footer_clients,'history_rows':footer_history,'saved_full_row_reconciliation_hash_verified':True,'fresh_footer_checks':2,'fresh_predictor_row_reads':0,'feature_mapping_checks':23,'category_cells':category_cells,'split_support_independent_floor_recomputed':support,'ledger_unchanged':True,'method_sha256':sha256(Path(__file__)),'scope_note':'Current hashes/footers/aggregate consistency plus preserved pre-freeze full-row SQL parity;not a fresh all-client semantic row scan'},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','clients':footer_clients,'history_rows':footer_history,'predictor_row_reads':0}))
