import copy

import pytest

from credit_atlas.suite_snapshot import business_report, business_projection


@pytest.fixture
def snapshot():
    rows = [{"program": "7A", "bucket": "2020", "status": "charged_off", "records": 2, "reported_approval_amount": "10.000000000001"},
            {"program": "7A", "bucket": "2020", "status": "disbursed_status_withheld", "records": 8, "reported_approval_amount": "90.000000000000"},
            {"program": "504", "bucket": "2020", "status": "paid_in_full", "records": 3, "reported_approval_amount": "100.0"},
            {"program": "504", "bucket": "2021", "status": "charged_off", "records": 4, "reported_approval_amount": "200.0"}]
    return {"view_id": "suite-view-aaaaaaaaaaaa", "business": {"business_id": "business-sba-bbbbbbbbbbbb", "receipt_sha256": "a" * 64,
            "aggregates": {"dimensions": {"approval_fiscal_year": rows}, "amount_scope": {"7A": "total loan", "504": "SBA/CDC component"},
                           "limitations": ["snapshot shares not PD"]},
            "quality": {"all_source": {"flags": 9}}, "contract": {"version": "SYNTHETIC-QA"}}}


def test_selected_scope_keeps_decimal_strings_and_explicit_whole_source_quality(snapshot):
    original = copy.deepcopy(snapshot)
    result = business_report(snapshot, {"program": "7A", "dimension": "approval_fiscal_year", "bucket": "2020"})
    assert result["selected_record_count"] == 10
    assert all(r["program"] == "7A" and r["bucket"] == "2020" for r in result["rows"])
    assert result["rows"][0]["reported_approval_amount"] == "10.000000000001"
    assert result["quality"] == snapshot["business"]["quality"]
    assert result["quality_scope"].startswith("whole_source")
    assert result["public_release_approved"] is False and not result["model_training_performed"]
    result["rows"][0]["records"] = 999
    assert snapshot == original


def test_program_scope_with_unavailable_year_returns_empty_records_not_synthetic_zero_amount(snapshot):
    result = business_report(snapshot, {"program": "7A", "dimension": "approval_fiscal_year", "bucket": "2021"})
    assert result["selected_record_count"] == 0 and result["rows"] == []


@pytest.mark.parametrize("query", [{"program": "other"}, {"dimension": "loan_timeline"}, {"bucket": "../private"}, {"loan_key": "raw"}])
def test_unknown_scope_and_row_level_filters_rejected(snapshot, query):
    with pytest.raises(ValueError):
        business_report(snapshot, {"dimension": "approval_fiscal_year", **query})


def test_business_report_without_case_is_unavailable():
    with pytest.raises(ValueError, match="no business case"):
        business_report({"view_id": "suite-view-aaaaaaaaaaaa"}, {})


def test_business_projection_rejects_unrelated_acquisition_lineage(tmp_path, monkeypatch):
    monkeypatch.setattr("credit_atlas.suite_snapshot.verify_sba", lambda *a: (tmp_path, {"suite_id": "suite-other"}, {}, "a" * 64))
    with pytest.raises(ValueError, match="lineage differ"):
        business_projection(tmp_path, "business-sba-bbbbbbbbbbbb", "suite-current")
