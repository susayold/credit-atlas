"""Independent streaming monthly-stock and Python profile-bucket reconstruction."""
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.service import ResearchService
from credit_atlas.workspace import contained,sha256,write_new

ROOT=Path(__file__).resolve().parents[1];CASE='d01-a24484b21a21';OUT=None

def bucket(field,value):
    enums={'occupancy':{'P','I','S'},'loan_purpose':{'P','C','N','R'},'channel':{'R','B','C','T'},'property_type':{'CO','CP','PU','SF'},'first_time_homebuyer':{'Y','N'},'amortization_type':{'FRM','ARM'}}
    if field in enums:return value if value in enums[field] else 'Unknown'
    if field=='units':return 'Unavailable' if value is None or value<=0 else str(value) if value<=4 else '5+'
    limits={'classic_fico':(300,850),'original_ltv':(0,200),'original_dti':(0,100),'original_cltv':(0,250),'original_term':(1,480)}
    if value is None:return 'Unavailable'
    if field in limits and not limits[field][0]<=value<=limits[field][1]:return 'Unavailable'
    if field=='original_upb' and value<=0:return 'Unavailable'
    rules={'classic_fico':[(620,'<620'),(680,'620-679'),(740,'680-739'),(780,'740-779')],
           'original_upb':[(100000,'<100k'),(200000,'100k-199k'),(300000,'200k-299k'),(500000,'300k-499k')]}
    if field in rules:
        for ceiling,label in rules[field]:
            if value<ceiling:return label
        return '780+' if field=='classic_fico' else '500k+'
    rules={'original_ltv':[(60,'<=60'),(75,'61-75'),(80,'76-80'),(90,'81-90'),(95,'91-95')],
           'original_cltv':[(60,'<=60'),(75,'61-75'),(80,'76-80'),(90,'81-90'),(100,'91-100')],
           'original_dti':[(20,'<=20'),(30,'21-30'),(40,'31-40'),(50,'41-50')],
           'original_term':[(180,'<=180'),(240,'181-240'),(360,'241-360')]}
    for ceiling,label in rules[field]:
        if value<=ceiling:return label
    return {'original_ltv':'96+','original_cltv':'101+','original_dti':'51+','original_term':'361-480'}[field]

