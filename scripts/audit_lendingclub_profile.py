"""Independent Arrow CSV engine: every missingness column and selected stats."""
import hashlib,json,time,uuid
from collections import Counter
from decimal import Decimal
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
root=Path.cwd();profile=root/'artifacts/private/lendingclub-profile-28db23b7bd0a/profile.json'
doc=json.loads(profile.read_text(encoding='utf8'));folder=root/'data/private/retail'/doc['source_id']
receipt=json.loads((folder/'acquisition-complete.json').read_text(encoding='utf8'))
source=next(s for s in receipt['sources'] if s['file'].endswith('.csv'));path=folder/source['file']
out=root/'artifacts/private'/('lendingclub-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=hashlib.sha256(ledger.read_bytes()).hexdigest()
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1024**2):h.update(chunk)
    return h.hexdigest()
assert digest(path)==source['sha256']==receipt['publisher_file_metadata'][0]['content_details']['sha256_hash']
assert digest(profile)=='0ab0d8179811cec4499a83fd727e1d5cf7597f37b9b703f64af10774d9ed9e36'
reader=csv.open_csv(path,read_options=csv.ReadOptions(block_size=8*1024**2),
    convert_options=csv.ConvertOptions(column_types={c:pa.string() for c in doc['columns']},null_values=[],strings_can_be_null=False))
missing=Counter();groups=Counter();numeric={k:{'present':0,'missing':0,'invalid':0,'zero':0,'negative':0,'min':None,'max':None,'sum':Decimal(0)} for k in doc['numeric_source_profiles']}
rows=0;ids=[];last=time.monotonic();tokens=pa.array(doc['missing_tokens'])
for batch in reader:
    rows+=batch.num_rows;table=pa.Table.from_batches([batch]);ids.append(table['id'])
    for name in doc['columns']:
        text=pc.utf8_trim_whitespace(table[name]);blank=pc.is_in(text,value_set=tokens)
        n=pc.sum(pc.cast(blank,pa.int64())).as_py();missing[name]+=n
        if name not in numeric:continue
        stat=numeric[name];stat['missing']+=n;stat['present']+=batch.num_rows-n
        cleaned=pc.if_else(blank,pa.scalar(None,type=pa.string()),text)
        numbers=pc.cast(cleaned,pa.decimal128(38,6));mm=pc.min_max(numbers).as_py();total=pc.sum(numbers).as_py()
        if total is not None:stat['sum']+=total
        if mm['min'] is not None:stat['min']=mm['min'] if stat['min'] is None else min(stat['min'],mm['min'])
        if mm['max'] is not None:stat['max']=mm['max'] if stat['max'] is None else max(stat['max'],mm['max'])
        stat['zero']+=pc.sum(pc.cast(pc.equal(numbers,0),pa.int64())).as_py() or 0
        stat['negative']+=pc.sum(pc.cast(pc.less(numbers,0),pa.int64())).as_py() or 0
    aggregated=table.group_by(['issue_d','loan_status','LoanStatus','application_type']).aggregate([('id','count')])
    for group in aggregated.to_pylist():groups[(group['issue_d'].strip(),group['loan_status'].strip(),group['LoanStatus'].strip(),group['application_type'].strip())]+=group['id_count']
    if time.monotonic()-last>12:print('audited records',rows,flush=True);last=time.monotonic()
issues=[]
if rows!=doc['rows']:issues.append('row count')
for name in doc['columns']:
    if missing[name]!=doc['missing_counts'][name]:issues.append('missingness '+name)
for name,stat in numeric.items():
    expected=doc['numeric_source_profiles'][name]
    for key,value in stat.items():
        if key in {'sum','min','max'}:
            good=value is None and expected[key] is None or value is not None and expected[key] is not None and value==Decimal(expected[key])
        else:good=value==expected[key]
        if not good:issues.append(name+' '+key)
monthly=Counter();statuses=Counter();cross=Counter();types=Counter();date_keys=[]
for (date,status,target,application),count in groups.items():
    month,day,year=map(int,date.split('/'));key=f'{year:04d}-{month:02d}';date_keys.append(f'{key}-{day:02d}')
    monthly[(key,status)]+=count;statuses[status]+=count;cross[(status,target)]+=count;types[application]+=count
expected_monthly=Counter({(r['issue_month'],r['source_loan_status']):r['records'] for r in doc['monthly_source_status_counts']})
expected_cross=Counter({(r['source_loan_status'],r['encoded_LoanStatus_raw']):r['records'] for r in doc['source_status_encoded_cross_counts']})
for label,good in [('monthly cohorts',monthly==expected_monthly),('source status',dict(statuses)==doc['source_status_counts']),
    ('target encoding',cross==expected_cross),('application types',dict(types)==doc['application_type_counts']),
    ('date range',[min(date_keys),max(date_keys)]==doc['issue_date_range'])]:
    if not good:issues.append(label)
all_ids=pa.chunked_array([chunk for array in ids for chunk in array.chunks]);distinct=pc.count_distinct(all_ids).as_py()
unchanged=digest(ledger)==before
result={'status':'PASS' if not issues and unchanged else 'ISSUES_FOUND','issues':issues,'rows':rows,'raw_cell_positions':rows*len(doc['columns']),
    'missingness_columns_checked':len(doc['columns']),'numeric_profiles_checked':len(numeric),'numeric_checks':sum(len(s) for s in numeric.values()),
    'monthly_status_cells_checked':len(monthly),'source_target_cross_cells_checked':len(cross),'distinct_source_ids':distinct,
    'source_id_duplicates':rows-distinct,'ledger_unchanged':unchanged,
    'scope':'Independent Arrow parser/Decimal aggregation and cohort/label counts,not original source fidelity,application chronology or fixed-horizon target qualification'}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(out);print(result)
if result['status']!='PASS':raise SystemExit(1)
