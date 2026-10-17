from __future__ import annotations

import csv
from pathlib import Path

import pytest

from credit_atlas.hmda_national_views import DIMENSIONS, HmdaNationalViews, aggregate_csv


FIELDS = [
    "activity_year", "lei", "state_code", "county_code", "action_taken", "loan_type",
    "loan_purpose", "lien_status", "occupancy_type", "derived_dwelling_category",
    "debt_to_income_ratio", "derived_race", "derived_ethnicity", "derived_sex",
    "applicant_credit_score_type", "denial_reason_1", "loan_amount",
]
FIELDS += [f"synthetic_field_{index}" for index in range(99 - len(FIELDS))]


def row(**overrides):
    value = {field: "" for field in FIELDS}
    value.update({
        "activity_year": "2025", "lei": "A" * 20, "state_code": "CA", "county_code": "06037",
        "action_taken": "1", "loan_type": "1", "loan_purpose": "1", "lien_status": "1",
        "occupancy_type": "1", "derived_dwelling_category": "Single Family (1-4 Units):Site-Built",
        "debt_to_income_ratio": "36%", "derived_race": "White",
        "derived_ethnicity": "Not Hispanic or Latino", "derived_sex": "Male",
        "applicant_credit_score_type": "3", "loan_amount": "100000",
    })
    value.update(overrides)
    return value


def write_lar(path: Path, records: list[dict[str, str]], delimiter: str = ",") -> Path:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(records)
    return path


def test_aggregate_csv_preserves_actions_and_explicit_decision_denominator(tmp_path: Path) -> None:
    path = write_lar(tmp_path / "lar.csv", [
        row(action_taken="1", loan_amount="100000"),
        row(action_taken="3", loan_amount="150000", denial_reason_1="3", state_code="CA"),
        row(action_taken="4", loan_amount="200000", state_code="NY", lei="B" * 20),
    ])

    result = aggregate_csv(path, tmp_path)

    assert result["summary"]["records"] == 3
    assert result["summary"]["decision_denominator"] == 2
    assert result["summary"]["denied_numerator"] == 1
    assert result["summary"]["descriptive_denial_rate"] == "0.5"
    assert result["summary"]["public_amount_sum_usd"] == "450000.00"
    assert {item["code"]: item["records"] for item in result["actions"]} == {"1": 1, "3": 1, "4": 1}
    ca = next(item for item in result["breakdowns"]["state_code"] if item["bucket"] == "CA")
    assert (ca["records"], ca["decision_denominator"], ca["denied_numerator"]) == (2, 2, 1)
    assert ca["descriptive_denial_rate"] == "0.5"
    assert result["quality"] == {"wrong_year_rows": 0, "invalid_action_rows": 0, "invalid_amount_rows": 0}


def test_aggregate_dynamic_pipe_delimited_lar(tmp_path: Path) -> None:
    path = write_lar(tmp_path / "dynamic-lar.txt", [
        row(action_taken="1", loan_amount="100000"),
        row(action_taken="3", loan_amount="150000", denial_reason_1="3", lei="B" * 20),
    ], delimiter="|")

    result = aggregate_csv(path, tmp_path, delimiter="|")

    assert result["summary"]["records"] == 2
    assert result["summary"]["decision_denominator"] == 2
    assert result["summary"]["denied_numerator"] == 1
    assert result["quality"] == {"wrong_year_rows": 0, "invalid_action_rows": 0, "invalid_amount_rows": 0}


def test_denial_reason_dimension_counts_only_action_three(tmp_path: Path) -> None:
    path = write_lar(tmp_path / "lar.csv", [
        row(action_taken="1", denial_reason_1="3"),
        row(action_taken="3", denial_reason_1="3"),
        row(action_taken="3", denial_reason_1="2"),
    ])

    result = aggregate_csv(path, tmp_path)

    reasons = {item["bucket"]: item for item in result["breakdowns"]["denial_reason_1"]}
    assert reasons["3"]["records"] == 1
    assert reasons["2"]["records"] == 1
    assert reasons["3"]["decision_denominator"] is None
    assert reasons["3"]["descriptive_denial_rate"] is None
    assert result["summary"]["denied_numerator"] == 2


