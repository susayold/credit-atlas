from pathlib import Path
import duckdb
from crsl.attrition import create_attrition

def test_nulls_not_dropped_by_unpivot_and_grouping_not_outcome():
    with duckdb.connect() as db:
        db.execute('CREATE TABLE labels(loan_id VARCHAR,eligibility_reason VARCHAR,target INTEGER)')
        db.execute("INSERT INTO labels VALUES ('a','eligible',1),('b','eligible',NULL),('c','not_early_entry',NULL)")
        db.execute('CREATE TABLE dim_loan(loan_id VARCHAR,is_relief_refinance BOOLEAN,classic_fico INTEGER,original_dti INTEGER,original_ltv INTEGER,original_cltv INTEGER,original_upb INTEGER)')
        db.execute("INSERT INTO dim_loan VALUES ('a',false,700,0,80,80,100000),('b',false,750,NULL,90,90,200000),('c',true,650,NULL,95,95,150000)")
        create_attrition(db,Path(__file__).resolve().parents[1]/'sql')
        assert db.execute("SELECT loans,observed_values,missing_values,minimum FROM attrition_features WHERE feature='original_dti' AND entry_eligible").fetchone()==(2,1,1,0)
        assert db.execute("SELECT SUM(loans) FROM attrition_features WHERE feature='original_dti'").fetchone()[0]==3


def test_distribution_exactly_reproducible_under_row_order_and_thread_changes():
    results=[]
    for threads,order in [(1,'ASC'),(4,'DESC')]:
        with duckdb.connect() as db:
            db.execute(f'SET threads={threads}')
            db.execute(f'''CREATE TABLE labels AS SELECT i::VARCHAR AS loan_id,
                'eligible' AS eligibility_reason FROM range(30000) t(i) ORDER BY i {order}''')
            db.execute(f'''CREATE TABLE dim_loan AS SELECT i::VARCHAR AS loan_id,
                false AS is_relief_refinance, (500+i%340)::INTEGER AS classic_fico,
                (i%50)::INTEGER AS original_dti,(50+i%100)::INTEGER AS original_ltv,
                (60+i%90)::INTEGER AS original_cltv,(100000+i*137)::INTEGER AS original_upb
                FROM range(30000) t(i) ORDER BY i {order}''')
            create_attrition(db,Path(__file__).resolve().parents[1]/'sql')
            results.append(db.execute('SELECT * FROM attrition_features ORDER BY feature').fetchall())
    assert results[0]==results[1]
