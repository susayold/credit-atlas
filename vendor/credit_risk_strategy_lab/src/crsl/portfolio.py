"""Real-data descriptive portfolio marts. Does not train models or publish raw data."""
import argparse
import json
import uuid
from pathlib import Path
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from .source import write_json_new,utc_now,sha256
from .cli import code_fingerprint
from .episodes import episode_events

def create_marts(db,sql_dir):
    db.execute('CREATE TEMP TABLE monthly AS '+(sql_dir/'portfolio_monthly.sql').read_text())
    db.execute('CREATE TEMP VIEW pairs AS '+(sql_dir/'transitions.sql').read_text())
    db.execute('''CREATE TEMP TABLE transition_matrix AS
      WITH grouped AS (
       SELECT delinquency_state AS origin,destination,COUNT(*) AS pairs,
        SUM(current_upb) AS opening_upb,COUNT(*) FILTER (WHERE current_upb IS NULL) AS missing_balance_pairs
       FROM pairs WHERE adjacent GROUP BY ALL
      ) SELECT *,pairs/SUM(pairs) OVER(PARTITION BY origin)::DOUBLE AS count_probability,
       opening_upb/NULLIF(SUM(opening_upb) OVER(PARTITION BY origin),0)::DOUBLE AS opening_balance_probability
      FROM grouped ORDER BY origin,destination''')
    bad=db.execute('''SELECT COUNT(*) FROM (
     SELECT origin FROM transition_matrix GROUP BY origin
     HAVING ABS(SUM(count_probability)-1)>1e-10 OR ABS(SUM(opening_balance_probability)-1)>1e-10)''').fetchone()[0]
    if bad: raise ValueError('Transition probabilities do not sum to one')

def run(root,canonical_run):
    source=json.loads((canonical_run/'run-complete.json').read_text())
    if source.get('status')!='CANONICAL_COMPLETE': raise ValueError('Completed canonical input required')
    destination=root/'artifacts/private'/('portfolio-'+uuid.uuid4().hex[:12]);destination.mkdir()
    manifest={'started_at':utc_now(),'canonical_run':canonical_run.name,'visibility':'private',
              'public_release_approved':False,'code_sha256':code_fingerprint(root),
              'evidence_class':'derived_observed_sample','model_training':False}
    write_json_new(destination/'run-start.json',manifest)
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        for table in ('dim_loan','fact_loan_month'):
            path=canonical_run/(table+'.parquet')
            if sha256(path)!=source['outputs_sha256'][path.name]: raise ValueError('Canonical input changed')
            db.read_parquet(str(path)).create_view(table)
        create_marts(db,root/'sql')
        for table in ('monthly','transition_matrix'):
            db.table(table).write_parquet(str(destination/(table+'.parquet')),compression='zstd')
        diagnostics=[{'destination':r[0],'rows':r[1]} for r in db.execute(
            'SELECT destination,COUNT(*) FROM pairs WHERE NOT adjacent GROUP BY 1 ORDER BY 1').fetchall()]
        selected=db.execute('SELECT loan_id,period,delinquency_state,terminal_type FROM fact_loan_month ORDER BY loan_id,period')
        def stream():
            while batch:=selected.fetchmany(10000):
                yield from batch
        schema=pa.schema([('loan_id',pa.string()),('confirmation_month',pa.date32()),('event_type',pa.string())])
        counts={}; buffer=[]
        with pq.ParquetWriter(destination/'episodes.parquet',schema,compression='zstd') as writer:
            for loan,month,event in episode_events(stream()):
                counts[event]=counts.get(event,0)+1
                buffer.append(dict(loan_id=loan,confirmation_month=month,event_type=event))
                if len(buffer)==10000:
                    writer.write_table(pa.Table.from_pylist(buffer,schema=schema));buffer=[]
            if buffer: writer.write_table(pa.Table.from_pylist(buffer,schema=schema))
    write_json_new(destination/'summary.json',{'nonadjacent_pairs':diagnostics,'episode_events':counts,
        'limitations':['Lifetime sample descriptors, not default12m rates or collection treatment effects.',
                       'Matrix includes only adjacent pairs; non-adjacent observations reported separately.',
                       'Opening balance weighting is a stock exposure weight, not a causal weight.']})
    manifest.update(completed_at=utc_now(),status='PORTFOLIO_MARTS_COMPLETE',
                    outputs_sha256={p.name:sha256(p) for p in destination.glob('*.parquet')})
    write_json_new(destination/'run-complete.json',manifest)
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--canonical-run',type=Path,required=True)
    args=parser.parse_args()
    print(run(Path(__file__).resolve().parents[2],args.canonical_run.resolve()))