def test_aggregate_csv_builds_state_loan_type_intersections_and_reconciles(tmp_path: Path) -> None:
    path = write_lar(tmp_path / "lar.csv", [
        row(state_code="CA", loan_type="1", action_taken="1", loan_amount="100000"),
        row(state_code="CA", loan_type="1", action_taken="3", loan_amount="150000"),
        row(state_code="CA", loan_type="2", action_taken="4", loan_amount="200000"),
        row(state_code="NY", loan_type="1", action_taken="4", loan_amount="300000"),
    ])

    result = aggregate_csv(path, tmp_path)

    intersections = {(item["state_code"], item["loan_type"]): item
                     for item in result["intersections"]["state_code_loan_type"]}
    california_conventional = intersections[("CA", "1")]
    assert (california_conventional["records"], california_conventional["decision_denominator"],
            california_conventional["denied_numerator"]) == (2, 2, 1)
    assert california_conventional["descriptive_denial_rate"] == "0.5"
    assert sum(item["records"] for item in intersections.values()) == result["summary"]["records"] == 4
    assert sum(item["decision_denominator"] for item in intersections.values()) == result["summary"]["decision_denominator"] == 2
    assert sum(item["denied_numerator"] for item in intersections.values()) == result["summary"]["denied_numerator"] == 1


def test_report_returns_validated_filtered_summary_from_intersections(tmp_path: Path, monkeypatch) -> None:
    service = HmdaNationalViews(tmp_path)
    intersections = [
        {"state_code": "CA", "loan_type": "1", "records": 2, "decision_denominator": 2,
         "denied_numerator": 1, "descriptive_denial_rate": "0.5", "public_amount_sum_usd": "250000.00"},
        {"state_code": "CA", "loan_type": "2", "records": 3, "decision_denominator": 1,
         "denied_numerator": 0, "descriptive_denial_rate": "0", "public_amount_sum_usd": "200000.00"},
        {"state_code": "NY", "loan_type": "1", "records": 1, "decision_denominator": 0,
         "denied_numerator": 0, "descriptive_denial_rate": None, "public_amount_sum_usd": "300000.00"},
    ]
    payload = {"source_id": "source", "snapshot_date": "2026-06-02", "activity_year": 2025,
        "summary": {"records": 6, "decision_denominator": 3, "denied_numerator": 1},
        "actions": [], "breakdowns": {key: [] for key in DIMENSIONS},
        "intersections": {"state_code_loan_type": intersections}, "scope": "test", "limitations": [],
        "denominator_contract": {"codes": ["1", "2", "3"]}}
    monkeypatch.setattr(service, "_view", lambda identifier: (tmp_path, {}, payload))

    report = service.report("hmda-national-view-0123456789ab", {
        "dimension": "county_code", "filter_state_code": "CA", "filter_loan_type": "1"})
    assert report["applied_filters"] == {"state_code": "CA", "loan_type": "1"}
    assert report["filtered_summary"] == {"records": 2, "decision_denominator": 2,
        "denied_numerator": 1, "descriptive_denial_rate": "0.5", "public_amount_sum_usd": "250000.00"}

    state_report = service.report("hmda-national-view-0123456789ab", {
        "dimension": "county_code", "filter_state_code": "CA"})
    assert state_report["filtered_summary"]["records"] == 5
    assert state_report["filtered_summary"]["decision_denominator"] == 3
    with pytest.raises(ValueError, match="Unsupported HMDA national state_code filter"):
        service.report("hmda-national-view-0123456789ab", {"filter_state_code": "ZZ"})
    with pytest.raises(ValueError, match="Invalid HMDA national aggregate query"):
        service.report("hmda-national-view-0123456789ab", {"borrower_id": "x"})


def test_aggregate_csv_rejects_wrong_year_or_invalid_action(tmp_path: Path) -> None:
    wrong_year = write_lar(tmp_path / "wrong-year.csv", [row(activity_year="2024")])
    with pytest.raises(ValueError, match="row quality"):
        aggregate_csv(wrong_year, tmp_path)

    bad_action = write_lar(tmp_path / "bad-action.csv", [row(action_taken="9")])
    with pytest.raises(ValueError, match="action distribution"):
        aggregate_csv(bad_action, tmp_path)


def test_report_rejects_unknown_dimension_before_loading_view(tmp_path: Path) -> None:
    service = HmdaNationalViews(tmp_path)
    with pytest.raises(ValueError, match="Unsupported HMDA national breakdown dimension"):
        service.report("hmda-national-view-0123456789ab", {"dimension": "borrower_id"})
    assert "denial_reason_1" in DIMENSIONS
