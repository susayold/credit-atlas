"""Gated multi-case orchestration with explicit synthetic engineering fixtures."""
import json
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.assessment import run, validate_review, fit_plan
from credit_atlas.study import prepare
from credit_atlas.study_features import prepare_features
from credit_atlas.workspace import read_json, sha256, write_new
from .test_private_loan_scope import two_cases
from .test_study_features import feature_study


def test_incomplete_study_stops_before_model_fit_and_preserves_blocked_receipt(two_cases, tmp_path, monkeypatch):
    root, study = feature_study(two_cases, tmp_path)
    feature = Path(prepare_features(root, study.name)["feature_directory"])
    import crsl.models.assessment
    monkeypatch.setattr(crsl.models.assessment, "assess",
                        lambda *args, **kwargs: pytest.fail("Unqualified study entered model fitting"))
    result = run(root, study.name, feature.name)
    assert result["status"] == "BLOCKED_BEFORE_FIT" and result["model_training_performed"] is False
    assert "missing_required_vintages" in result["blocking_reasons"]
    folder = Path(result["assessment_directory"])
    assert not (folder / "assessment.json").exists() and not (folder / "fit-start.json").exists()
    assert read_json(folder / "assessment-complete.json")["final_test_scored"] is False


def settings():
    return {"train_cutoff": "2021-01-01", "calibration_cutoff": "2023-01-01",
            "evaluation_cutoff": "2025-01-01", "logistic_C": 1.,
            "calibration_C": 1., "minimum_events": 50,
            "bin_edges": ["0", "0.1", "0.5", "0.9", "1"],
            "challenger_parameters": {"learning_rate": 0.1, "max_iter": 5,
                "max_leaf_nodes": 3, "min_samples_leaf": 20, "l2_regularization": 1., "random_state": 17}}


