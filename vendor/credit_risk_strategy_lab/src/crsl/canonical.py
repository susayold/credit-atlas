"""Release-47 canonical tables. Original raw fields and monthly states stay auditable."""
from __future__ import annotations
import argparse
import json
import uuid
from pathlib import Path
import duckdb
from .contracts import fields_for, ORIG_DATES, PERF_DATES, ORIG_NUMERIC, PERF_NUMERIC
from .source import write_json_new, utc_now, sha256
from .cli import code_fingerprint

# General User Guide Release 47 pp4-15. No global 9/99/999 replacement.
SENTINELS = {
 'classic_fico': '9999', 'vantagescore':'9999', 'mi_percent':'999',
 'units':'99', 'original_cltv':'999', 'original_dti':'999',
 'original_ltv':'999', 'borrowers':'99', 'property_valuation_method':'7',
 'first_time_homebuyer':'9', 'occupancy':'9', 'channel':'9',
 'property_type':'99', 'postal_code':'000', 'loan_purpose':'9',
 'eltv':'999', 'mi_cancellation':'7',
}
INTEGER_FIELDS={'classic_fico','vantagescore','units','original_cltv','original_dti',
 'original_ltv','original_term','borrowers','property_valuation_method',
 'loan_age','remaining_months','eltv'}
ENUMS={
 'origination':{
  'first_time_homebuyer':{'Y','N','9'},'occupancy':{'P','I','S','9'},
  'channel':{'R','B','C','T','9'},'prepayment_penalty':{'Y','N'},
  'amortization_type':{'FRM','ARM'},'property_type':{'CP','CO','PU','SF','MH','99'},
  'loan_purpose':{'P','C','N','R','9'},'super_conforming':{'Y','N'},
  'special_eligibility':{'','H','F','R'},'harp':{'Y','N'},'interest_only':{'Y','N'},
  'property_valuation_method':{'1','2','3','4','7'}},
 'performance':{
  'delinquency':{f'{i:02d}' for i in range(100)}|{'RA','XX'},
  'zero_balance_code':{'','01','02','03','09','15','16','96'},
  'modification':{'','Y','P'},'rate_step':{'','Y','N'},
  'payment_deferral':{'','C','P'},'disaster':{'','Y'},
  'assistance':{'','F','R','T'},'mi_cancellation':{'Y','N','7'}},
}

def clean_expr(field, table):
    raw=f'TRIM("{field}")'
    clean=f"NULLIF({raw}, '')"
    if field in SENTINELS:
        clean=f"NULLIF({clean}, '{SENTINELS[field]}')"
    dates=ORIG_DATES if table=='origination' else PERF_DATES
    numerics=ORIG_NUMERIC if table=='origination' else PERF_NUMERIC|{'net_sales_proceeds'}
    if field in dates:
        clean=f"CAST(strptime({clean}, '%Y%m') AS DATE)"
    elif field in numerics and field != 'msa':
        # Integer casts in DuckDB round; validate integrality before casting.
        clean=f"CAST({clean} AS {'INTEGER' if field in INTEGER_FIELDS else 'DECIMAL(18,6)'})"
    return clean

def assert_source(db):
    for table, enums in ENUMS.items():
        for field, accepted in enums.items():
            actual={r[0] for r in db.execute(f'SELECT DISTINCT TRIM("{field}") FROM {table}').fetchall()}
            if not actual <= accepted:
                raise ValueError(f'Unknown source enum {table}.{field}; review contract')
    for table in ('origination','performance'):
        for field in set(fields_for(table)) & INTEGER_FIELDS:
            number=f'CAST(NULLIF(TRIM("{field}"),\'\') AS DECIMAL(18,6))'
            if db.execute(f'SELECT COUNT(*) FROM {table} WHERE {number}<>trunc({number})').fetchone()[0]:
                raise ValueError(f'Nonintegral source value {table}.{field}')
    failures=db.execute("""SELECT
      (SELECT COUNT(*)-COUNT(DISTINCT loan_id) FROM origination),
      (SELECT COUNT(*) FROM (SELECT loan_id,period FROM performance GROUP BY ALL HAVING COUNT(*)>1)),
      (SELECT COUNT(*) FROM performance p ANTI JOIN origination o USING(loan_id)),
      (SELECT COUNT(*) FROM origination o ANTI JOIN performance p USING(loan_id))""").fetchone()
    if any(failures):
        raise ValueError('Source grain/referential integrity failed')

