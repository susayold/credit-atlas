"""Independent set-based cure/redefault and follow-up reconstruction for P2.06."""
import json
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.service import ResearchService
from credit_atlas.workspace import contained,sha256,write_new

ROOT=Path(__file__).resolve().parents[1];CASE='d01-a24484b21a21';RUN_OUT=None

def run():
    global RUN_OUT
    out=ROOT/'artifacts/private'/('cure-acceptance-'+uuid4().hex[:12]);out.mkdir();RUN_OUT=out
    ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    service=ResearchService(ROOT,review_path=out/'qa-reviews.sqlite3');case=service.case(CASE);manifest=case['manifest']
    inputs=[f for f in manifest['verified_inputs'] if Path(f['path']).name in {'dim_loan.parquet','fact_loan_month.parquet','episodes.parquet'}]
    assert len(inputs)==3
    for f in inputs:assert sha256(contained(ROOT,f['path']))==f['sha256']
    con=duckdb.connect();con.execute("SET memory_limit='1GB'");con.execute('SET threads=2');con.execute('SET temp_directory=?',[str(out/'tmp')])
    for name,run in [('dim_loan','canonical_run'),('fact_loan_month','canonical_run'),('episodes','portfolio_run')]:
        table=con.read_parquet(str(contained(ROOT,manifest[run])/(name+'.parquet')))
        if name=='fact_loan_month':table=table.project('loan_id,period,delinquency_state,terminal_type')
        table.create_view(name)
    print('Source hashes verified;full panel projected to four episode columns',flush=True)
    # Separate continuity blocks, D3 anchors and consecutive CURRENT runs.
    # This does not call the upstream state-machine generator.
    con.execute('''CREATE TEMP TABLE ordered AS
      SELECT *,lag(period) OVER w AS previous_period,lag(terminal_type) OVER w AS previous_terminal
      FROM fact_loan_month WINDOW w AS(PARTITION BY loan_id ORDER BY period)''')
    con.execute('''CREATE TEMP TABLE blocks AS SELECT *,sum(CASE WHEN
      (previous_period IS NOT NULL AND date_diff('month',previous_period,period)<>1)
      OR previous_terminal IS NOT NULL OR delinquency_state='UNKNOWN'
      OR (terminal_type IS NOT NULL AND delinquency_state<>'D3PLUS') THEN 1 ELSE 0 END)
      OVER(PARTITION BY loan_id ORDER BY period) AS block
      FROM ordered''')
    con.execute('''CREATE TEMP TABLE runs AS SELECT *,
      max(CASE WHEN delinquency_state='D3PLUS' THEN period END) OVER w AS last_d3,
      sum(CASE WHEN delinquency_state<>'CURRENT' OR terminal_type IS NOT NULL THEN 1 ELSE 0 END) OVER w AS current_run
      FROM blocks WINDOW w AS(PARTITION BY loan_id,block ORDER BY period)''')
    con.execute('''CREATE TEMP TABLE streaks AS SELECT *,
      count(*) FILTER(WHERE delinquency_state='CURRENT' AND terminal_type IS NULL)
       OVER(PARTITION BY loan_id,block,current_run ORDER BY period) AS current_streak
      FROM runs''')
    con.execute('''CREATE TEMP TABLE confirmations AS SELECT loan_id,block,last_d3,min(period) AS confirmed
      FROM streaks WHERE current_streak=3 AND last_d3 IS NOT NULL
      AND delinquency_state='CURRENT' AND terminal_type IS NULL GROUP BY ALL''')
    print('Continuity blocks and current-run confirmations reconstructed',flush=True)
    con.execute('''CREATE TEMP TABLE expected_events AS
      SELECT loan_id,min(period) AS confirmation_month,'FIRST_OBSERVED_D3' AS event_type
       FROM fact_loan_month WHERE delinquency_state='D3PLUS' GROUP BY loan_id
      UNION ALL
      SELECT s.loan_id,s.period,'ONE_MONTH_CURE' FROM streaks s
       LEFT JOIN confirmations c USING(loan_id,block,last_d3)
       WHERE s.delinquency_state='CURRENT' AND s.terminal_type IS NULL AND s.current_streak=1
       AND s.last_d3 IS NOT NULL AND (c.confirmed IS NULL OR s.period<=c.confirmed)
      UNION ALL
      SELECT loan_id,confirmed,'SUSTAINED_CURE_CONFIRMED' FROM confirmations
      UNION ALL
      SELECT d.loan_id,d.period,'REDEFAULT_AFTER_SUSTAINED_CURE' FROM
       (SELECT loan_id,block,period,lag(period) OVER(PARTITION BY loan_id,block ORDER BY period) AS previous_d3
        FROM blocks WHERE delinquency_state='D3PLUS') d
       JOIN confirmations c ON d.loan_id=c.loan_id AND d.block=c.block AND d.previous_d3=c.last_d3
       WHERE c.confirmed<d.period''')
    differences=con.execute('''SELECT count(*) FROM ((SELECT * FROM expected_events EXCEPT ALL
      SELECT loan_id,confirmation_month,event_type FROM episodes) UNION ALL
      (SELECT loan_id,confirmation_month,event_type FROM episodes EXCEPT ALL SELECT * FROM expected_events))''').fetchone()[0]
    assert differences==0
    event_count=con.execute('SELECT count(*) FROM expected_events').fetchone()[0]
    print('All event rows match:',event_count,flush=True)
    # Dense expected-month grid distinguishes gap from end-of-source; no missing month filled as known.
    con.execute('''CREATE TEMP TABLE expected_followup AS WITH anchors AS(
      SELECT e.*,f.terminal_type AS anchor_terminal,
       CASE WHEN d.is_relief_refinance IS TRUE THEN 'relief' WHEN d.is_relief_refinance IS FALSE THEN 'non_relief' ELSE 'unknown' END AS segment
      FROM expected_events e JOIN fact_loan_month f ON e.loan_id=f.loan_id AND e.confirmation_month=f.period
       JOIN dim_loan d ON e.loan_id=d.loan_id), ends AS(SELECT loan_id,max(period) AS last_period FROM fact_loan_month GROUP BY loan_id),
      inspected AS(SELECT a.loan_id,a.confirmation_month,a.event_type,a.segment,a.anchor_terminal,h.horizon,
       m.i,f.period,f.delinquency_state,f.terminal_type,x.last_period,
       a.confirmation_month+interval '1 month'*m.i AS wanted_month
       FROM anchors a JOIN ends x USING(loan_id) CROSS JOIN (VALUES(6),(12)) h(horizon)
       CROSS JOIN range(1,13) m(i) LEFT JOIN fact_loan_month f
       ON a.loan_id=f.loan_id AND f.period=a.confirmation_month+interval '1 month'*m.i WHERE m.i<=h.horizon),
      stop_at AS(SELECT loan_id,confirmation_month,event_type,segment,anchor_terminal,horizon,
       min(i) FILTER(WHERE period IS NULL OR delinquency_state='UNKNOWN' OR terminal_type IS NOT NULL) AS bad_month
       FROM inspected GROUP BY ALL)
      SELECT s.loan_id,s.confirmation_month,s.event_type,s.segment,s.horizon,
       CASE WHEN s.anchor_terminal IS NOT NULL THEN 'terminal_at_confirmation'
        WHEN s.bad_month IS NULL THEN 'complete_nonterminal_followup'
        WHEN f.period IS NULL AND f.wanted_month>f.last_period THEN 'end_of_source'
        WHEN f.period IS NULL THEN 'interrupted_gap'
        WHEN f.delinquency_state='UNKNOWN' THEN 'interrupted_unknown' ELSE 'terminal_exit' END AS followup_status,
       CASE WHEN s.anchor_terminal IS NOT NULL THEN 0 WHEN s.bad_month IS NULL THEN s.horizon ELSE s.bad_month-1 END AS observed
       FROM stop_at s LEFT JOIN inspected f ON s.loan_id=f.loan_id AND s.confirmation_month=f.confirmation_month
        AND s.event_type=f.event_type AND s.horizon=f.horizon AND f.i=s.bad_month''')
    cells=con.execute('''SELECT coalesce(segment,'all') AS segment,event_type,horizon AS horizon_months,
       followup_status,count(*) AS events,count(DISTINCT loan_id) AS distinct_loans,sum(observed) AS observed_nonterminal_months_sum
       FROM expected_followup GROUP BY GROUPING SETS((segment,event_type,horizon,followup_status),(event_type,horizon,followup_status))
       ORDER BY segment,event_type,horizon_months,followup_status''').fetchall()
    names=[c[0] for c in con.description];expected=[dict(zip(names,r)) for r in cells]
    actual=service.episode_followup(CASE)
    assert actual['rows']==expected and actual['audited_events']==event_count
    print('Independent follow-up grid matches:',len(expected),'groups',flush=True)
    scopes=0
    for segment in ['all','relief','non_relief','unknown']:
        for year in ['all','1990']:
            p=service.report(CASE,{'segment':segment,'transition_year':year,'from':'2020-01','to':'2020-02','horizon':'6'})['supplemental_evidence']['episode_followup']
            assert p['rows']==[r for r in expected if r['segment']==segment]
            assert p['filters_applied']==['segment'] and p['filter_context']=={'segment':segment,'horizons_months':[6,12]}
            scopes+=1
    # Check timeline projector against canonical/event source for event-type representatives.
    index=ROOT/'artifacts/private'/CASE/'loan-index.parquet';con.read_parquet(str(index)).create_view('loan_index')
    choices=con.execute('''SELECT event_type,min(loan_key) AS loan_key FROM expected_events e JOIN loan_index i USING(loan_id) GROUP BY event_type ORDER BY event_type''').fetchall()
    timeline_checks=[]
    for event,token in choices:
        raw=con.execute('SELECT loan_id FROM loan_index WHERE loan_key=?',[token]).fetchone()[0]
        t=service.timeline(CASE,token)
        events=con.execute('SELECT confirmation_month,event_type FROM expected_events WHERE loan_id=? ORDER BY confirmation_month,event_type',[raw]).fetchall()
        assert t['events']==[{'confirmation_month':d.isoformat(),'event_type':e} for d,e in events]
        months=con.execute('SELECT period,delinquency_state,terminal_type FROM fact_loan_month WHERE loan_id=? ORDER BY period',[raw]).fetchall()
        assert [(r['period'],r['delinquency_state'],r['terminal_type']) for r in t['months']]==[(d.isoformat(),s,term) for d,s,term in months]
        timeline_checks.append({'event_type':event,'loan_key':token,'events':len(events),'monthly_rows':len(months)})
    con.close();assert sha256(ledger)==before
    write_new(out/'followup.json',actual)
    write_new(out/'receipt.json',{'status':'PASS','requirement':'P2.06','case_id':CASE,'event_count':event_count,'event_differences':differences,'followup_cells':len(expected),'followup_event_horizon_checks':event_count*2,
        'export_scopes_checked':scopes,'timeline_checks':timeline_checks,'source_inputs':inputs,'case_receipt_sha256':sha256(ROOT/'artifacts/private'/CASE/'case-complete.json'),
        'ledger_unchanged':True,'independent_method':'Set-based continuity blocks,CURRENT runs,D3 anchors and first-confirmation relations;dense future-month grid',
        'methods':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'src/credit_atlas/episode_followup.py',ROOT/'src/credit_atlas/service.py',ROOT/'vendor/credit_risk_strategy_lab/src/crsl/episodes.py']}})
    print(out);print(json.dumps({'status':'PASS','events':event_count,'followup_cells':len(expected),'timeline_types':len(choices)}))

if __name__=='__main__':
    try:run()
    except Exception as error:
        if RUN_OUT is not None:write_new(RUN_OUT/'failed.json',{'status':'FAIL','error_type':type(error).__name__,'error':str(error)})
        raise
