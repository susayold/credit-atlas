"""Repeatable private source diagnostics; deliberately does not construct targets."""
from __future__ import annotations
import argparse
import json
import uuid
from pathlib import Path
import duckdb
from .source import sha256, utc_now, write_json_new
from .cli import code_fingerprint

def rows(db, sql):
    query = db.execute(sql)
    names = [item[0] for item in query.description]
    return [dict(zip(names, row)) for row in query.fetchall()]

def diagnostic_tables(db, sql_dir: Path) -> dict:
    db.execute('CREATE TEMP TABLE loan_profile AS ' +
               (sql_dir/'profile_events.sql').read_text(encoding='utf-8').rstrip(';\n'))
    return {
      'event_support': rows(db, """SELECT COUNT(*) AS loans,
        COUNT(*) FILTER (WHERE first_observed_d3_period IS NOT NULL) AS ever_observed_d3_loans,
        COUNT(*) FILTER (WHERE TRY_CAST(first_status AS INTEGER) BETWEEN 3 AND 99) AS already_d3_at_entry,
        COUNT(*) FILTER (WHERE ever_reo) AS ever_reo_loans,
        COUNT(*) FILTER (WHERE terminal_rows>1) AS multiple_terminal_loans,
        COUNT(*) FILTER (WHERE populated_loss_rows>0) AS populated_loss_loans,
        SUM(loss_rows_unexpected_terminal) AS loss_rows_unexpected_terminal,
        SUM(loss_rows_with_defect) AS loss_rows_with_defect,
        SUM(eligible_code_without_loss_rows) AS eligible_code_without_loss_rows
        FROM loan_profile"""),
      'entry_age': rows(db, """SELECT first_observed_age, COUNT(*) AS loans
        FROM loan_profile GROUP BY ALL ORDER BY first_observed_age"""),
      'terminal_support': rows(db, """SELECT zero_balance_code,
        COUNT(*) AS monthly_rows, COUNT(DISTINCT loan_id) AS loans,
        COUNT(*) FILTER (WHERE TRIM(actual_loss)<>'') AS populated_loss_rows
        FROM performance WHERE TRIM(zero_balance_code)<>'' GROUP BY ALL ORDER BY 1"""),
      'annual_support': rows(db, """SELECT SUBSTR(period,1,4) AS calendar_year,
        COUNT(*) AS monthly_rows, COUNT(DISTINCT loan_id) AS observed_loans,
        COUNT(*) FILTER (WHERE TRY_CAST(delinquency AS INTEGER) BETWEEN 3 AND 99) AS d3_state_rows,
        COUNT(*) FILTER (WHERE TRIM(actual_loss)<>'') AS populated_loss_rows
        FROM performance GROUP BY ALL ORDER BY 1"""),
      'first_d3_by_year': rows(db, """SELECT SUBSTR(first_observed_d3_period,1,4) AS first_observed_d3_year,
        COUNT(*) AS loans FROM loan_profile WHERE first_observed_d3_period IS NOT NULL
        GROUP BY ALL ORDER BY 1"""),
      'raw_origination_values': rows(db, """SELECT 'classic_fico' AS field, classic_fico AS raw_value, COUNT(*) AS loans FROM origination GROUP BY 2
        UNION ALL SELECT 'vantagescore', vantagescore, COUNT(*) FROM origination GROUP BY 2
        UNION ALL SELECT 'harp', harp, COUNT(*) FROM origination GROUP BY 2
        UNION ALL SELECT 'original_dti', original_dti, COUNT(*) FROM origination GROUP BY 2
        UNION ALL SELECT 'property_valuation_method', property_valuation_method, COUNT(*) FROM origination GROUP BY 2
        ORDER BY 1,2"""),
    }

def run(root: Path, source_run: Path) -> Path:
    complete = json.loads((source_run/'run-complete.json').read_text())
    result = json.loads((source_run/'result.json').read_text())
    if complete['data_kind'] != 'annual_sample' or result['status'] != 'PROFILED':
        raise ValueError('A completed annual sample profile is required')
    if result['gates']['source_qualification'] != 'CANDIDATE_FOR_COHORT_REVIEW':
        raise ValueError('Source integrity screen must pass before event diagnostics')
    destination = root/'artifacts/private'/('spike-' + uuid.uuid4().hex[:12])
    destination.mkdir(parents=True, exist_ok=False)
    inputs = {table: source_run/table/'staging.parquet' for table in ('origination','performance')}
    write_json_new(destination/'run-start.json', {
        'started_at':utc_now(), 'source_run':source_run.name,
        'source_sha256':complete['source_sha256'], 'code_sha256':code_fingerprint(root),
        'staging_sha256':{k:sha256(v) for k,v in inputs.items()},
        'visibility':'private', 'research_ready':False})
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        for table, path in inputs.items():
            db.read_parquet(str(path)).create_view(table)
        tables = diagnostic_tables(db, root/'sql')
        db.table('loan_profile').write_parquet(str(destination/'profile.parquet'), compression='zstd')
        # Reproducible pseudorandom ranking (seed is part of the string) + explicit edge cases.
        db.execute("""CREATE TEMP TABLE selected AS SELECT loan_id, 'seed_20260910' AS reason
          FROM loan_profile ORDER BY md5(loan_id || ':20260910') LIMIT 10""")
        db.execute("""INSERT INTO selected SELECT loan_id, 'edge' FROM loan_profile
          WHERE observed_rows<13 OR first_observed_d3_period IS NOT NULL OR populated_loss_rows>0
          QUALIFY ROW_NUMBER() OVER (PARTITION BY observed_rows<13,
            first_observed_d3_period IS NOT NULL, populated_loss_rows>0 ORDER BY loan_id)=1""")
        db.sql("SELECT p.* FROM performance p SEMI JOIN selected s USING(loan_id)").write_parquet(
            str(destination/'spotcheck_trajectories.parquet'), compression='zstd')
        db.table('selected').write_parquet(str(destination/'spotcheck_selection.parquet'))
        counts = rows(db, 'SELECT COUNT(*) AS selected_rows, COUNT(DISTINCT loan_id) AS selected_loans FROM selected')
    write_json_new(destination/'diagnostics.json', {'tables':tables, 'spotcheck':counts,
        'notes':['First observed D3 is not necessarily a new incident or a validated horizon label.',
                 'Loss presence does not establish complete resolved losses or LGD eligibility.',
                 '2012 acquisition vintage alone cannot validate a multi-vintage model.'],
        'research_ready':False})
    write_json_new(destination/'run-complete.json', {'completed_at':utc_now(),
        'status':'DIAGNOSTICS_COMPLETE', 'source_run':source_run.name,
        'outputs_sha256':{p.name:sha256(p) for p in destination.iterdir() if p.is_file()},
        'research_ready':False, 'public_release_approved':False})
    return destination

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[2], args.source_run.resolve()))
