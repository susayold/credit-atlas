from pathlib import Path
import pytest
from crsl.ingest import stage_member
from crsl.qualification import profile, qualify
from crsl.cli import inspect_archive

SQL = Path(__file__).resolve().parents[1]/"sql"

def measured(archive, destination):
    results = [stage_member(archive, member, table, destination/table)
       for table, member in (("origination","sample_orig_2012.txt"),
                             ("performance","sample_perf_2012.txt"))]
    result=profile(Path(results[0]["staging_file"]), Path(results[1]["staging_file"]), SQL)
    return results,result

def test_duplicate_month_and_gap(make_zip, make_record, tmp_path):
    rows=[make_record("performance",period="201201"),
          make_record("performance",period="201201"),
          make_record("performance",period="201203")]
    _, result=measured(make_zip(performance=rows),tmp_path/"staging")
    assert result["summary"]["duplicate_monthly_keys"] == 1
    assert result["summary"]["loans_with_gaps"] == 1
    assert result["summary"]["loans_with_13_contiguous_observed_months"] == 0

def test_orphan_and_no_history_are_not_hidden(make_zip,make_record,tmp_path):
    staged,result=measured(make_zip(performance=[make_record("performance",loan_id="F12Q10000002")]),
                          tmp_path/"staging")
    assert result["summary"]["orphan_performance_rows"] == 1
    assert result["summary"]["loans_without_performance"] == 1
    assert qualify("annual_sample",staged,result)["gates"]["referential_integrity"] == "FAIL"

def test_format_example_never_qualifies_even_perfect_profile():
    s={"duplicate_origination_keys":0,"duplicate_monthly_keys":0,
       "orphan_performance_rows":0,"loans_with_13_contiguous_observed_months":100000}
    result=qualify("format_example",[{"status":"PASS"}],{"summary":s})
    assert result["research_ready"] is False
    assert result["gates"]["source_qualification"] == "BLOCKED"

def test_annual_parse_not_equivalent_to_model_approval():
    s={"duplicate_origination_keys":0,"duplicate_monthly_keys":0,
       "orphan_performance_rows":0,"loans_with_13_contiguous_observed_months":100000}
    result=qualify("annual_sample",[{"status":"PASS"}],{"summary":s})
    assert result["gates"]["source_qualification"] == "CANDIDATE_FOR_COHORT_REVIEW"
    assert result["gates"]["model_training"] == "BLOCKED"
    assert result["research_ready"] is False

def test_row_counts_are_not_incident_events(make_zip,make_record,tmp_path):
    rows=[make_record("performance",period="201201",delinquency="03"),
          make_record("performance",period="201202",delinquency="04")]
    _,result=measured(make_zip(performance=rows),tmp_path/"staging")
    assert result["summary"]["d3plus_rows_not_incident_events"] == 2
    assert result["summary"]["performance_loans"] == 1

def test_synthetic_end_to_end_manifest(make_zip, tmp_path):
    import shutil, json
    root=tmp_path/"project"
    shutil.copytree(SQL,root/"sql")
    archive=make_zip(kind="format")
    run,result=inspect_archive(root,archive,"format_example",batch_size=1)
    assert result["status"] == "PROFILED"
    assert not result["research_ready"]
    assert (run/"run-complete.json").exists()
    complete=json.loads((run/"run-complete.json").read_text())
    assert complete["source_sha256"]
    assert complete["data_kind"] == "format_example"
    assert complete["public_release_approved"] is False

def test_release_checked_before_run_creation(tmp_path,make_zip):
    with pytest.raises(ValueError,match="Unsupported release"):
        inspect_archive(tmp_path,make_zip(),"annual_sample",release=46)

def test_git_unavailable_is_not_recorded_as_clean(tmp_path):
    from crsl.cli import git_state
    state = git_state(tmp_path)
    assert state["dirty"] is None
    assert state["status_available"] is False
