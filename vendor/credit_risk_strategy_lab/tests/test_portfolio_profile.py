from pathlib import Path

import duckdb

from crsl.portfolio_profile import build
from crsl.portfolio_profile_export import load
from crsl.source import sha256


SQL = Path(__file__).resolve().parents[1] / 'sql'


def dim_rows():
    return [
        ('a', True, 610, 85, 45, 90, 200000, 360, 1, 'P', 'P', 'R', 'SF', 'Y', 'FRM'),
        ('b', False, 780, 70, None, 70, 300000, 360, 1, 'I', 'C', 'B', 'CO', 'N', 'FRM'),
        ('c', None, None, None, 30, None, 100000, None, 2, '9', '9', '9', '9', '9', 'ARM'),
    ]


def test_profile_has_unknown_segment_and_reconciles_each_dimension():
    with duckdb.connect() as db:
        db.execute('''CREATE TABLE dim_loan(
            loan_id VARCHAR,is_relief_refinance BOOLEAN,classic_fico INTEGER,
            original_ltv INTEGER,original_dti INTEGER,original_cltv INTEGER,
            original_upb DECIMAL(18,2),original_term INTEGER,units INTEGER,
            occupancy VARCHAR,loan_purpose VARCHAR,channel VARCHAR,property_type VARCHAR,
            first_time_homebuyer VARCHAR,amortization_type VARCHAR)''')
        db.executemany('INSERT INTO dim_loan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', dim_rows())
        rows = build(db, SQL).fetchall()
    assert len(rows) > 0
    assert {row[0] for row in rows} == {'relief', 'non_relief', 'unknown_relief'}
    for segment in {'relief', 'non_relief', 'unknown_relief'}:
        for dimension in {row[2] for row in rows if row[0] == segment}:
            cells = [row for row in rows if row[0] == segment and row[2] == dimension]
            assert sum(row[4] for row in cells) == cells[0][8]
            assert abs(sum(row[11] for row in cells) - 1) < 1e-10
            assert all(row[5] + row[6] == row[4] for row in cells)


def test_profile_export_is_hash_checked_and_id_free(tmp_path):
    canonical = tmp_path / 'canonical'
    profile = tmp_path / 'profile'
    canonical.mkdir()
    profile.mkdir()
    with duckdb.connect() as db:
        db.execute('''COPY (SELECT * FROM (VALUES
          ('relief',1,'classic_fico','780+',2,2,0,100.0,2,2,100.0,1.0,1.0)
        ) t(segment,dimension_order,dimension,bucket,loans,known_upb_loans,missing_upb_loans,
            opening_upb,segment_loans,segment_known_upb_loans,segment_opening_upb,count_share,balance_share))
        TO ? (FORMAT PARQUET)''', [str(profile / 'profile.parquet')])
        db.execute('''COPY (SELECT * FROM (VALUES ('a',TRUE)) t(loan_id,is_relief_refinance))
                     TO ? (FORMAT PARQUET)''', [str(canonical / 'dim_loan.parquet')])
    (canonical / 'run-complete.json').write_text(
        '{"status":"CANONICAL_COMPLETE","outputs_sha256":{"dim_loan.parquet":"%s"}}'
        % sha256(canonical / 'dim_loan.parquet'))
    (profile / 'run-complete.json').write_text(
        '{"status":"PORTFOLIO_PROFILE_COMPLETE","canonical_run":"canonical",'
        '"canonical_sha256":"%s","outputs_sha256":{"profile.parquet":"%s"}}'
        % (sha256(canonical / 'run-complete.json'), sha256(profile / 'profile.parquet')))
    result = load(tmp_path, canonical, profile)
    assert result['status'] == 'verified_development'
    assert result['rows'][0]['dimension'] == 'classic_fico'
    assert 'loan_id' not in result['rows'][0]
