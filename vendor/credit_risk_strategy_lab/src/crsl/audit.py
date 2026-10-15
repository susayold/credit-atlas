"""Private B03 diagnostics: source parity, field coverage and signed loss reconciliation."""
import argparse
import json
import uuid
from pathlib import Path
import duckdb
from .source import utc_now,sha256,write_json_new
from .contracts import fields_for
from .cli import code_fingerprint

def loss_checks(db,sql_dir,recent_start='2026-01-01'):
    from datetime import date
    date.fromisoformat(recent_start)
    db.execute('CREATE TEMP TABLE loss_audit AS '+(sql_dir/'loss_audit.sql').read_text().format(recent_start=recent_start))
    def rows(query):
        cur=db.execute(query)
        return [dict(zip([d[0] for d in cur.description],r)) for r in cur.fetchall()]
    return {'loss_availability':rows('SELECT availability_reason,zero_balance_code,COUNT(*) AS loans FROM loss_audit GROUP BY ALL ORDER BY 1,2'),
      'loss_reconciliation':rows("""SELECT COUNT(*) FILTER (WHERE actual_loss IS NOT NULL) AS reported,
        COUNT(*) FILTER (WHERE actual_loss IS NOT NULL AND loss_residual IS NULL) AS incomplete_formula,
        COUNT(*) FILTER (WHERE ABS(loss_residual)>0.01) AS loss_mismatch,
        COUNT(*) FILTER (WHERE ABS(expense_residual)>0.01) AS expense_mismatch,
        CAST(MAX(ABS(loss_residual)) AS VARCHAR) AS max_abs_loss_residual_usd,
        CAST(MAX(ABS(expense_residual)) AS VARCHAR) AS max_abs_expense_residual_usd
        FROM loss_audit""")}

def run(root,canonical_run):
    manifest=json.loads((canonical_run/'run-complete.json').read_text())
    if manifest.get('status')!='CANONICAL_COMPLETE': raise ValueError('Completed canonical input required')
    source_run=root/'artifacts/private'/manifest['source_run']
    output=root/'artifacts/private'/('audit-'+uuid.uuid4().hex[:12]); output.mkdir()
    start={'started_at':utc_now(),'canonical_run':canonical_run.name,
           'code_sha256':code_fingerprint(root),'visibility':'private','public_release_approved':False}
    write_json_new(output/'run-start.json',start)
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        for table in ('dim_loan','fact_loan_month'):
            path=canonical_run/(table+'.parquet')
            if sha256(path)!=manifest['outputs_sha256'][path.name]: raise ValueError('Input changed')
            db.read_parquet(str(path)).create_view(table)
        db.execute("""CREATE TEMP TABLE selected AS SELECT loan_id FROM dim_loan
         ORDER BY md5(loan_id||':20260910') LIMIT 10""")
        db.execute("""INSERT INTO selected SELECT loan_id FROM fact_loan_month
         WHERE actual_loss IS NOT NULL OR defect_settlement_date IS NOT NULL
           OR delinquency_state IN ('D3PLUS','REO','UNKNOWN') OR loan_age>12
         QUALIFY ROW_NUMBER() OVER (PARTITION BY actual_loss IS NOT NULL,
           defect_settlement_date IS NOT NULL,delinquency_state,loan_age>12 ORDER BY loan_id,period)=1""")
        parity={}
        for source,target in [('origination','dim_loan'),('performance','fact_loan_month')]:
            db.read_parquet(str(source_run/source/'staging.parquet')).create_view('raw_'+source)
            raw_cols=','.join('r."'+f+'"' for f in fields_for(source))
            typed_cols=','.join('c."raw_'+f+'"' for f in fields_for(source))
            # Symmetric set difference; complete-source uniqueness was checked separately.
            raw=f'SELECT {raw_cols} FROM raw_{source} r SEMI JOIN selected s USING(loan_id)'
            typed=f'SELECT {typed_cols} FROM {target} c SEMI JOIN selected s USING(loan_id)'
            n=db.execute(f'SELECT COUNT(*) FROM (({raw} EXCEPT {typed}) UNION ALL ({typed} EXCEPT {raw}))').fetchone()[0]
            parity[source]=n
        if any(parity.values()): raise ValueError('Raw/canonical spot-check mismatch')
        findings=loss_checks(db,root/'sql')
        findings['raw_parity_difference_rows']=parity
        findings['seed']=20260910
        findings['selected_loans']=db.execute('SELECT COUNT(DISTINCT loan_id) FROM selected').fetchone()[0]
        findings['relief_dti_crosscheck']=[{'is_relief_refinance':r[0],'loans':r[1],'dti_missing':r[2]} for r in
          db.execute('SELECT is_relief_refinance,COUNT(*),COUNT(*) FILTER (WHERE original_dti IS NULL) FROM dim_loan GROUP BY 1 ORDER BY is_relief_refinance').fetchall()]
        missing=[]
        # Row counts and availability by reporting year + terminal category; no future imputation.
        for field in fields_for('performance'):
            cur=db.execute(f"""SELECT year(period) AS year,coalesce(terminal_type,'NONTERMINAL') AS event_category,
              COUNT(*) AS monthly_rows,COUNT(*) FILTER (WHERE "{field}" IS NULL) AS null_rows
              FROM fact_loan_month GROUP BY ALL ORDER BY 1,2""")
            missing.extend({'field':field,'year':r[0],'event_category':r[1],'monthly_rows':r[2],'null_rows':r[3]} for r in cur.fetchall())
        findings['field_availability_by_year_event']=missing
        db.table('loss_audit').write_parquet(str(output/'loss_audit.parquet'),compression='zstd')
        db.sql('SELECT DISTINCT loan_id FROM selected').write_parquet(str(output/'spotcheck_loans.parquet'))
    write_json_new(output/'findings.json',findings)
    start.update(completed_at=utc_now(),status='AUDIT_COMPLETE',research_ready=False,
                 outputs_sha256={p.name:sha256(p) for p in output.iterdir() if p.is_file()})
    write_json_new(output/'run-complete.json',start)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--canonical-run',type=Path,required=True)
    args=parser.parse_args()
    print(run(Path(__file__).resolve().parents[2],args.canonical_run.resolve()))
