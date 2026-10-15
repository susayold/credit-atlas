from decimal import Decimal
from types import SimpleNamespace
import duckdb
import pytest
from credit_atlas.observed_loss_details import COMPONENTS,EXPENSES,report


def fixture(tmp_path):
    folder=tmp_path/'canonical';folder.mkdir()
    with duckdb.connect() as con:
        con.execute('CREATE TABLE f(loan_id VARCHAR,period DATE,zero_balance_date DATE,zero_balance_code VARCHAR,actual_loss DECIMAL(18,6),'+','.join(f+' DECIMAL(18,6)' for f in COMPONENTS+EXPENSES)+')')
        # Gain -20, complete expenses10; duplicate must not add99 to source sums.
        rows=[('A','2020-01-01','2020-01-01','09',-20,100,-130,0,10,0,0,2,3,4,1),
              ('A','2020-02-01','2020-01-01','09',99,100,0,0,10,0,0,2,3,4,1),
              ('B','2020-01-01','2020-01-01','02',0,0,0,0,0,0,0,0,0,0,0),
              ('C','2020-01-01','2020-01-01','03',None,100,None,None,None,None,None,None,None,None,None),
              ('D','2020-01-01','2020-01-01','01',500,100,0,0,0,0,0,0,0,0,0)]
        con.executemany('INSERT INTO f VALUES('+','.join('?' for _ in rows[0])+')',rows)
        con.execute('COPY f TO ? (FORMAT PARQUET)',[str(folder/'fact_loan_month.parquet')])
    service=SimpleNamespace(root=tmp_path,case=lambda _: {'manifest':{'canonical_run':'canonical','case_id':'d01-test','pipeline_run':'pipeline-test'}})
    return service


def test_signed_magnitude_missing_zero_and_duplicate(tmp_path):
    r=report(fixture(tmp_path),{'run':'d01-test'})
    assert r['selected_terminal_loans']==3 and r['duplicate_terminal_rows_removed']==1
    assert r['signed_ratio']['observations']==1 and Decimal(r['signed_ratio']['mean_exact'])==Decimal('-.2')
    assert Decimal(r['magnitude_ratio']['mean_exact'])==Decimal('.2')
    assert r['ratio_missing_or_zero_denominator']==1
    assert r['expense_formula']['checked_rows']==2 and Decimal(r['expense_formula']['max_abs_residual_exact'])==0
    assert r['loss_formula']['checked_rows']==2 and Decimal(r['loss_formula']['max_abs_residual_exact'])==0
    assert r['field_quality']['actual_loss']=={'known':2,'missing':1,'negative':1,'zero':1,'positive':0}
    assert r['expected_loss_dollars'] is None and r['filters_applied']==[]
    assert 'loan_id' not in str(r) and str(tmp_path) not in str(r)


@pytest.mark.parametrize('query',[{}, {'run':'x','segment':'all'},{'run':'x','horizon':'12'}])
def test_whole_source_query(tmp_path,query):
    with pytest.raises(ValueError,match='run only'):report(fixture(tmp_path),query)
