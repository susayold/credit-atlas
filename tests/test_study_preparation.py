import pytest
from pathlib import Path

from credit_atlas.study import prepare
from credit_atlas.workspace import read_json, write_new
from .test_private_loan_scope import two_cases


def protocol(tmp_path):
    path = tmp_path / "SYNTHETIC-protocol.json"
    write_new(path, {"version": 1, "status": "approved", "claim": "retrospective_temporal_not_strict_pit",
                     "train_years": [2020], "calibration_years": [2022],
                     "validation_years": [2024], "test_years": [2026],
                     "train_fit_month": "2021-01-01", "calibration_fit_month": "2023-01-01",
                     "selection_freeze_month": "2025-01-01",
                     "minimum_positive_per_partition": 1, "minimum_negative_per_partition": 1})
    return path


def test_preparing_inputs_does_not_fit_or_approve_incomplete_study(two_cases, tmp_path):
    api, ids, _ = two_cases
    result = prepare(api.root, [ids[0]], protocol(tmp_path))
    assert result["model_fit_ready"] is False
    assert result["support"]["train"]["positive"] == 1
    assert result["support"]["test"] == {"positive": 0, "negative": 0}
    assert "missing_required_vintages" in result["blocking_reasons"]
    receipt = read_json(Path(result["study_directory"]) / "study-complete.json")
    assert receipt["model_training_performed"] is False
    assert receipt["label_rows"] == 1


def test_same_vintage_rebuilds_cannot_inflate_study_population(two_cases, tmp_path):
    api, ids, _ = two_cases
    selected_protocol = protocol(tmp_path)
    with pytest.raises(ValueError, match="Overlapping"):
        prepare(api.root, ids, selected_protocol)
    with pytest.raises(ValueError, match="distinct"):
        prepare(api.root, [ids[0], ids[0]], selected_protocol)
