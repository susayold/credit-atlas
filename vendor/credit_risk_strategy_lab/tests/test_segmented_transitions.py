from pathlib import Path
import duckdb
import pytest
from crsl.segmented_transitions import build
from crsl.segmented_transition_export import load
from crsl.source import sha256


def test_segments_preserve_gaps_missing_balance_and_support():
    with duckdb.connect() as db:
        db.execute("CREATE TABLE dim_loan AS SELECT * FROM (VALUES ('a',TRUE),('b',FALSE)) t(loan_id,is_relief_refinance)")
        db.execute('''CREATE TABLE fact_loan_month AS SELECT * FROM (VALUES
          ('a',DATE '2020-01-01',100.0,'CURRENT',NULL::VARCHAR),
          ('a',DATE '2020-02-01',90.0,'D1',NULL),
          ('a',DATE '2020-04-01',80.0,'CURRENT',NULL),
          ('b',DATE '2020-01-01',NULL,'CURRENT',NULL),
          ('b',DATE '2020-02-01',NULL,'CURRENT',NULL)
        ) t(loan_id,period,current_upb,delinquency_state,terminal_type)''')
        rows = build(db, Path(__file__).resolve().parents[1] / 'sql').to_pylist()
        assert sum(r['pairs'] for r in rows) == 2
        missing = next(r for r in rows if r['segment'] == 'non_relief')
        assert missing['balance_probability'] is None
        assert missing['missing_balance_pairs'] == 1
        assert all(r['count_probability'] == 1 and r['sparse_cell'] for r in rows)


def test_duplicate_dimension_rejected():
    with duckdb.connect() as db:
        db.execute("CREATE TABLE dim_loan AS SELECT * FROM (VALUES ('a'),('a')) t(loan_id)")
        with pytest.raises(ValueError, match='Duplicate'):
            build(db, Path('sql'))


def test_export_load_is_hash_checked_and_id_free(tmp_path):
    run = tmp_path / 'segmented'
    run.mkdir()
    path = run / 'transitions.parquet'
    with duckdb.connect() as db:
        db.execute('''COPY (SELECT * FROM (VALUES
          ('relief','CURRENT','D1',4,2,100.0,0,4,1.0,1.0,FALSE)
        ) t(segment,origin,destination,pairs,distinct_loans,opening_upb,
            missing_balance_pairs,origin_pairs,count_probability,balance_probability,sparse_cell))
        TO ? (FORMAT PARQUET)''', [str(path)])
    (run / 'run-complete.json').write_text('''{"status":"SEGMENTED_TRANSITIONS_COMPLETE",
      "canonical_run":"canonical-test","adjacent_pairs":4,
      "outputs_sha256":{"transitions.parquet":"%s"}}''' % sha256(path))
    payload = load(tmp_path, run)
    assert payload['rows'][0]['segment'] == 'relief'
    assert 'loan_id' not in payload['rows'][0]
