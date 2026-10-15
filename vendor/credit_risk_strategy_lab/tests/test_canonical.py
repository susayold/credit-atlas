import duckdb
import pytest
from crsl.canonical import create_views, clean_expr, ENUMS
from crsl.ingest import stage_member

def prepare(db,make_record,make_zip,tmp_path,orig_changes=None,perf_changes=None):
    orig={k:sorted(v- {''})[0] if v-{''} else '' for k,v in ENUMS['origination'].items()}
    orig.update(amortization_type='FRM',harp='N',original_dti='0',original_ltv='80',first_time_homebuyer='N')
    orig.update(orig_changes or {})
    perf={k:sorted(v)[0] for k,v in ENUMS['performance'].items()}
    perf.update(delinquency='00',mi_cancellation='7')
    perf.update(perf_changes or {})
    archive=make_zip(origination=[make_record('origination',**orig)],performance=[make_record('performance',**perf)])
    for table,member in [('origination','sample_orig_2012.txt'),('performance','sample_perf_2012.txt')]:
        result=stage_member(archive,member,table,tmp_path/table)
        db.read_parquet(result['staging_file']).create_view(table)

def test_field_specific_nulls_zero_and_raw_preservation(make_record,make_zip,tmp_path):
    with duckdb.connect() as db:
        prepare(db,make_record,make_zip,tmp_path,{'vantagescore':'9999','original_dti':'0','mi_percent':'0','original_ltv':'999'})
        create_views(db)
        row=db.execute('SELECT vantagescore,original_dti,mi_percent,original_ltv,raw_original_ltv,origination_year FROM dim_loan').fetchone()
        assert row==(None,0,0,None,'999',2012)

def test_sales_not_automatically_default(make_record,make_zip,tmp_path):
    with duckdb.connect() as db:
        prepare(db,make_record,make_zip,tmp_path,perf_changes={'zero_balance_code':'15','delinquency':'00'})
        create_views(db)
        assert db.execute('SELECT delinquency_state,terminal_type FROM fact_loan_month').fetchone()==('CURRENT','OTHER_TERMINATION')

def test_harp_subset_requires_ltv_over_80(make_record,make_zip,tmp_path):
    with duckdb.connect() as db:
        prepare(db,make_record,make_zip,tmp_path,{'harp':'Y','original_ltv':'80'})
        create_views(db)
        assert db.execute('SELECT is_relief_refinance,is_harp_subset FROM dim_loan').fetchone()==(True,False)

def test_unknown_enum_fail_closed(make_record,make_zip,tmp_path):
    with duckdb.connect() as db:
        prepare(db,make_record,make_zip,tmp_path,{'channel':'Z'})
        with pytest.raises(ValueError,match='Unknown source enum'): create_views(db)

def test_integer_cast_does_not_round_silently(make_record,make_zip,tmp_path):
    with duckdb.connect() as db:
        prepare(db,make_record,make_zip,tmp_path,{'original_dti':'20.5'})
        with pytest.raises(ValueError,match='Nonintegral'): create_views(db)

@pytest.mark.parametrize('field,table,value,expected',[
 ('original_dti','origination','999',None),('original_dti','origination','0',0),
 ('current_upb','performance','999',999),('current_upb','performance','0',0),
 ('actual_loss','performance','',None),('actual_loss','performance','-10',-10),
 ('eltv','performance','999',None),('mi_percent','origination','0',0),
 ('msa','origination','00123','00123'),('postal_code','origination','000',None)])
def test_conversion_contract(field,table,value,expected):
    with duckdb.connect() as db:
        result=db.execute(f'SELECT {clean_expr(field,table)} FROM (SELECT ? AS "{field}")',[value]).fetchone()[0]
        assert result==expected
