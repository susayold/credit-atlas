"""Source temporal evidence; activity dates never become a certified cutoff."""
import json,uuid
from pathlib import Path
import duckdb
from credit_atlas.workspace import read_json,sha256,write_new
root=Path.cwd();source=root/'data/private/retail/lendingclub-full-source-3954d375d972'
receipt=read_json(source/'acquisition-complete.json');assert sha256(source/'acquisition-complete.json')=='8c75b6f45be94ccc7e610f3be8aa1f51246b48bc69331dea8db518c69f657d55'
file=next(s for s in receipt['sources'] if s['file'].startswith('accepted'));path=source/file['file'];assert sha256(path)==file['sha256']
out=root/'artifacts/private'/('lendingclub-temporal-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
con=duckdb.connect();con.execute("SET memory_limit='512MB'");con.execute('SET threads=2');con.execute('SET temp_directory=?',[str(out/'tmp')])
literal="'"+path.as_posix().replace("'","''")+"'"
con.execute("CREATE TEMP VIEW raw AS SELECT * FROM read_csv("+literal+",header=true,all_varchar=true,nullstr='__NO_SOURCE_NULL__',sample_size=2048)")
con.execute("""CREATE TEMP VIEW dated AS SELECT *,try_strptime(issue_d,'%b-%Y') AS booked,
    try_strptime(last_pymnt_d,'%b-%Y') AS last_payment,try_strptime(last_credit_pull_d,'%b-%Y') AS credit_pull,
    try_strptime(next_pymnt_d,'%b-%Y') AS next_payment,try_cast(trim(replace(term,'months','')) AS INTEGER) AS term_months FROM raw""")
date_profiles=[]
for raw,typed,role in [('issue_d','booked','funded month'),('last_pymnt_d','last_payment','last received payment month'),('last_credit_pull_d','credit_pull','last credit-pull month'),('next_pymnt_d','next_payment','scheduled next payment month')]:
    row=con.execute('SELECT count(*),count('+typed+'),min('+typed+'),max('+typed+'),sum(CASE WHEN '+typed+" IS NULL AND trim("+raw+")<>'' THEN 1 ELSE 0 END) FROM dated").fetchone()
    date_profiles.append({'field':raw,'role':role,'source_rows':row[0],'valid_months':row[1],
        'min_observed_month':row[2].strftime('%Y-%m') if row[2] else None,'max_observed_month':row[3].strftime('%Y-%m') if row[3] else None,
        'nonblank_unparsed':row[4],'certified_snapshot_cutoff':False})
rows=con.execute("""SELECT strftime(booked,'%Y-%m'),loan_status,term_months,count(*),
    sum(CASE WHEN last_payment IS NOT NULL THEN 1 ELSE 0 END),
    sum(CASE WHEN date_diff('month',booked,last_payment)>=12 THEN 1 ELSE 0 END),
    sum(CASE WHEN last_payment<booked THEN 1 ELSE 0 END),
    sum(CASE WHEN credit_pull<booked THEN 1 ELSE 0 END)
    FROM dated GROUP BY 1,2,3 ORDER BY 1,2,3""").fetchall()
cohorts=[{'issue_month':r[0],'source_loan_status':r[1],'contract_term_months':r[2],'records':r[3],
    'last_payment_month_available':r[4],'last_payment_span_at_least_12m':r[5],
    'last_payment_before_booking':r[6],'last_credit_pull_before_booking':r[7]} for r in rows]
counts=con.execute("""SELECT count(*),sum(CASE WHEN booked IS NULL THEN 1 ELSE 0 END),
    sum(CASE WHEN member_id='' THEN 1 ELSE 0 END),sum(CASE WHEN term_months NOT IN (36,60) OR term_months IS NULL THEN 1 ELSE 0 END)
    FROM dated""").fetchone()
con.close()
doc={'source_id':receipt['source_id'],'source_receipt_sha256':sha256(source/'acquisition-complete.json'),'source_file':file,
    'date_profiles':date_profiles,'cohort_term_payment_span':cohorts,'source_rows':counts[0],'unavailable_booking_month':counts[1],
    'missing_member_id':counts[2],'unsupported_or_missing_contract_term':counts[3],
    'certified_observation_cutoff':None,'fixed_horizon_pd12_labels':None,'maturity_qualified':False,'application_feature_timing_qualified':False,
    'model_training_performed':False,'ledger_unchanged':sha256(ledger)==before,'visibility':'private','public_release_approved':False,
    'interpretations':['A last-payment span of12months proves only a timestamp span,not continuous observation or a no-default label.',
        'Latest credit-pull/payment dates and file creation timestamps do not certify a common observation cutoff.',
        'Next-payment month is a schedule field,not observed future performance.',
        'Terminal/current status does not provide first default-event history;last payment is not a substitute event date.',
        'Without a certified cutoff and event/exits history,no cohort is automatically marked mature for PD12.',
        'member_id missingness prevents verified borrower grouping;loan IDs alone do not resolve shared-borrower leakage.']}
write_new(out/'profile.json',doc);write_new(out/'receipt.json',{'status':'TEMPORAL_EVIDENCE_BUILT','profile_sha256':sha256(out/'profile.json'),'cohort_term_groups':len(cohorts),'ledger_unchanged':doc['ledger_unchanged']})
print(out);print(sha256(out/'profile.json'));print(date_profiles);print('groups',len(cohorts),'counts',counts)
