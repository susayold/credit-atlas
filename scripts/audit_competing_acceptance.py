"""Independent per-loan endpoints and rational competing-incidence audit."""
import math,random,json
from collections import Counter
from fractions import Fraction
from itertools import groupby
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.service import ResearchService
from credit_atlas.workspace import contained,read_json,sha256,write_new

ROOT=Path(__file__).resolve().parents[1];CASE='d01-a24484b21a21';OUT=None
def ordinal(d):return d.year*12+d.month

def incidence(counts):
    n=sum(counts.values());survival=Fraction(1);cif=[Fraction(0)]*3;out={}
    for age in range(1,25):
        risk=sum(n for (stop,_),n in counts.items() if stop>=age)
        events=[counts.get((age,c),0) for c in ['d3','prepayment','other_exit']]
        if risk:
            cif=[v+survival*Fraction(e,risk) for v,e in zip(cif,events)]
            survival*=Fraction(risk-sum(events),risk)
        out[age]=(risk,cif[:],survival)
    return out

def run():
    global OUT
    OUT=ROOT/'artifacts/private'/('competing-acceptance-'+uuid4().hex[:12]);OUT.mkdir()
    ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    service=ResearchService(ROOT,review_path=OUT/'qa-reviews.sqlite3');case=service.case(CASE);manifest=case['manifest']
    snapshot=case['snapshot'];vintage=snapshot['snapshot']['vintage_evidence'];folder=ROOT/'vendor/credit_risk_strategy_lab/artifacts/private'/vintage['vintage_run']
    receipt=read_json(folder/'run-complete.json');summary=read_json(folder/'summary.json')
    source_inputs=[]
    for p in [contained(ROOT,manifest['canonical_run'])/'dim_loan.parquet',contained(ROOT,manifest['canonical_run'])/'fact_loan_month.parquet',folder/'vintage_ledger.parquet',folder/'summary.json',folder/'run-complete.json']:
        source_inputs.append({'path':str(p.relative_to(ROOT)),'sha256':sha256(p)})
    for f in manifest['verified_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
    con=duckdb.connect();con.execute("SET memory_limit='1GB'");con.execute('SET threads=2');con.execute('SET temp_directory=?',[str(OUT/'tmp')])
    con.read_parquet(str(contained(ROOT,manifest['canonical_run'])/'dim_loan.parquet')).create_view('dim')
    con.read_parquet(str(contained(ROOT,manifest['canonical_run'])/'fact_loan_month.parquet')).project('loan_id,period,loan_age,delinquency_state,modification,terminal_type').create_view('fact')
    con.read_parquet(str(folder/'vintage_ledger.parquet')).create_view('saved')
    static={r[0]:r[1:] for r in con.execute('SELECT loan_id,origination_year,is_relief_refinance,first_payment_date FROM dim').fetchall()}
    expected_saved={r[0]:r[1:] for r in con.execute('SELECT loan_id,stop_age,endpoint,censor_reason,calendar_age FROM saved').fetchall()}
    last=con.execute('SELECT max(period) FROM fact').fetchone()[0]
    cursor=con.execute('SELECT loan_id,period,loan_age,delinquency_state,modification,terminal_type FROM fact ORDER BY loan_id,period')
    def stream():
        while batch:=cursor.fetchmany(10000):yield from batch
    totals=Counter();eligible=Counter();exclusions=Counter();counts={};calendar={};label_counts=Counter();all_count=0
    for loan,group in groupby(stream(),lambda r:r[0]):
        rows=list(group);first=rows[0];year,relief,payment=static[loan];segment='relief' if relief is True else 'non_relief' if relief is False else 'unknown_relief'
        all_count+=1;totals[(year,'all')]+=1;totals[(year,segment)]+=1
        contractual=None if payment is None else ordinal(first[1])-ordinal(payment)+1
        reason=('terminal_at_entry' if first[5] is not None else 'severe_at_entry' if first[3] in {'D3PLUS','REO'} else 'unknown_at_entry' if first[3]=='UNKNOWN' else 'modified_at_entry' if first[4] is not None else 'missing_entry_age' if first[2] is None or contractual is None else 'entry_age_mismatch' if first[2]!=contractual else 'not_early_entry' if not 0<=first[2]<=1 else 'eligible')
        exclusions[reason]+=1
        if reason!='eligible':
            assert loan not in expected_saved;label_counts[('ineligible',None)]+=1;continue
        months={ordinal(r[1])-ordinal(first[1]):r for r in rows[1:]}
        stop=24;endpoint='censored';censor='horizon_complete'
        for age in range(1,25):
            r=months.get(age)
            if r is None:
                stop=age-1;censor='administrative' if age>max(months,default=0) else 'unknown_or_gap';break
            if r[3]=='UNKNOWN':stop=age-1;censor='unknown_or_gap';break
            cause='d3' if r[3]=='D3PLUS' else 'other_exit' if r[3]=='REO' or r[5] in {'CREDIT_TERMINATION','OTHER_TERMINATION'} else 'prepayment' if r[5]=='PREPAID_OR_MATURED' else None
            if cause:stop=age;endpoint=cause;censor=None;break
        maturity=ordinal(last)-ordinal(first[1]);assert expected_saved[loan]==(stop,endpoint,censor,maturity)
        for s in ['all',segment]:
            key=(year,s);eligible[key]+=1;counts.setdefault(key,Counter())[(stop,endpoint)]+=1;calendar.setdefault(key,[]).append(maturity)
        # Twelve-month binary labels distinguish unknown/censored from true negatives.
        events=[]
        for age,r in months.items():
            if age<=12:
                if r[3]=='D3PLUS':events.append((age,0,'d3_event'))
                if r[3]=='REO' or r[5] in {'CREDIT_TERMINATION','OTHER_TERMINATION'}:events.append((age,1,'other_exit'))
                if r[5]=='PREPAID_OR_MATURED':events.append((age,2,'prepayment'))
        end=min(events)[0] if events else 12
        observed=[r for age,r in months.items() if age<=end]
        outcome='unknown_followup' if any(r[3]=='UNKNOWN' for r in observed) else ('administrative_censoring' if max(months,default=0)<end else 'gap_followup') if len(observed)<end else min(events)[2] if events else 'complete_no_event'
        target=1 if outcome=='d3_event' else 0 if outcome in {'prepayment','complete_no_event'} else None
        label_counts[(outcome,target)]+=1
    assert all_count==50000 and sum(eligible.values())==2*len(expected_saved)
    con.read_parquet(str(contained(ROOT,manifest['label_run'])/'labels.parquet')).create_view('labels')
    assert dict(label_counts)=={(o,t):n for o,t,n in con.execute('SELECT outcome,target,count(*) FROM labels GROUP BY ALL').fetchall()}
    probability_checks=0
    for row in summary['curves']:
        key=(row['origination_year'],row['segment']);age=row['observation_age'];n=eligible[key];risk,cif,survival=incidence(counts[key])[age]
        assert row['source_loans']==totals[key] and row['eligible_loans']==n and row['excluded_loans']==totals[key]-n
        assert row['at_risk']==risk and row['calendar_mature_loans']==sum(a>=age for a in calendar[key])
        mature=n>0 and all(a>=age for a in calendar[key]);assert row['maturity_complete']==mature
        for cause,value in zip(['d3','prepayment','other_exit'],cif):
            assert row['observed_'+cause+'_count']==sum(v for (stop,c),v in counts[key].items() if c==cause and stop<=age)
            actual=row['cif_'+cause]
            if mature and row['supported']:assert actual is not None and abs(actual-float(value))<=1e-12
            else:assert actual is None
            probability_checks+=1
        assert sum(cif)+survival==1
    print('Full endpoint ledger,labels and rational incidence match',flush=True)
    # Reproduce seeded loan-bootstrap quantiles with an independently evaluated estimator.
    bootstrap_checks=0
    for key,c in counts.items():
        randomizer=random.Random(receipt['seed']);keys=sorted(c);weights=[c[k] for k in keys];n=sum(c.values());draws={h:[] for h in [6,12,24]}
        for replicate in range(receipt['resamples']):
            sampled=Counter(randomizer.choices(keys,weights=weights,k=n));values=incidence(sampled)
            for h in draws:draws[h].append(float(values[h][1][0]))
        for h,values in draws.items():
            row=next(r for r in summary['horizons'] if (r['origination_year'],r['segment'],r['observation_age'])==(*key,h))
            values.sort()
            for field,fraction in [('ci_lower',.025),('ci_upper',.975)]:
                if row[field] is not None:
                    index=(len(values)-1)*fraction;lo=math.floor(index);hi=math.ceil(index);expected=values[lo]+(values[hi]-values[lo])*(index-lo)
                    assert abs(row[field]-expected)<=1e-12;bootstrap_checks+=1
        print('Bootstrap checked',key,flush=True)
    for row in vintage['rows']:
        expected=next(r for r in summary['horizons'] if (r['origination_year'],r['segment'],r['observation_age'])==(row['origination_year'],row['segment'],row['observation_age']))
        assert all(row[k]==expected[k] for k in row)
    exports=0
    for s in ['all','relief','non_relief','unknown']:
        for h in ['6','12','24']:
            report=service.report(CASE,{'segment':s,'horizon':h})
            table=next(t for t in report['report']['tables'] if t['table_id']=='vintage_competing_risk')
            assert table['rows']==[r for r in vintage['rows'] if r['segment']==s and r['observation_age']==int(h)]
            exports+=1
    con.close();assert sha256(ledger)==before
    write_new(OUT/'receipt.json',{'status':'PASS','requirement':'P2.07','source_loans':all_count,'eligible_loans':len(expected_saved),'ledger_rows_checked':len(expected_saved),'curve_rows_checked':len(summary['curves']),'probability_checks':probability_checks,'bootstrap_bound_checks':bootstrap_checks,'export_scopes':exports,'exclusions':dict(exclusions),'label_counts':[{'outcome':o,'target':t,'loans':n} for (o,t),n in label_counts.items()],
      'source_inputs':source_inputs,'case_receipt_sha256':sha256(ROOT/'artifacts/private'/CASE/'case-complete.json'),'ledger_unchanged':True,'bootstrap_coverage_claimed':False,
      'methods':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'src/credit_atlas/service.py',ROOT/'vendor/credit_risk_strategy_lab/src/crsl/vintage.py',ROOT/'vendor/credit_risk_strategy_lab/sql/marts/vintage.sql']}})
    print(OUT)

if __name__=='__main__':
    try:run()
    except Exception as error:
        if OUT:write_new(OUT/'failed.json',{'status':'FAIL','error_type':type(error).__name__,'error':str(error)})
        raise
