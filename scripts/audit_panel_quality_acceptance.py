"""Source-wide raw blanks, field sentinels, panel grain and continuity audit."""
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.service import ResearchService
from credit_atlas.workspace import contained,sha256,write_new

ROOT=Path(__file__).resolve().parents[1];CASE='d01-a24484b21a21'
out=ROOT/'artifacts/private'/('panel-quality-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
service=ResearchService(ROOT,review_path=out/'qa-reviews.sqlite3');case=service.case(CASE);m=case['manifest'];q=case['snapshot']['source_quality'];tech=q['technical_profile']
con=duckdb.connect();con.execute("SET memory_limit='512MB'");con.execute('SET threads=2');con.execute('SET temp_directory=?',[str(out/'tmp')])
for name in ['dim_loan','fact_loan_month']:con.read_parquet(str(contained(ROOT,m['canonical_run'])/(name+'.parquet'))).create_view(name)
checks={
 'origination_rows':con.execute('SELECT count(*) FROM dim_loan').fetchone()[0],
 'origination_loans':con.execute('SELECT count(DISTINCT loan_id) FROM dim_loan').fetchone()[0],
 'performance_rows':con.execute('SELECT count(*) FROM fact_loan_month').fetchone()[0],
 'performance_loans':con.execute('SELECT count(DISTINCT loan_id) FROM fact_loan_month').fetchone()[0],
 'duplicate_origination_keys':con.execute('SELECT count(*)-count(DISTINCT loan_id) FROM dim_loan').fetchone()[0],
 'duplicate_monthly_keys':con.execute('SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM fact_loan_month GROUP BY loan_id,period)').fetchone()[0],
 'orphan_performance_rows':con.execute('SELECT count(*) FROM fact_loan_month f WHERE NOT EXISTS(SELECT 1 FROM dim_loan d WHERE d.loan_id=f.loan_id)').fetchone()[0],
 'loans_without_performance':con.execute('SELECT count(*) FROM dim_loan d WHERE NOT EXISTS(SELECT 1 FROM fact_loan_month f WHERE f.loan_id=d.loan_id)').fetchone()[0],
 'first_period':con.execute("SELECT strftime(min(period),'%Y%m') FROM fact_loan_month").fetchone()[0],
 'last_period':con.execute("SELECT strftime(max(period),'%Y%m') FROM fact_loan_month").fetchone()[0],
 'unknown_status_rows':con.execute("SELECT count(*) FROM fact_loan_month WHERE raw_delinquency='XX'").fetchone()[0],
 'reo_status_rows':con.execute("SELECT count(*) FROM fact_loan_month WHERE raw_delinquency='RA'").fetchone()[0],
 'd3plus_rows_not_incident_events':con.execute("SELECT count(*) FROM fact_loan_month WHERE try_cast(raw_delinquency AS INTEGER) BETWEEN 3 AND 99").fetchone()[0],
 'populated_loss_rows_not_resolved_loans':con.execute("SELECT count(*) FROM fact_loan_month WHERE trim(raw_actual_loss)<>''").fetchone()[0]}
# Backwards adjacency and continuity runs independently inspect observation lengths.
con.execute('''CREATE TEMP TABLE observed AS SELECT loan_id,period,
 lead(period) OVER(PARTITION BY loan_id ORDER BY period) AS next_period FROM fact_loan_month''')
coverage=con.execute('''SELECT min(n),max(n),count(*) FILTER(WHERE gaps>0) FROM
 (SELECT loan_id,count(*) n,sum(CASE WHEN date_diff('month',period,next_period)>1 THEN 1 ELSE 0 END) gaps FROM observed GROUP BY loan_id)''').fetchone()
checks.update(min_observed_months=coverage[0],max_observed_months=coverage[1],loans_with_gaps=coverage[2])
contiguous=con.execute('''SELECT count(DISTINCT loan_id) FROM (SELECT loan_id FROM
 (SELECT loan_id,period,row_number() OVER(PARTITION BY loan_id ORDER BY period)-date_diff('month',DATE '1900-01-01',period) AS run FROM observed)
 GROUP BY loan_id,run HAVING count(*)>=13) x''').fetchone()[0]
assert contiguous==tech['loans_with_13_contiguous_observed_months']
checks['loans_with_13_contiguous_observed_months']=contiguous
for key,value in checks.items():assert tech[key]==value,(key,tech[key],value)
blank_checks=0
for kind,table in [('origination','dim_loan'),('performance','fact_loan_month')]:
    fields=q['source_blank_counts'][kind]
    values=con.execute('SELECT '+','.join('count(*) FILTER(WHERE trim("raw_'+f+'")=\'\')' for f in fields)+' FROM '+table).fetchone()
    for f,n in zip(fields,values):assert fields[f]==n;blank_checks+=1
sentinels={'classic_fico':'9999','original_dti':'999','original_ltv':'999','original_cltv':'999','vantagescore':'9999','property_valuation_method':'7'}
for field,token in sentinels.items():
    raw_missing,canonical_missing=con.execute(f'SELECT count(*) FILTER(WHERE trim(raw_{field}) IN (?,\'\')),count(*) FILTER(WHERE {field} IS NULL) FROM dim_loan',[token]).fetchone()
    assert raw_missing==canonical_missing==q['canonical_missing_counts'][field]
# Validate every monthly raw delinquency/terminal mapping without canonical helper imports.
mis=con.execute('''SELECT count(*) FROM fact_loan_month WHERE delinquency_state IS DISTINCT FROM
 CASE WHEN trim(raw_delinquency)='00' THEN 'CURRENT' WHEN trim(raw_delinquency)='01' THEN 'D1'
 WHEN trim(raw_delinquency)='02' THEN 'D2' WHEN trim(raw_delinquency)='RA' THEN 'REO'
 WHEN try_cast(trim(raw_delinquency) AS INTEGER)>=3 AND try_cast(trim(raw_delinquency) AS INTEGER)<=99 THEN 'D3PLUS' ELSE 'UNKNOWN' END
 OR terminal_type IS DISTINCT FROM CASE WHEN trim(raw_zero_balance_code)='01' THEN 'PREPAID_OR_MATURED'
 WHEN trim(raw_zero_balance_code) IN ('02','03','09') THEN 'CREDIT_TERMINATION'
 WHEN trim(raw_zero_balance_code) IN ('15','16','96') THEN 'OTHER_TERMINATION' ELSE NULL END''').fetchone()[0]
assert mis==0
monitor=service.monitoring(CASE)
assert all(r['value']==tech[r['check']] for r in monitor['integrity_checks'])
assert all(r['missing']==q['canonical_missing_counts'][r['field']] and r['population']==50000 for r in monitor['field_availability'])
assert monitor['model_monitoring']['drift_alert'] is None and monitor['model_monitoring']['calibration_alert'] is None
con.close();assert sha256(ledger)==before
inputs=[f for f in m['verified_inputs'] if Path(f['path']).name in {'dim_loan.parquet','fact_loan_month.parquet'}]
write_new(out/'receipt.json',{'status':'PASS','requirement':'P2.02','technical_checks':len(checks),'raw_blank_field_checks':blank_checks,'sentinel_fields':len(sentinels),'monthly_mapping_rows':4510559,'mapping_differences':mis,'source_counts':checks,'ledger_unchanged':True,'source_inputs':inputs,'case_receipt_sha256':sha256(ROOT/'artifacts/private'/CASE/'case-complete.json'),
 'methods':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'src/credit_atlas/monitoring.py',ROOT/'src/credit_atlas/service.py']}})
print(out);print('PASS',len(checks),blank_checks,len(sentinels))
