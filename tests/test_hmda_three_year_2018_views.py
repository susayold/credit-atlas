from pathlib import Path

import pytest

from credit_atlas.hmda_three_year_2018_views import DIMENSIONS, HmdaThreeYear2018Views


def test_report_keeps_three_year_release_and_private_visibility(monkeypatch, tmp_path: Path):
    identifier = "hmda-three-year-2018-view-123456789abc"
    payload = {"view_id": identifier, "release_type": "Three-Year National Dataset",
        "freeze_date": "2021-12-31", "summary": {"records": 15_138_510,
        "denied_numerator": 2_552_640, "decision_denominator": 10_623_751},
        "breakdowns": [
            {"dimension": "state_code", "bucket": "CA", "records": 100,
             "decision_denominator": 80, "denied_numerator": 10, "descriptive_denial_rate": "0.125"},
            {"dimension": "state_code", "bucket": "NY", "records": 50,
             "decision_denominator": 40, "denied_numerator": 5, "descriptive_denial_rate": "0.125"},
        ]}
    view = HmdaThreeYear2018Views(tmp_path)
    monkeypatch.setattr(view, "_view", lambda selected: (tmp_path, {}, payload))

    result = view.report(identifier, {"view_id": identifier, "dimension": "state_code"})

    assert result["activity_year"] == 2018
    assert result["release_type"] == "Three-Year National Dataset"
    assert result["summary"]["decision_denominator"] == 10_623_751
    assert [row["bucket"] for row in result["breakdown"]] == ["CA", "NY"]
    assert result["visibility"] == "private"
    assert result["public_release_approved"] is False


def test_report_rejects_unknown_dimension_and_extra_filters(monkeypatch, tmp_path: Path):
    identifier = "hmda-three-year-2018-view-123456789abc"
    view = HmdaThreeYear2018Views(tmp_path)
    monkeypatch.setattr(view, "_view", lambda selected: (tmp_path, {}, {}))
    with pytest.raises(ValueError, match="Unsupported HMDA 2018 breakdown dimension"):
        view.report(identifier, {"dimension": "lei"})
    with pytest.raises(ValueError, match="Invalid HMDA 2018 aggregate query"):
        view.report(identifier, {"dimension": "state_code", "lei": "sensitive"})


def test_all_2018_dimensions_have_human_labels():
    assert len(DIMENSIONS) == 20
    assert DIMENSIONS["ltv_band"].startswith("LTV band")
    assert DIMENSIONS["denial_reason-1"].endswith("action 3 only")
