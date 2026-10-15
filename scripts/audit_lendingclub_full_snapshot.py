"""Independent DuckDB parser census for both complete publisher GZIP files."""
import json,uuid
from pathlib import Path
import duckdb
from credit_atlas.workspace import sha256
root=Path.cwd();profile=root/'artifacts/private/lendingclub-full-profile-f4168e8d746c/profile.json'
assert sha256(profile)=='f8be3a2f137172f019d4cce743c173c03176f1fb5d3e3b54e67350ee34f60098'
doc=json.loads(profile.read_text(encoding='utf8'));folder=root/'data/private/retail'/doc['source_id']
out=root/'artifacts/private'/('lendingclub-full-audit-'+uuid.uuid4().hex[:12]);out.mkdir();issues=[];checks=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
con=duckdb.connect();con.execute("SET memory_limit='512MB'");con.execute('SET threads=2')
con.execute('SET temp_directory=?',[str(out/'tmp')])
def identifier(name):return '"'+name.replace('"','""')+'"'
for p in doc['profiles']:
    path=folder/p['file'];assert sha256(path)==p['source_sha256']
    literal="'"+path.as_posix().replace("'","''")+"'"
    con.execute("CREATE OR REPLACE TEMP VIEW source AS SELECT * FROM read_csv("+literal+",header=true,all_varchar=true,nullstr='__CREDIT_ATLAS_NO_SOURCE_NULL__',sample_size=2048)")
    columns=[r[0] for r in con.execute('DESCRIBE source').fetchall()]
    if columns!=p['columns']:issues.append(p['kind']+' columns')
    missing_expr=[]
    for name in columns:
        value='regexp_replace('+identifier(name)+",'^\\s+|\\s+$','','g')"
        missing_expr.append("SUM(CASE WHEN "+value+" IN ('','NA','N/A','null','NULL','NaN','nan','None') THEN 1 ELSE 0 END)")
    null_expr=' OR '.join(identifier(name)+' IS NULL' for name in columns)
    values=con.execute('SELECT COUNT(*),'+','.join(missing_expr)+',SUM(CASE WHEN '+null_expr+' THEN 1 ELSE 0 END) FROM source').fetchone()
    if values[-1]:issues.append(p['kind']+' unexpected SQL null conversion')
    if values[0]!=p['rows']:issues.append(p['kind']+' rows')
    for name,n in zip(columns,values[1:-1]):
        if n!=p['missing_counts'][name]:issues.append(p['kind']+' missing '+name)
    date=identifier(p['date_column']);category=identifier(p['category_column'])
    period="strftime(try_strptime(trim("+date+"),'%b-%Y'),'%Y-%m')" if p['kind']=='accepted' else "strftime(try_cast(trim("+date+" ) AS DATE),'%Y-%m')"
    grouped=con.execute('SELECT '+period+' AS month,trim('+category+') AS category,COUNT(*) FROM source GROUP BY 1,2 ORDER BY 1,2').fetchall()
    expected={(r['month'],r['source_category']):r['records'] for r in p['month_category_counts']}
    actual={(m,c):n for m,c,n in grouped if m is not None}
    if actual!=expected:issues.append(p['kind']+' monthly category counts')
    null_dates=sum(n for m,c,n in grouped if m is None)
    if null_dates!=sum(p['invalid_or_missing_date_counts'].values()):issues.append(p['kind']+' missing dates')
    categories=dict(con.execute('SELECT trim('+category+'),COUNT(*) FROM source GROUP BY 1').fetchall())
    if categories!=p['source_category_counts']:issues.append(p['kind']+' source categories')
    checks.append({'kind':p['kind'],'rows':values[0],'missing_columns_checked':len(columns),'month_category_cells_checked':len(actual),'null_or_invalid_dates':null_dates})
    print(checks[-1],flush=True)
con.close();unchanged=sha256(ledger)==before
result={'status':'PASS' if not issues and unchanged else 'ISSUES_FOUND','checks':checks,'issues':issues,'ledger_unchanged':unchanged,
    'scope':'Independent DuckDB CSV/GZIP parser,all column missingness,rows/categories/monthly groups;not approval denominator,target timing,original fidelity or rights qualification'}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(out);print(result['status']);print(issues[:20])
if result['status']!='PASS':raise SystemExit(1)
