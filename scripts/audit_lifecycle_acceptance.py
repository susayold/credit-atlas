"""Current source-wide index/identity audit and source-backed timeline probes."""
import json,re
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.server import STATIC
from credit_atlas.service import ResearchService
from credit_atlas.workspace import contained,sha256,write_new

ROOT=Path(__file__).resolve().parents[1];CASE='d01-a24484b21a21'
out=ROOT/'artifacts/private'/('lifecycle-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
service=ResearchService(ROOT,review_path=out/'qa-reviews.sqlite3');case=service.case(CASE);manifest=case['manifest']
con=duckdb.connect();con.execute("SET memory_limit='512MB'");con.execute('SET threads=2')
for name,stage in [('dim_loan','canonical_run'),('fact_loan_month','canonical_run'),('labels','label_run'),('episodes','portfolio_run')]:
    con.read_parquet(str(contained(ROOT,manifest[stage])/(name+'.parquet'))).create_view(name)
index=ROOT/'artifacts/private'/CASE/'loan-index.parquet';assert sha256(index)==manifest['outputs_sha256']['loan-index.parquet']
con.read_parquet(str(index)).create_view('idx')
counts=con.execute('SELECT count(*),count(DISTINCT loan_id),count(DISTINCT loan_key) FROM idx').fetchone();assert counts==(50000,50000,50000)
assert con.execute("SELECT count(*) FROM idx WHERE NOT regexp_full_match(loan_key,'[0-9a-f]{24}')").fetchone()[0]==0
fields='loan_id,origination_year,segment,classic_fico,original_ltv,outcome,target'
con.execute('''CREATE TEMP VIEW source_index AS SELECT d.loan_id,d.origination_year,
 CASE WHEN d.is_relief_refinance IS TRUE THEN 'relief' WHEN d.is_relief_refinance IS FALSE THEN 'non_relief' ELSE 'unknown' END AS segment,
 d.classic_fico,d.original_ltv,l.outcome,l.target FROM dim_loan d JOIN labels l USING(loan_id)''')
assert con.execute(f'SELECT count(*) FROM ((SELECT {fields} FROM idx EXCEPT ALL SELECT {fields} FROM source_index) UNION ALL (SELECT {fields} FROM source_index EXCEPT ALL SELECT {fields} FROM idx))').fetchone()[0]==0
raw_ids={r[0].encode() for r in con.execute('SELECT loan_id FROM idx').fetchall()}
prefixes={r[:4] for r in raw_ids};pattern=re.compile(b'|'.join(re.escape(p) for p in prefixes));lengths={len(r) for r in raw_ids}
def safe(data):
    for match in pattern.finditer(data):
        assert not any(data[match.start():match.start()+n] in raw_ids for n in lengths)
assets=[]
for name in sorted(set(STATIC.values())):
    path=ROOT/'apps/web'/name;safe(path.read_bytes());assets.append({'path':str(path.relative_to(ROOT)),'sha256':sha256(path)})
scopes=0;sampled={}
for segment in ['all','relief','non_relief','unknown']:
    for outcome in ['all','positive','negative','unavailable']:
        where=[];values=[]
        if segment!='all':where.append('segment=?');values.append(segment)
        if outcome=='unavailable':where.append('target IS NULL')
        elif outcome!='all':where.append('target=?');values.append(1 if outcome=='positive' else 0)
        predicate=' WHERE '+' AND '.join(where) if where else ''
        expected=con.execute('SELECT count(*) FROM idx'+predicate,values).fetchone()[0]
        r=service.loans(CASE,{'segment':segment,'outcome':outcome,'limit':'50'})
        assert r['total_matching']==expected and len(r['rows'])==min(expected,50)
        assert [x['loan_key'] for x in r['rows']]==[x[0] for x in con.execute('SELECT loan_key FROM idx'+predicate+' ORDER BY loan_key LIMIT 50',values).fetchall()]
        safe(json.dumps(r).encode());assert all(set(x)=={'loan_key','origination_year','segment','classic_fico','original_ltv','outcome'} for x in r['rows'])
        if r['rows']:sampled.setdefault(r['rows'][0]['loan_key'],(segment,outcome))
        scopes+=1
# Include confirmed event types and terminal-state variants, then check complete timelines.
for token, in con.execute('''SELECT min(loan_key) FROM idx i JOIN episodes e USING(loan_id) GROUP BY e.event_type
 UNION SELECT min(loan_key) FROM idx i JOIN fact_loan_month f USING(loan_id) WHERE terminal_type IS NOT NULL GROUP BY terminal_type''').fetchall():
    if token:sampled.setdefault(token,('all','representative_event_or_exit'))
timeline_checks=[]
for token,(segment,outcome) in sampled.items():
    raw=con.execute('SELECT loan_id FROM idx WHERE loan_key=?',[token]).fetchone()[0]
    r=service.timeline(CASE,token);safe(json.dumps(r).encode());assert 'loan_id' not in json.dumps(r)
    def normalize(value):
        return value.isoformat() if isinstance(value,date) else float(value) if isinstance(value,Decimal) else value
    static_fields=['origination_year','classic_fico','original_dti','original_ltv','original_cltv','original_upb','original_term','original_interest_rate','occupancy','loan_purpose','property_type','first_payment_date','is_relief_refinance','is_harp_subset']
    data=con.execute('SELECT '+','.join(static_fields)+' FROM dim_loan WHERE loan_id=?',[raw]).fetchone()
    assert r['static']=={k:normalize(v) for k,v in zip(static_fields,data)}
    label_fields=['landmark','horizon_end','eligibility_reason','outcome','target','label_known_month']
    data=con.execute('SELECT '+','.join(label_fields)+' FROM labels WHERE loan_id=?',[raw]).fetchone()
    assert r['label']=={k:normalize(v) for k,v in zip(label_fields,data)}
    rows=con.execute('SELECT period,delinquency_state,terminal_type,current_upb,current_rate,loan_age,modification,assistance,payment_deferral FROM fact_loan_month WHERE loan_id=? ORDER BY period',[raw]).fetchall()
    names=['period','delinquency_state','terminal_type','current_upb','current_rate','loan_age','modification','assistance','payment_deferral']
    expected=[]
    for row in rows:
        expected.append({k:v.isoformat() if k=='period' else float(v) if k in {'current_upb','current_rate'} and v is not None else v for k,v in zip(names,row)})
    assert r['months']==expected
    events=con.execute('SELECT confirmation_month,event_type FROM episodes WHERE loan_id=? ORDER BY confirmation_month,event_type',[raw]).fetchall()
    assert r['events']==[{'confirmation_month':d.isoformat(),'event_type':e} for d,e in events]
    assert r['case_id']==CASE and 'no model prediction' in r['limitation']
    for prefix in [token[:3],token]:
        result=service.loans(CASE,{'q':prefix,'limit':'50'})
        assert result['total_matching']==con.execute('SELECT count(*) FROM idx WHERE starts_with(loan_key,?)',[prefix]).fetchone()[0]
    timeline_checks.append({'loan_key':token,'segment_scope':segment,'outcome_scope':outcome,'months':len(rows),'events':len(events)})
con.close();assert sha256(ledger)==before
inputs=[f for f in manifest['verified_inputs'] if Path(f['path']).name in {'dim_loan.parquet','fact_loan_month.parquet','labels.parquet','episodes.parquet'}]
write_new(out/'receipt.json',{'status':'PASS','requirement':'P2.04','index_rows':50000,'unique_keys':50000,'index_source_differences':0,'list_scopes':scopes,'timeline_checks':timeline_checks,'static_assets_checked':assets,'source_inputs':inputs,
    'index_sha256':sha256(index),'case_receipt_sha256':sha256(ROOT/'artifacts/private'/CASE/'case-complete.json'),'ledger_unchanged':True,
    'methods':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'src/credit_atlas/service.py',ROOT/'src/credit_atlas/snapshot.py',ROOT/'src/credit_atlas/server.py']}})
print(out);print(json.dumps({'status':'PASS','list_scopes':scopes,'timeline_cases':len(timeline_checks),'static_assets':len(assets)}))
