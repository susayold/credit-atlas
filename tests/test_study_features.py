"""Deliberate leakage, missingness and lineage failures in synthetic studies."""
import json
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.study import prepare
from credit_atlas.study_features import encode_audit, prepare_features
from credit_atlas.workspace import read_json, sha256, write_new
from .test_private_loan_scope import two_cases
from .test_study_preparation import protocol


CONFIG = {"numeric": ["classic_fico", "original_dti"], "categorical": ["occupancy"]}


def row(identifier, role, fico, dti, occupancy):
    return {"loan_id": identifier, "partition": role, "included": True,
            "classic_fico": fico, "original_dti": dti, "occupancy": occupancy}


def test_evaluation_values_never_change_train_imputation_scaling_or_vocabulary():
    train = [row("A", "train", 600, None, "P"), row("B", "train", 800, None, None)]
    records = train + [row("C", "calibration", 1000, 30, "I")]
    encoder, audit = encode_audit(records, CONFIG)
    changed = train + [row("C", "calibration", 2000, 99, "S")]
    second, _ = encode_audit(changed, CONFIG)
    assert encoder.state == second.state
    assert encoder.state["numeric"]["classic_fico"]["median"] == 700
    assert encoder.state["categorical"]["occupancy"] == ["__missing__", "__unseen__", "value:P"]
    assert audit["all_missing_train"] == ["original_dti"]
    coverage = next(r for r in audit["coverage"] if r["partition"] == "calibration"
                    and r["feature"] == "occupancy")
    assert coverage["unseen"] == 1
    assert audit["transform_mutates_fit"] is False
    vector = encoder.transform([records[-1]])[0]
    assert vector[-2] == 1  # unseen bucket, never fitted to calibration category.


@pytest.mark.parametrize("bad", [
    row("A", "test", 700, 30, "P"),
    {**row("A", "train", 700, 30, "P"), "included": False},
    row("A", "train", float("nan"), 30, "P"),
])
def test_final_test_excluded_rows_and_nonfinite_features_fail(bad):
    with pytest.raises(ValueError):
        encode_audit([bad], CONFIG)


def test_future_feature_config_duplicate_loans_and_missing_columns_fail():
    records = [row("A", "train", 700, 30, "P")]
    with pytest.raises(ValueError, match="allowlist"):
        encode_audit(records, {"numeric": ["current_upb"], "categorical": []})
    with pytest.raises(ValueError, match="unique"):
        encode_audit(records * 2, CONFIG)
    del records[0]["classic_fico"]
    with pytest.raises(ValueError, match="Missing"):
        encode_audit(records, CONFIG)


def test_no_training_population_is_explicitly_unavailable():
    encoder, audit = encode_audit([row("C", "calibration", 700, 30, "P")], CONFIG)
    assert encoder is None and audit["status"] == "NO_INCLUDED_TRAIN"