def large_synthetic_study(two_cases, tmp_path):
    api, ids, _ = two_cases
    root, previous = feature_study(two_cases, tmp_path)
    case = root / "artifacts/private" / ids[0]
    manifest = read_json(case / "case-complete.json")
    stage = root / manifest["canonical_run"]
    dims, labels = [], []
    for year, count in [(2020, 400), (2022, 100), (2024, 100), (2026, 100)]:
        for index in range(count):
            identifier = f"SYNTHETIC-{year}-{index:04d}"
            target = index % 2
            dims.append({"loan_id": identifier, "classic_fico": float("nan") if year == 2026 else 620 + 100 * target + index % 13,
                         "original_dti": 30 if index % 5 else None, "occupancy": "P"})
            labels.append({"loan_id": identifier, "origination_year": year, "target": target,
                           "label_known_month": date(year, 2, 1), "landmark": date(year, 1, 1)})
    for name, records in [("dim_loan", dims), ("labels", labels)]:
        pq.write_table(pa.Table.from_pylist(records), stage / (name + ".parquet"))
    snapshot = read_json(case / "snapshot.json")
    snapshot["source_years"] = [2020, 2022, 2024, 2026]
    (case / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    manifest["outputs_sha256"]["snapshot.json"] = sha256(case / "snapshot.json")
    for item in manifest["verified_inputs"]:
        item["sha256"] = sha256(root / item["path"])
    (case / "case-complete.json").write_text(json.dumps(manifest), encoding="utf-8")
    # Existing synthetic protocol is approved, but only the new 700-row source
    # population satisfies strict 200/50 class support in every outer role.
    protocol = previous / "protocol.json"
    result = prepare(root, [ids[0]], protocol)
    study = Path(result["study_directory"])
    feature = Path(prepare_features(root, study.name)["feature_directory"])
    assert read_json(study / "study-complete.json")["source_and_split_ready"] is True
    review = {"schema_version": 1, "status": "approved_for_development",
              "study_id": study.name, "study_receipt_sha256": sha256(study / "study-complete.json"),
              "feature_audit_id": feature.name,
              "feature_receipt_sha256": sha256(feature / "feature-complete.json"),
              "reviewer": "SYNTHETIC-QA", "rationale": "Synthetic engineering test, no production/model qualification claim.",
              "settings": settings()}
    path = tmp_path / "SYNTHETIC-development-review.json"
    write_new(path, review)
    return root, study, feature, path


def test_qualified_synthetic_flow_persists_three_models_and_keeps_final_test_locked(two_cases, tmp_path):
    root, study, feature, review = large_synthetic_study(two_cases, tmp_path)
    result = run(root, study.name, feature.name, review)
    assert result["status"] == "DEVELOPMENT_ASSESSMENT_VERIFIED"
    folder = Path(result["assessment_directory"])
    verification = read_json(folder / "verification.json")
    assert verification["score_sets_checked"] == 6 and verification["validation_loans"] == 100
    payload = read_json(folder / "assessment.json")
    assert set(payload["models"]) == {"constant", "logistic", "challenger"}
    assert payload["cohort_counts"] == {"train": 400, "calibration": 100, "validation": 100}
    for model in payload["models"].values():
        assert len(model["private_validation_scores"]["raw"]) == 100
        assert all("SYNTHETIC-2024-" in row["loan_id"] for row in model["private_validation_scores"]["raw"])
    receipt = read_json(folder / "assessment-complete.json")
    assert receipt["research_ready"] is False and receipt["champion_selected"] is False
    assert receipt["final_test_scored"] is False
    assert (folder / "challenger-model.json").exists()
    plan = read_json(folder / "fit-plan.json")
    assert plan["final_model_fits"] == 3 and plan["separate_calibration_fits"] == 3
    assert plan["total_declared_fit_calls"] == 6 and plan["final_test_access"] is False
    from credit_atlas.service import ResearchService
    from credit_atlas.study_registry import assessment_summary
    from credit_atlas.study_features import verify_prepared
    service = ResearchService(root)
    _, prepared, _, digest = verify_prepared(service, study.name)
    summary = assessment_summary(service, folder, prepared, digest)
    assert len(summary["validation_metrics"]) == 6
    assert summary["cohort_counts"] == payload["cohort_counts"]
    serialized = json.dumps(summary)
    assert "SYNTHETIC-" not in serialized and "private_validation_scores" not in serialized
    assert "loan_id" not in serialized and str(root) not in serialized
    (folder / "verification.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="evidence changed"):
        assessment_summary(service, folder, prepared, digest)


def test_unreviewed_qualified_population_still_stops_before_fit(two_cases, tmp_path):
    root, study, feature, _ = large_synthetic_study(two_cases, tmp_path)
    result = run(root, study.name, feature.name)
    assert result["status"] == "BLOCKED_BEFORE_FIT"
    assert result["blocking_reasons"] == ["development_feature_review_not_provided"]
    from credit_atlas.service import ResearchService
    from credit_atlas.study_registry import assessment_summary
    from credit_atlas.study_features import verify_prepared
    service = ResearchService(root)
    _, prepared, _, digest = verify_prepared(service, study.name)
    folder = Path(result["assessment_directory"])
    summary = assessment_summary(service, folder, prepared, digest)
    assert summary["model_training_performed"] is False
    assert summary["blocking_reasons"] == result["blocking_reasons"]
    assert "validation_metrics" not in summary
    listing = service.studies(prepared["case_references"][0]["case_id"])
    assert next(item for item in listing["studies"] if item["study_id"] == study.name)["assessments"] == [summary]
    (folder / "access-start.json").write_text("{}", encoding="utf-8")
    unavailable = service.studies(prepared["case_references"][0]["case_id"])
    assert next(item for item in unavailable["studies"] if item["study_id"] == study.name)["assessments"][0]["status"] == "evidence_unavailable_or_changed"


@pytest.mark.parametrize("changed", [
    {"evaluation_cutoff": "2027-01-01"}, {"minimum_events": 1},
    {"minimum_events": 51}, {"bin_edges": ["0", "0.7", "0.5", "1"]},
    {"challenger_parameters": {"max_iter": 100000}},
])
def test_review_cannot_change_temporal_protocol_weaken_support_or_unbound_parameters(changed):
    study = {"study_id": "study-" + "1" * 12,
             "protocol": {"train_fit_month": "2021-01-01", "calibration_fit_month": "2023-01-01",
                          "selection_freeze_month": "2025-01-01"},
             "support": {"calibration": {"positive": 50, "negative": 50},
                         "validation": {"positive": 50, "negative": 50}}}
    review = {"schema_version": 1, "status": "approved_for_development", "study_id": study["study_id"],
              "study_receipt_sha256": "a" * 64, "feature_audit_id": "feature-audit-" + "2" * 12,
              "feature_receipt_sha256": "b" * 64, "reviewer": "SYNTHETIC-QA",
              "rationale": "Only test the review parser.", "settings": {**settings(), **changed}}
    with pytest.raises(ValueError):
        validate_review(review, study, "a" * 64, review["feature_audit_id"], "b" * 64)


def test_predeclared_train_only_regularization_grid_and_fold_fit_budget():
    config = settings()
    config["logistic_C"] = None
    config["logistic_tuning"] = {"C_grid": ["0.1", "1"],
        "minimum_train_class": 200, "minimum_holdout_class": 50,
        "folds": [{"fit_cutoff": "2018-01-01", "holdout_landmark_end": "2019-01-01", "evaluation_cutoff": "2019-06-01"},
                  {"fit_cutoff": "2019-06-01", "holdout_landmark_end": "2020-01-01", "evaluation_cutoff": "2020-06-01"}]}
    records = []
    for year, count in [(2017, 400), (2018, 100), (2019, 100)]:
        for index in range(count):
            landmark = date(year, 7 if year == 2019 else 1, 1)
            records.append({"loan_id": f"SYNTHETIC-{year}-{index}", "partition": "train",
                            "target": index % 2, "landmark": landmark,
                            "label_known_month": date(year, 8 if year == 2019 else 2, 1)})
    plan = fit_plan(records, config, 12)
    study = {"study_id": "study-" + "1" * 12,
             "protocol": {"train_fit_month": "2021-01-01", "calibration_fit_month": "2023-01-01",
                          "selection_freeze_month": "2025-01-01"},
             "support": {"calibration": {"positive": 50, "negative": 50},
                         "validation": {"positive": 50, "negative": 50}}}
    review = {"schema_version": 1, "status": "approved_for_development",
              "study_id": study["study_id"], "study_receipt_sha256": "a" * 64,
              "feature_audit_id": "feature-audit-" + "2" * 12,
              "feature_receipt_sha256": "b" * 64, "reviewer": "SYNTHETIC-QA",
              "rationale": "Predeclared synthetic temporal tuning.", "settings": config}
    assert validate_review(review, study, "a" * 64, review["feature_audit_id"], "b" * 64) == config
    assert plan["inner_candidate_fits"] == 4
    assert plan["total_declared_fit_calls"] == 10
    assert plan["train_encoded_matrix_bytes"] == 600 * 12 * 8
    with pytest.raises(ValueError, match="support"):
        fit_plan(records[:100], config, 12)