def create_views(db):
    assert_source(db)
    for table, target in [('origination','dim_loan'),('performance','fact_loan_month')]:
        columns=[f'"{f}" AS "raw_{f}"' for f in fields_for(table)]
        columns += [f'{clean_expr(f,table)} AS "{f}"' for f in fields_for(table)]
        columns += ['_source_line','47 AS source_release']
        if table=='origination':
            columns += ["2000+CAST(substr(loan_id,2,2) AS INTEGER) - CASE WHEN substr(loan_id,2,2)='99' THEN 100 ELSE 0 END AS origination_year",
                        'CAST(substr(loan_id,5,1) AS INTEGER) AS origination_quarter',
                        "harp='Y' AS is_relief_refinance",
                        f"harp='Y' AND {clean_expr('original_ltv',table)}>80 AS is_harp_subset"]
        else:
            columns += ["CASE WHEN delinquency='00' THEN 'CURRENT' WHEN delinquency='01' THEN 'D1' WHEN delinquency='02' THEN 'D2' WHEN TRY_CAST(delinquency AS INTEGER) BETWEEN 3 AND 99 THEN 'D3PLUS' WHEN delinquency='RA' THEN 'REO' ELSE 'UNKNOWN' END AS delinquency_state",
                        "CASE WHEN zero_balance_code='01' THEN 'PREPAID_OR_MATURED' WHEN zero_balance_code IN ('02','03','09') THEN 'CREDIT_TERMINATION' WHEN zero_balance_code IN ('15','16','96') THEN 'OTHER_TERMINATION' ELSE NULL END AS terminal_type"]
        db.execute(f'CREATE TEMP VIEW {target} AS SELECT '+',\n'.join(columns)+f' FROM {table}')
    expected=db.execute('SELECT COUNT(*) FROM fact_loan_month').fetchone()[0]
    joined=db.execute('SELECT COUNT(*) FROM fact_loan_month JOIN dim_loan USING(loan_id)').fetchone()[0]
    if joined!=expected:
        raise ValueError('Canonical join changed monthly cardinality')

def run(root: Path, source_run: Path):
    complete=json.loads((source_run/'run-complete.json').read_text())
    result=json.loads((source_run/'result.json').read_text())
    if complete.get('data_kind')!='annual_sample' or result.get('status')!='PROFILED':
        raise ValueError('Completed annual-source profile required')
    if result['gates']['source_qualification']!='CANDIDATE_FOR_COHORT_REVIEW':
        raise ValueError('Initial source qualification must pass')
    destination=root/'artifacts/private'/('canonical-'+uuid.uuid4().hex[:12])
    destination.mkdir(parents=True,exist_ok=False)
    inputs={t:source_run/t/'staging.parquet' for t in ('origination','performance')}
    manifest={'started_at':utc_now(),'source_run':source_run.name,'release':47,
              'source_sha256':complete['source_sha256'],'code_sha256':code_fingerprint(root),
              'staging_sha256':{t:sha256(p) for t,p in inputs.items()},
              'visibility':'private','public_release_approved':False,'research_ready':False}
    write_json_new(destination/'run-start.json',manifest)
    try:
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            for table,path in inputs.items(): db.read_parquet(str(path)).create_view(table)
            create_views(db)
            for table in ('dim_loan','fact_loan_month'):
                db.table(table).write_parquet(str(destination/(table+'.parquet')),compression='zstd')
            # Diagnostic summary excludes loan identifiers.
            measures=db.execute("""SELECT COUNT(*),COUNT(*) FILTER (WHERE classic_fico IS NULL),
              COUNT(*) FILTER (WHERE original_dti IS NULL), COUNT(*) FILTER (WHERE vantagescore IS NULL),
              COUNT(*) FILTER (WHERE is_relief_refinance),COUNT(*) FILTER (WHERE is_harp_subset)
              FROM dim_loan""").fetchone()
        summary=dict(zip(('loans','fico_missing','dti_missing','vs4_missing','relief_refinance_loans','harp_subset_loans'),measures))
        manifest.update(completed_at=utc_now(),status='CANONICAL_COMPLETE',summary=summary,
                        outputs_sha256={p.name:sha256(p) for p in destination.glob('*.parquet')})
        write_json_new(destination/'run-complete.json',manifest)
        return destination
    except Exception as error:
        write_json_new(destination/'run-failed.json',{'failed_at':utc_now(),'exception_type':type(error).__name__})
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run',type=Path,required=True)
    args=parser.parse_args()
    print(run(Path(__file__).resolve().parents[2],args.source_run.resolve()))
