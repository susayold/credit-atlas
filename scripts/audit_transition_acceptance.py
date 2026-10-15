"""P2.05 source-wide independent LAG reconstruction and filter/export audit."""
import json
import math
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.service import ResearchService
from credit_atlas.workspace import contained,sha256,write_new

ROOT=Path(__file__).resolve().parents[1]
CASE='d01-a24484b21a21'
RUN_OUT=None

def run():
    global RUN_OUT
    out=ROOT/'artifacts/private'/('transition-acceptance-'+uuid4().hex[:12]);out.mkdir()
    RUN_OUT=out
    ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    service=ResearchService(ROOT,review_path=out/'qa-reviews.sqlite3')
    case=service.case(CASE);manifest=case['manifest'];actual=service.period_transitions(CASE)
    inputs=[]
    for entry in manifest['verified_inputs']:
        if Path(entry['path']).name in {'dim_loan.parquet','fact_loan_month.parquet','transition_matrix.parquet','transitions.parquet'}:
            path=contained(ROOT,entry['path']);assert sha256(path)==entry['sha256'];inputs.append(entry)
    assert len(inputs)==4
    con=duckdb.connect();con.execute("SET memory_limit='1GB'");con.execute('SET threads=2');con.execute('SET temp_directory=?',[str(out/'tmp')])
    for name in ['dim_loan','fact_loan_month']:
        con.read_parquet(str(contained(ROOT,manifest['canonical_run'])/(name+'.parquet'))).create_view(name)
    # Traverse backwards from the destination, rather than reusing engine LEAD SQL.
    con.execute('''CREATE TEMP TABLE independent_pairs AS
      WITH previous AS (
       SELECT *,lag(period) OVER w AS prior_period,lag(delinquency_state) OVER w AS prior_state,
        lag(current_upb) OVER w AS prior_upb,lag(terminal_type) OVER w AS prior_terminal
       FROM fact_loan_month WINDOW w AS (PARTITION BY loan_id ORDER BY period))
      SELECT p.loan_id,prior_period,prior_state AS origin,coalesce(terminal_type,delinquency_state) AS destination,prior_upb AS opening_upb,
       CASE WHEN is_relief_refinance IS TRUE THEN 'relief' WHEN is_relief_refinance IS FALSE THEN 'non_relief' ELSE 'unknown' END AS segment
      FROM previous p JOIN dim_loan d USING(loan_id)
      WHERE prior_period IS NOT NULL AND prior_terminal IS NULL AND date_diff('month',prior_period,period)=1''')
    count=con.execute('SELECT count(*) FROM independent_pairs').fetchone()[0]
    assert count==actual['adjacent_pairs']==4460559
    con.execute('''CREATE TEMP TABLE independent_cells AS SELECT year(prior_period)::INTEGER AS reporting_year,
      coalesce(segment,'all') AS segment,origin,destination,count(*) AS pairs,count(DISTINCT loan_id) AS distinct_loans,
      sum(opening_upb) AS opening_upb,count(*) FILTER(WHERE opening_upb IS NULL) AS missing_balance_pairs
      FROM independent_pairs GROUP BY GROUPING SETS((reporting_year,segment,origin,destination),(segment,origin,destination),
       (reporting_year,origin,destination),(origin,destination))''')
    rows=con.execute('SELECT * FROM independent_cells').fetchall()
    names=[d[0] for d in con.description];expected={}
    for values in rows:
        r=dict(zip(names,values));expected[(r['reporting_year'],r['segment'],r['origin'],r['destination'])]=r
    served=actual['rows']+actual['lifetime_rows'];assert len(served)==len(expected)
    max_probability_error=0;amount_checks=0;origin_groups={}
    for key,r in expected.items():
        group=key[:3];bucket=origin_groups.setdefault(group,{'pairs':0,'upb':None})
        bucket['pairs']+=r['pairs']
        if r['opening_upb'] is not None:bucket['upb']=(bucket['upb'] or Decimal(0))+r['opening_upb']
    for r in served:
        key=(r['reporting_year'],r['segment'],r['origin'],r['destination']);e=expected[key];g=origin_groups[key[:3]]
        for metric in ['pairs','distinct_loans','missing_balance_pairs']:assert r[metric]==e[metric]
        assert r['origin_pairs']==g['pairs']
        assert r['opening_upb']==(float(e['opening_upb']) if e['opening_upb'] is not None else None)
        assert r['origin_opening_upb']==(float(g['upb']) if g['upb'] is not None else None)
        amount_checks+=2
        for metric,value in [('count_probability',e['pairs']/g['pairs']),('balance_probability',None if e['opening_upb'] is None or not g['upb'] else float(e['opening_upb']/g['upb']))]:
            if value is None:assert r[metric] is None
            else:
                error=abs(r[metric]-value);max_probability_error=max(max_probability_error,error);assert error<=1e-12
        assert r['sparse_cell']==(e['distinct_loans']<30)
    scoped=0
    for segment in ['all','relief','non_relief','unknown']:
        for year in ['all',*[str(y) for y in actual['reporting_years']],'1990']:
            # Export is source-scoped; chart dates do not alter transition years.
            q={'segment':segment,'basis':'balance','horizon':'6','transition_year':year,'from':'2020-01','to':'2020-02'}
            report=service.report(CASE,q);projection=report['supplemental_evidence']['period_transitions']
            wanted=[r for r in actual['rows'] if r['segment']==segment and (year=='all' or r['reporting_year']==int(year))]
            assert projection['rows']==wanted
            assert projection['lifetime_rows']==[r for r in actual['lifetime_rows'] if r['segment']==segment]
            assert projection['filter_context']=={'segment':segment,'transition_year':year}
            assert projection['filters_applied']==['segment','transition_year']
            assert 'lifetime_rows retain' in projection['scope_note']
            scoped+=1
    con.close();assert sha256(ledger)==before
    write_new(out/'period-transitions.json',actual)
    write_new(out/'receipt.json',{'status':'PASS','requirement':'P2.05','case_id':CASE,'pipeline_run':manifest['pipeline_run'],'source_years':manifest['source_years'],
        'adjacent_pairs':count,'year_cells':len(actual['rows']),'lifetime_cells':len(actual['lifetime_rows']),'independent_method':'Destination-side LAG from full canonical panel;no engine transition SQL reused',
        'source_inputs_verified':inputs,'origin_and_cell_amount_checks':amount_checks,'max_probability_error':max_probability_error,'probability_tolerance':1e-12,
        'export_scopes_checked':scoped,'export_numbers':'Existing JSON uses floats;exact Decimal sums are verified before conversion;not an accounting ledger',
        'ledger_unchanged':True,'methods':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'src/credit_atlas/period_transitions.py',ROOT/'src/credit_atlas/service.py',ROOT/'vendor/credit_risk_strategy_lab/sql/transitions.sql']},
        'raw_case_receipt_sha256':sha256(ROOT/'artifacts/private'/CASE/'case-complete.json'),'audit_scope':'Current descriptive transition requirement;multi-vintage/OOT models remain outside this acceptance'})
    print(out);print(json.dumps({'status':'PASS','adjacent_pairs':count,'cells':len(served),'export_scopes':scoped}))

if __name__=='__main__':
    try:run()
    except Exception as error:
        if RUN_OUT is not None:write_new(RUN_OUT/'failed.json',{'status':'FAIL','requirement':'P2.05','error_type':type(error).__name__,'error':str(error)})
        raise
