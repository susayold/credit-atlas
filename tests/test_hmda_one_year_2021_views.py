from __future__ import annotations

import csv
from pathlib import Path

import pytest

from credit_atlas import hmda_one_year_2021_views as one_year


FIELDS = [
    "activity_year", "lei", "state_code", "county_code", "action_taken", "loan_type",
    "loan_purpose", "lien_status", "occupancy_type", "derived_dwelling_category",
    "debt_to_income_ratio", "derived_race", "derived_ethnicity", "derived_sex",
    "applicant_credit_score_type", "denial_reason_1", "loan_amount", "combined_loan_to_value_ratio",
]
FIELDS += [f"synthetic_field_{index}" for index in range(99 - len(FIELDS))]


def row(**overrides):
    value = {field: "" for field in FIELDS}
    value.update({"activity_year": "2021", "lei": "A" * 20, "state_code": "CA",
        "county_code": "06037", "action_taken": "1", "loan_type": "1", "loan_purpose": "1",
        "lien_status": "1", "occupancy_type": "1", "derived_dwelling_category": "Single Family",
        "debt_to_income_ratio": "36%", "derived_race": "White", "derived_ethnicity": "Not Hispanic",
        "derived_sex": "Male", "applicant_credit_score_type": "3", "loan_amount": "100000"})
    value.update(overrides)
    return value


def write_lar(path: Path, records):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    return path


def test_aggregate_csv_preserves_all_actions_and_denominator(tmp_path: Path, monkeypatch):
    actions = {"1": 2, "2": 1, "3": 1, "4": 1}
    monkeypatch.setattr(one_year, "EXPECTED_ACTIONS", actions)
    path = write_lar(tmp_path / "lar.csv", [row(action_taken="1"), row(action_taken="1", state_code="NY"),
        row(action_taken="2"), row(action_taken="3", denial_reason_1="3"), row(action_taken="4")])

    result = one_year.aggregate_csv(path, tmp_path)

    assert result["summary"]["records"] == 5
    assert result["summary"]["decision_denominator"] == 4
    assert result["summary"]["denied_numerator"] == 1
    assert result["summary"]["descriptive_denial_rate"] == "0.25"
    assert {item["code"]: item["records"] for item in result["actions"]} == actions
    reason = result["breakdowns"]["denial_reason_1"][0]
    assert reason["bucket"] == "3" and reason["records"] == 1
    assert reason["denominator_kind"] == "action_3_applications"


@pytest.mark.parametrize("record", [row(activity_year="2023"), row(action_taken="9"), row(state_code="ZZ"),
    row(loan_type="9"), row(lei="bad-lei"), row(loan_amount="bad-amount")])
def test_aggregate_csv_rejects_invalid_rows(tmp_path: Path, monkeypatch, record):
    monkeypatch.setattr(one_year, "EXPECTED_ACTIONS", {"1": 1})
    path = write_lar(tmp_path / "bad.csv", [record])
    with pytest.raises(ValueError):
        one_year.aggregate_csv(path, tmp_path)


def test_source_id_is_release_specific(tmp_path: Path):
    with pytest.raises(ValueError, match="Invalid 2021 HMDA One-Year source id"):
        one_year.source_folder(tmp_path, "hmda-national-snapshot-2025-123456789abc")
