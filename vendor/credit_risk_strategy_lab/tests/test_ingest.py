import pyarrow.parquet as pq
import pytest
from crsl.ingest import stage_member

def test_batching_preserves_strings_and_counts(make_record, make_zip, tmp_path):
    rows = [make_record("performance", current_upb="0"),
            make_record("performance", current_upb="")]
    archive = make_zip(performance=rows)
    result = stage_member(archive, "sample_perf_2012.txt", "performance", tmp_path/"staged", 1)
    data = pq.read_table(result["staging_file"]).to_pylist()
    assert result["rows"] == result["accepted"] == 2
    assert result["rejected"] == 0
    assert [r["current_upb"] for r in data] == ["0", ""]
    assert [r["_source_line"] for r in data] == [1, 2]

def test_quarantine_and_fail_not_silent_skip(make_record, make_zip, tmp_path):
    rows = [make_record("performance"), make_record("performance", delinquency="BAD")]
    archive = make_zip(performance=rows)
    result = stage_member(archive, "sample_perf_2012.txt", "performance", tmp_path/"staged")
    assert result["status"] == "FAIL"
    assert result["rows"] == result["accepted"] + result["rejected"] == 2
    assert "delinquency_unknown" in (tmp_path/"staged/quarantine.jsonl").read_text()
    assert "F12Q1" not in (tmp_path/"staged/quarantine.jsonl").read_text()

def test_repeated_ingestion_same_logical_content(make_zip, tmp_path):
    archive = make_zip()
    a = stage_member(archive, "sample_perf_2012.txt", "performance", tmp_path/"a", 1)
    b = stage_member(archive, "sample_perf_2012.txt", "performance", tmp_path/"b", 100)
    assert pq.read_table(a["staging_file"]).equals(pq.read_table(b["staging_file"]))
    with pytest.raises(FileExistsError):
        stage_member(archive, "sample_perf_2012.txt", "performance", tmp_path/"a")

def test_positive_batch_required(make_zip, tmp_path):
    with pytest.raises(ValueError, match="positive"):
        stage_member(make_zip(), "sample_perf_2012.txt", "performance", tmp_path/"a", 0)

