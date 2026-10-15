"""Observation/label contracts. Only completed immutable canonical runs are accepted."""
from __future__ import annotations
import argparse
import json
import uuid
from pathlib import Path
import duckdb
from .source import sha256,write_json_new,utc_now
from .cli import code_fingerprint

def create_labels(db, sql_dir, config):
    horizon=config['horizon_months']
    minimum=config['early_entry_min_age']; maximum=config['early_entry_max_age']
    if any(type(x) is not int for x in (horizon,minimum,maximum)) or not (1<=horizon<=60 and 0<=minimum<=maximum<=12):
        raise ValueError('Invalid integer horizon/entry ages')
    # Reject unsupported semantic changes instead of silently ignoring configuration.
    expected={'landmark':'first_observed_month',
      'require_source_and_contractual_age_agreement':True,'exclude_modified_at_entry':True,
      'endpoint':'numeric_delinquency_03_through_99','prepayment_estimand':'event_before_prepayment',
      'same_month_d3_and_exit':'d3_priority_at_monthly_resolution',
      'unknown_or_gap_before_outcome':'unavailable',
      'relief_refinance_policy':'retain_with_flag_and_segmented_diagnostics'}
    if any(config.get(k)!=v for k,v in expected.items()):
        raise ValueError('Unsupported label semantics; implement and test before changing config')
    db.execute('CREATE TEMP TABLE observation AS '+(sql_dir/'observation.sql').read_text(encoding='utf-8'))
    invalid=db.execute("""SELECT COUNT(*) FROM observation WHERE terminal_rows>1
       OR first_terminal_month<last_observed_month""").fetchone()[0]
    if invalid:
        raise ValueError('Conflicting/repeated/post-terminal observations require review')
    query=(sql_dir/'labels.sql').read_text(encoding='utf-8').format(horizon=horizon,min_age=minimum,max_age=maximum)
    db.execute('CREATE TEMP TABLE labels AS '+query)
    n=db.execute('SELECT COUNT(*) FROM dim_loan').fetchone()[0]
    counts=db.execute('SELECT COUNT(*), COUNT(DISTINCT loan_id) FROM labels').fetchone()
    if counts!=(n,n): raise ValueError('Label cardinality does not reconcile')
    leakage=db.execute("""SELECT COUNT(*) FROM labels WHERE
      (target IS NOT NULL AND eligibility_reason<>'eligible')
      OR (target IS NOT NULL AND (unknown_to_stop>0 OR observed_to_stop<>required_to_stop))
      OR (target IS NOT NULL AND label_known_month>horizon_end)""").fetchone()[0]
    if leakage: raise ValueError('Label invariant failed')

def run(root, canonical_run):
    manifest=json.loads((canonical_run/'run-complete.json').read_text())
    if manifest.get('status')!='CANONICAL_COMPLETE': raise ValueError('Completed canonical run required')
    inputs={t:canonical_run/(t+'.parquet') for t in ('dim_loan','fact_loan_month')}
    for table,path in inputs.items():
        if sha256(path)!=manifest['outputs_sha256'][table+'.parquet']:
            raise ValueError('Canonical artifact changed')
    config=json.loads((root/'configs/cohort.json').read_text())
    destination=root/'artifacts/private'/('labels-'+uuid.uuid4().hex[:12])
    destination.mkdir(parents=True,exist_ok=False)
    start={'started_at':utc_now(),'canonical_run':canonical_run.name,
           'config':config,'code_sha256':code_fingerprint(root),'visibility':'private',
           'research_ready':False,'public_release_approved':False}
    write_json_new(destination/'run-start.json',start)
    try:
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            for table,path in inputs.items(): db.read_parquet(str(path)).create_view(table)
            create_labels(db,root/'sql',config)
            for table in ('observation','labels'):
                db.table(table).write_parquet(str(destination/(table+'.parquet')),compression='zstd')
            def fetch(query):
                result=db.execute(query)
                return [dict(zip([d[0] for d in result.description],r)) for r in result.fetchall()]
            # USD cents are reported as explicit decimal strings, avoiding float precision loss.
            summary={'eligibility':fetch("SELECT eligibility_reason,COUNT(*) AS loans, CAST(SUM(original_upb) AS VARCHAR) AS original_upb_usd FROM labels GROUP BY ALL ORDER BY 1"),
              'outcomes':fetch("SELECT outcome,COUNT(*) AS loans, CAST(SUM(original_upb) AS VARCHAR) AS original_upb_usd FROM labels GROUP BY ALL ORDER BY 1"),
              'segment_outcomes':fetch("SELECT is_relief_refinance,outcome,COUNT(*) AS loans FROM labels GROUP BY ALL ORDER BY 1,2"),
              'target':fetch('SELECT target,COUNT(*) AS loans FROM labels GROUP BY ALL ORDER BY 1')}
        write_json_new(destination/'summary.json',summary)
        start.update(completed_at=utc_now(),status='LABELS_DEVELOPMENT_COMPLETE',
            outputs_sha256={p.name:sha256(p) for p in destination.glob('*.parquet')},
            note='No research split or model authorized by this run; latest-release retrospective labels.')
        write_json_new(destination/'run-complete.json',start)
        return destination
    except Exception as error:
        write_json_new(destination/'run-failed.json',{'failed_at':utc_now(),'exception_type':type(error).__name__})
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical-run',type=Path,required=True)
    args=parser.parse_args()
    print(run(Path(__file__).resolve().parents[2],args.canonical_run.resolve()))