def feature_study(two_cases, tmp_path):
    api, ids, _ = two_cases
    case = tmp_path / "artifacts/private" / ids[0]
    manifest = read_json(case / "case-complete.json")
    stage = tmp_path / manifest["canonical_run"]
    dim = pq.read_table(stage / "dim_loan.parquet").to_pylist()
    for record in dim:
        record.update(units=1, first_time_homebuyer="N")
    final = {**dim[0], "loan_id": "SYNTHETIC-FINAL-TEST", "origination_year": 2026,
             "classic_fico": float("nan")}  # Any leaked test row makes encoder fail.
    dim.append(final)
    pq.write_table(pa.Table.from_pylist(dim), stage / "dim_loan.parquet")
    labels = pq.read_table(stage / "labels.parquet").to_pylist()
    labels.append({**labels[0], "loan_id": final["loan_id"], "origination_year": 2026,
                   "landmark": date(2026, 1, 1), "label_known_month": date(2026, 2, 1)})
    pq.write_table(pa.Table.from_pylist(labels), stage / "labels.parquet")
    snapshot = read_json(case / "snapshot.json")
    snapshot["source_years"] = [2020, 2026]
    (case / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    manifest["outputs_sha256"]["snapshot.json"] = sha256(case / "snapshot.json")
    for item in manifest["verified_inputs"]:
        item["sha256"] = sha256(tmp_path / item["path"])
    (case / "case-complete.json").write_text(json.dumps(manifest), encoding="utf-8")
    config = tmp_path / "vendor/credit_risk_strategy_lab/configs/features_origination.json"
    write_new(config, CONFIG)
    result = prepare(api.root, [ids[0]], protocol(tmp_path))
    return api.root, Path(result["study_directory"])


def test_private_feature_workflow_does_not_materialize_or_encode_final_test(two_cases, tmp_path):
    root, study = feature_study(two_cases, tmp_path)
    result = prepare_features(root, study.name)
    folder = Path(result["feature_directory"])
    receipt = read_json(folder / "feature-complete.json")
    coverage = read_json(folder / "feature-coverage.json")
    assert receipt["rows_by_partition"] == {"train": 1, "calibration": 0, "validation": 0}
    assert receipt["feature_contract_qualified"] is False and receipt["model_fit_ready"] is False
    assert receipt["final_test_predictors_materialized"] is False
    assert receipt["model_training_performed"] is False
    assert coverage["transform_parity"] == "PASS_ALL_DEVELOPMENT_ROWS"
    assert read_json(folder / "encoder.json")["fit_rows"] == 1
    access = read_json(folder / "access-start.json")
    assert access["final_test_outcome_counts_may_be_read"] is True
    assert "SYNTHETIC-FINAL-TEST" not in (folder / "feature-coverage.json").read_text()
    assert set(receipt["outputs_sha256"]) == {"access-start.json", "feature-coverage.json",
                                              "feature-config.json", "encoder.json"}


def test_tampered_prepared_protocol_is_rejected_before_feature_artifacts(two_cases, tmp_path):
    root, study = feature_study(two_cases, tmp_path)
    (study / "protocol.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="evidence changed"):
        prepare_features(root, study.name)
    assert not list((root / "artifacts/private").glob("feature-audit-*"))


def test_split_assignments_are_rederived_even_if_digest_is_updated(two_cases, tmp_path):
    root, study = feature_study(two_cases, tmp_path)
    path = study / "split_manifest.parquet"
    assignments = pq.read_table(path).to_pylist()
    assignments[-1]["included"] = False
    pq.write_table(pa.Table.from_pylist(assignments), path)
    receipt = read_json(study / "study-complete.json")
    receipt["outputs_sha256"]["split_manifest.parquet"] = sha256(path)
    (study / "study-complete.json").write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="Saved split"):
        prepare_features(root, study.name)
    failure = next((root / "artifacts/private").glob("feature-audit-*/feature-failed.json"))
    assert read_json(failure)["model_training_performed"] is False


def test_registry_serves_aggregate_coverage_only_for_related_verified_case(two_cases, tmp_path):
    api, ids, _ = two_cases
    root, study = feature_study(two_cases, tmp_path)
    result = prepare_features(root, study.name)
    from credit_atlas.service import ResearchService
    service = ResearchService(root)
    related = service.studies(ids[0])
    assert len(related["studies"]) == 1
    feature = related["studies"][0]["feature_audits"][0]
    assert feature["encoder_fit_rows"] == 1 and feature["model_fit_ready"] is False
    assert "loan_id" not in json.dumps(related)
    assert "SYNTHETIC-source-id" not in json.dumps(related)
    assert not service.studies(ids[1])["studies"]
    path = Path(result["feature_directory"]) / "encoder.json"
    path.write_text("{}", encoding="utf-8")
    unavailable = service.studies(ids[0])["studies"][0]["feature_audits"][0]
    assert unavailable["status"] == "evidence_unavailable_or_changed"


def test_malformed_unrelated_feature_receipt_does_not_disable_verified_study(two_cases, tmp_path):
    from credit_atlas.service import ResearchService
    _, ids, _ = two_cases
    root, study = feature_study(two_cases, tmp_path)
    prepare_features(root, study.name)
    write_new(root / "artifacts/private/feature-audit-aaaaaaaaaaaa/feature-complete.json", [])
    result = ResearchService(root).studies(ids[0])
    assert result["studies"][0]["status"] == "PREPARED_NOT_FIT_READY"
    assert result["unreadable_artifacts"] == 1
    assert len(result["studies"][0]["feature_audits"]) == 1
