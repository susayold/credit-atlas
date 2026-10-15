from pathlib import Path
import duckdb
from crsl.spike import diagnostic_tables
from crsl.ingest import stage_member

def test_spike_writes_private_trajectories_and_completion(make_zip,make_record,tmp_path):
    import json
    import shutil
    from crsl.cli import inspect_archive
    from crsl.spike import run
    root=tmp_path/'project'
    shutil.copytree(Path(__file__).resolve().parents[1]/'sql', root/'sql')
    periods=[f'2012{month:02d}' for month in range(1,13)]+['201301']
    archive=make_zip(performance=[make_record('performance',period=p) for p in periods])
    source_run,_=inspect_archive(root,archive,'annual_sample')
    output=run(root,source_run)
    complete=json.loads((output/'run-complete.json').read_text())
    assert complete['status']=='DIAGNOSTICS_COMPLETE'
    assert not complete['research_ready']
    assert not complete['public_release_approved']
    with duckdb.connect() as db:
        assert db.read_parquet(str(output/'profile.parquet')).count('*').fetchone()[0]==1
        assert db.read_parquet(str(output/'spotcheck_trajectories.parquet')).count('*').fetchone()[0]==13
    assert 'spotcheck_trajectories.parquet' in complete['outputs_sha256']

def test_d3_repeated_states_and_entry_are_separate(make_zip, make_record, tmp_path):
    archive = make_zip(performance=[
        make_record('performance', period='201201', delinquency='03'),
        make_record('performance', period='201202', delinquency='04'),
        make_record('performance', period='201203', delinquency='00',
                    zero_balance_code='01', actual_loss='')])
    with duckdb.connect() as db:
        for table, member in [('origination','sample_orig_2012.txt'),('performance','sample_perf_2012.txt')]:
            result=stage_member(archive,member,table,tmp_path/table)
            db.read_parquet(result['staging_file']).create_view(table)
        data=diagnostic_tables(db,Path(__file__).resolve().parents[1]/'sql')
        support=data['event_support'][0]
        assert support['ever_observed_d3_loans']==1
        assert support['already_d3_at_entry']==1
        assert support['populated_loss_loans']==0
        assert data['annual_support'][0]['d3_state_rows']==2
        assert data['terminal_support'][0]['zero_balance_code']=='01'

def test_empty_loss_is_not_zero_and_duplicate_terminal_flagged(make_zip,make_record,tmp_path):
    archive=make_zip(performance=[
        make_record('performance',period='201201',zero_balance_code='09',actual_loss=''),
        make_record('performance',period='201202',zero_balance_code='09',actual_loss='0')])
    with duckdb.connect() as db:
        for table,member in [('origination','sample_orig_2012.txt'),('performance','sample_perf_2012.txt')]:
            result=stage_member(archive,member,table,tmp_path/table)
            db.read_parquet(result['staging_file']).create_view(table)
        data=diagnostic_tables(db,Path(__file__).resolve().parents[1]/'sql')
        support=data['event_support'][0]
        assert support['multiple_terminal_loans']==1
        assert support['eligible_code_without_loss_rows']==1
        assert support['populated_loss_loans']==1