def run():
    global OUT
    OUT=ROOT/'artifacts/private'/('portfolio-acceptance-'+uuid4().hex[:12]);OUT.mkdir()
    ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    service=ResearchService(ROOT,review_path=OUT/'qa-reviews.sqlite3');case=service.case(CASE);manifest=case['manifest'];snapshot=case['snapshot']
    con=duckdb.connect();con.execute("SET memory_limit='512MB'");con.execute('SET threads=2');con.execute('SET temp_directory=?',[str(OUT/'tmp')])
    for name in ['dim_loan','fact_loan_month']:con.read_parquet(str(contained(ROOT,manifest['canonical_run'])/(name+'.parquet'))).create_view(name)
    assert con.execute('SELECT count(*) FROM (SELECT loan_id,period FROM fact_loan_month GROUP BY ALL HAVING count(*)>1)').fetchone()[0]==0
    monthly={};read_rows=0
    count_fields=['reported_loans','active_loans','terminal_loans','state_usable_active_loans','unknown_active_loans','d3_active_loans','reo_active_loans','missing_active_balance_loans']
    sum_fields=['observed_active_upb','state_usable_active_upb','d3_active_upb']
    cursor=con.execute('''SELECT f.period,f.delinquency_state,f.terminal_type,f.current_upb,d.is_relief_refinance FROM fact_loan_month f JOIN dim_loan d USING(loan_id)''')
    while batch:=cursor.fetchmany(10000):
        for period,state,terminal,upb,flag in batch:
            read_rows+=1;segment='relief' if flag is True else 'non_relief' if flag is False else 'unknown'
            for s in ['all',segment]:
                key=(s,period.isoformat());r=monthly.setdefault(key,{'period':period.isoformat(),**dict.fromkeys(count_fields,0),**dict.fromkeys(sum_fields,None),'zero_active_balance_loans':0})
                r['reported_loans']+=1
                if terminal is not None:r['terminal_loans']+=1;continue
                r['active_loans']+=1;r['state_usable_active_loans']+=state!='UNKNOWN';r['unknown_active_loans']+=state=='UNKNOWN';r['d3_active_loans']+=state=='D3PLUS';r['reo_active_loans']+=state=='REO'
                r['missing_active_balance_loans']+=upb is None;r['zero_active_balance_loans']+=upb==0
                if upb is not None:
                    for field,condition in [('observed_active_upb',True),('state_usable_active_upb',state!='UNKNOWN'),('d3_active_upb',state=='D3PLUS')]:
                        if condition:r[field]=(r[field] or Decimal(0))+upb
    assert read_rows==4510559
    zero=0;monthly_checks=0
    for segment in ['all','relief','non_relief','unknown']:
        actual=snapshot['snapshot']['monthly'] if segment=='all' else snapshot['monthly_by_segment'].get(segment,[])
        expected=[r for (s,period),r in sorted(monthly.items()) if s==segment];assert len(actual)==len(expected)
        for a,e in zip(actual,expected):
            for field in ['period',*count_fields]:assert a[field]==e[field];monthly_checks+=1
            for field in sum_fields:assert a[field]==(None if e[field] is None else float(e[field]));monthly_checks+=1
            count_share=None if not e['state_usable_active_loans'] else e['d3_active_loans']/e['state_usable_active_loans']
            balance_share=None if not e['state_usable_active_upb'] else float((e['d3_active_upb'] or Decimal(0))/e['state_usable_active_upb'])
            for field,value in [('d3_count_share',count_share),('d3_balance_share',balance_share)]:
                assert a[field] is None if value is None else abs(a[field]-value)<=1e-12;monthly_checks+=1
            assert e['state_usable_active_loans']+e['unknown_active_loans']==e['active_loans']
            if segment=='all':zero+=e['zero_active_balance_loans']
    print('Monthly stock/count/UPB/zero-vs-missing checks match',flush=True)
    profile=snapshot['snapshot']['portfolio_profile'];dimensions=profile['dimensions'];groups={};segment_totals=defaultdict(lambda:{'loans':0,'known':0,'upb':Decimal(0)})
    fields=['is_relief_refinance','original_upb',*dimensions]
    raw=con.execute('SELECT '+','.join(fields)+' FROM dim_loan').fetchall()
    for row in raw:
        values=dict(zip(fields,row));segment='relief' if row[0] is True else 'non_relief' if row[0] is False else 'unknown_relief';amount=values['original_upb'];known=amount is not None and amount>0
        t=segment_totals[segment];t['loans']+=1;t['known']+=known;t['upb']+=amount if known else Decimal(0)
        for dimension in dimensions:
            key=(segment,dimension,bucket(dimension,values[dimension]));g=groups.setdefault(key,{'loans':0,'known':0,'sum':None})
            g['loans']+=1;g['known']+=known
            if known:g['sum']=(g['sum'] or Decimal(0))+amount
    assert len(groups)==len(profile['rows'])
    for r in profile['rows']:
        key=(r['segment'],r['dimension'],r['bucket']);g=groups[key];t=segment_totals[r['segment']]
        assert r['loans']==g['loans'] and r['known_upb_loans']==g['known'] and r['missing_upb_loans']==g['loans']-g['known']
        assert r['opening_upb']==(float(g['sum']) if g['sum'] is not None else None)
        assert r['segment_loans']==t['loans'] and r['segment_known_upb_loans']==t['known'] and r['segment_opening_upb']==float(t['upb'])
        assert abs(r['count_share']-g['loans']/t['loans'])<=1e-12
        if g['sum'] is None:assert r['balance_share'] is None
        else:assert abs(r['balance_share']-float(g['sum']/t['upb']))<=1e-12
    exports=0
    for segment in ['all','relief','non_relief','unknown']:
        for start,end in [('',''),('2012-01','2012-03'),('2026-01','2026-03'),('1990-01','1990-12')]:
            p=service.report(CASE,{'segment':segment,'from':start,'to':end})
            monthly_table=next(t for t in p['report']['tables'] if t['table_id']=='portfolio_monthly')
            source=snapshot['snapshot']['monthly'] if segment=='all' else snapshot['monthly_by_segment'].get(segment,[])
            assert monthly_table['rows']==[r for r in source if (not start or r['period'][:7]>=start) and (not end or r['period'][:7]<=end)]
            profiles=next(t for t in p['report']['tables'] if t['table_id']=='portfolio_profile')
            assert profiles['rows']==[r for r in profile['rows'] if segment=='all' or r['segment']==segment]
            exports+=1
    con.close();assert sha256(ledger)==before
    inputs=[f for f in manifest['verified_inputs'] if Path(f['path']).name in {'dim_loan.parquet','fact_loan_month.parquet','profile.parquet'}]
    write_new(OUT/'receipt.json',{'status':'PASS','requirement':'P2.03','loan_months':read_rows,'monthly_checks':monthly_checks,'monthly_scope_rows':len(monthly),'zero_active_balance_observations':zero,'profile_dimensions':len(dimensions),'profile_groups':len(groups),'source_loans':len(raw),'export_scopes':exports,'source_inputs':inputs,'case_receipt_sha256':sha256(ROOT/'artifacts/private'/CASE/'case-complete.json'),'ledger_unchanged':True,
        'methods':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'src/credit_atlas/service.py',ROOT/'vendor/credit_risk_strategy_lab/sql/portfolio_monthly.sql',ROOT/'vendor/credit_risk_strategy_lab/sql/portfolio_profile.sql']}})
    print(OUT);print(json.dumps({'status':'PASS','checks':monthly_checks,'profile_groups':len(groups),'zero_active_balance':zero}))

if __name__=='__main__':
    try:run()
    except Exception as error:
        if OUT:write_new(OUT/'failed.json',{'status':'FAIL','error_type':type(error).__name__,'error':str(error)})
        raise
