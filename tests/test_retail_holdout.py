import copy
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.retail import NUMERIC_FEATURES, CATEGORICAL_FEATURES
from credit_atlas.retail_features import RetailEncoder
from credit_atlas.retail_freeze import choose_model
from credit_atlas.retail_holdout import frozen_transform, check_codec, claim_holdout, evaluate_holdout
from credit_atlas.workspace import read_json, write_new, sha256


def encoder_and_rows():
    rows = [{"partition": "train", **{n: 20 + i for n in NUMERIC_FEATURES},
             **dict.fromkeys(CATEGORICAL_FEATURES, i % 2)} for i in range(10)]
    return RetailEncoder().fit(rows), rows


def test_frozen_codec_reuses_exact_statistics_and_unseen_buckets_without_fitting(monkeypatch):
    encoder, rows = encoder_and_rows()
    state = copy.deepcopy(encoder.state)
    monkeypatch.setattr(RetailEncoder, "fit", lambda *a: pytest.fail("Holdout must never fit"))
    check_codec(state)
    validation = [{**r, "partition": "validation"} for r in rows]
    validation[0][CATEGORICAL_FEATURES[0]] = 9
    expected = encoder.transform(validation)
    final = [{**r, "partition": "final_test"} for r in validation]
    assert np.array_equal(expected, frozen_transform(state, final))
    assert state == encoder.state
    with pytest.raises(ValueError, match="excludes final-test"):
        encoder.transform(final)


@pytest.mark.parametrize("partition", ["train", "calibration", "validation", "wrong"])
def test_holdout_codec_rejects_wrong_roles(partition):
    encoder, rows = encoder_and_rows()
    with pytest.raises(ValueError, match="explicit permitted partition"):
        frozen_transform(encoder.state, [{**rows[0], "partition": partition}])


def test_holdout_codec_rejects_nonfinite_and_boolean_values():
    encoder, rows = encoder_and_rows()
    for value in (float("nan"), True):
        row = {**rows[0], "partition": "final_test", NUMERIC_FEATURES[0]: value}
        with pytest.raises(ValueError, match="Finite numeric"):
            frozen_transform(encoder.state, [row])


def test_ledger_prevents_reopening_same_source_split_with_another_model(tmp_path):
    ledger = tmp_path / "private/access.sqlite"
    claim_holdout(ledger, "same-source-split", "first-model", tmp_path / "first")
    with pytest.raises(ValueError, match="already been claimed"):
        claim_holdout(ledger, "same-source-split", "different-model", tmp_path / "second")


def selection_fixture():
    validation = {"constant": {"raw": {"brier_score": .2, "log_loss": .6}},
                  "logistic": {"raw": {"brier_score": .15, "log_loss": .5}}}
    pair = {"brier_score": {"point": .002, "lower": .001}, "log_loss": {"lower": .004}, "roc_auc": {"point": .007}}
    uncertain = {"brier_score": {"point": .00003, "lower": -.00002}, "log_loss": {"lower": -.0001}}
    comparison = {}
    comparison["paired_improvements"] = [{"reference": "logistic/raw", "candidate": "boosting/raw", "metrics": pair}] + [
        {"reference": n + "/raw", "candidate": n + "/calibrated", "metrics": copy.deepcopy(uncertain)} for n in ("logistic", "boosting")]
    return validation, comparison


def test_selection_rule_fallback_and_no_uncertain_calibration():
    validation, comparison = selection_fixture()
    assert choose_model(validation, comparison)["model"] == "boosting"
    assert choose_model(validation, comparison)["variant"] == "raw"
    comparison["paired_improvements"][0]["metrics"]["brier_score"]["lower"] = -.001
    assert choose_model(validation, comparison)["model"] == "logistic"
    validation["logistic"]["raw"]["brier_score"] = .21
    assert choose_model(validation, comparison)["model"] == "constant"


def test_selection_requires_material_positive_calibration_evidence():
    validation, comparison = selection_fixture()
    pair = comparison["paired_improvements"][2]["metrics"]
    pair["brier_score"] = {"point": .0002, "lower": .00005}
    pair["log_loss"]["lower"] = .0002
    assert choose_model(validation, comparison)["variant"] == "calibrated"


def test_complete_holdout_only_scores_frozen_model_and_records_one_time_access(tmp_path, monkeypatch):
    encoder, _ = encoder_and_rows()
    bundle, case_folder = tmp_path / "bundle", tmp_path / "case"
    bundle.mkdir(); case_folder.mkdir()
    write_new(bundle / "encoder.json", encoder.state)
    write_new(bundle / "model.json", {"kind": "constant", "prevalence": .2, "feature_dimension": len(encoder.state["feature_names"])})
    # Deliberately unusable development predictors: final-only query must exclude them.
    rows = [{"source_client_id": i + 1, "target": i % 2, "partition": "final_test" if i < 100 else "train",
             **dict.fromkeys(NUMERIC_FEATURES, 30. if i < 100 else float("nan")),
             **dict.fromkeys(CATEGORICAL_FEATURES, 0 if i < 100 else 99)} for i in range(110)]
    pq.write_table(pa.Table.from_pylist(rows), case_folder / "clients.parquet")
    pq.write_table(pa.Table.from_pylist([{k: r[k] for k in ("source_client_id", "partition")} for r in rows]), case_folder / "partitions.parquet")
    case = {"case_id": "retail-case-aaaaaaaaaaaa", "source_sha256": "a" * 64,
            "outputs_sha256": {"partitions.parquet": sha256(case_folder / "partitions.parquet"), "protocol.json": "b" * 64},
            "support": {"final_test": {"positive": 50, "negative": 50}}}
    monkeypatch.setattr("credit_atlas.retail_holdout.verify_freeze", lambda *a: (
        bundle, {"selected_model": "constant", "selected_variant": "raw"}, "c" * 64, case_folder, case))
    monkeypatch.setattr(RetailEncoder, "fit", lambda *a: pytest.fail("No holdout fitting"))
    result = evaluate_holdout(tmp_path, "retail-freeze-aaaaaaaaaaaa")
    assert result["holdout_metrics"]["loans"] == 100
    assert result["holdout_metrics"]["events"] == 50
    receipt = read_json(Path(result["directory"]) / "evaluation-complete.json")
    assert receipt["final_test_scored"] and not receipt["model_selection_performed"]
    assert not receipt["temporal_out_of_time"] and not receipt["qualified_for_production"]
    with pytest.raises(ValueError, match="already been claimed"):
        evaluate_holdout(tmp_path, "retail-freeze-bbbbbbbbbbbb")
