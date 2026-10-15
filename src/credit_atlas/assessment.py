"""Gated multi-case development assessment; final test remains locked."""
from __future__ import annotations

import math
import time
import uuid
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from .service import ResearchService
from .snapshot import json_ready
from .study_features import verify_prepared
from .study_registry import FEATURE_ID, feature_summary
from .workspace import contained, engine_root, read_json, sha256, timestamp, write_new

VERSION = "d01-gated-development-assessment-v1"


def validate_review(review, study, study_digest, feature_id, feature_digest):
    required = {"schema_version", "status", "study_id", "study_receipt_sha256",
                "feature_audit_id", "feature_receipt_sha256", "reviewer", "rationale", "settings"}
    if not isinstance(review, dict) or set(review) != required:
        raise ValueError("Explicit bounded development review fields required")
    if (review["schema_version"] != 1 or review["status"] != "approved_for_development"
            or review["study_id"] != study["study_id"] or review["study_receipt_sha256"] != study_digest
            or review["feature_audit_id"] != feature_id or review["feature_receipt_sha256"] != feature_digest
            or any(not isinstance(review[k], str) or not 1 <= len(review[k].strip()) <= 4000
                   for k in ("reviewer", "rationale"))):
        raise ValueError("Review must identify the exact study and feature audit")
    settings = review["settings"]
    expected = {"train_cutoff", "calibration_cutoff", "evaluation_cutoff", "logistic_C",
                "calibration_C", "minimum_events", "bin_edges", "challenger_parameters"}
    if not isinstance(settings, dict) or not expected <= set(settings) <= expected | {"logistic_tuning"}:
        raise ValueError("Predeclared bounded baseline/challenger settings required")
    config = study["protocol"]
    if [settings[k] for k in ("train_cutoff", "calibration_cutoff", "evaluation_cutoff")] != [
            config[k] for k in ("train_fit_month", "calibration_fit_month", "selection_freeze_month")]:
        raise ValueError("Development dates must match the prepared temporal protocol")
    tuning = settings.get("logistic_tuning")
    numeric_settings = ["calibration_C"] + (["logistic_C"] if tuning is None else [])
    if (type(settings["minimum_events"]) is not int or settings["minimum_events"] < 50
            or any(type(settings[k]) not in (int, float) or not math.isfinite(settings[k])
                   or not 0 < settings[k] <= 100 for k in numeric_settings)):
        raise ValueError("Calibration support and regularization bounds cannot be weakened")
    if any(min(study["support"][role].values()) < settings["minimum_events"]
           for role in ("calibration", "validation")):
        raise ValueError("Declared calibration/evaluation support exceeds the prepared cohorts")
    edges = settings["bin_edges"]
    if not isinstance(edges, list) or not 3 <= len(edges) <= 21:
        raise ValueError("Three to twenty-one predeclared bin edges required")
    from decimal import Decimal
    if tuning is not None:
        from crsl.policy.engine import day
        if (settings["logistic_C"] is not None or not isinstance(tuning, dict)
                or set(tuning) != {"folds", "C_grid", "minimum_train_class", "minimum_holdout_class"}
                or type(tuning["minimum_train_class"]) is not int or tuning["minimum_train_class"] < 200
                or type(tuning["minimum_holdout_class"]) is not int or tuning["minimum_holdout_class"] < 50
                or not isinstance(tuning["folds"], list) or not 2 <= len(tuning["folds"]) <= 8
                or not isinstance(tuning["C_grid"], list) or not 1 <= len(tuning["C_grid"]) <= 8):
            raise ValueError("Bounded train-only tuning and minimum class support required")
        try:
            grid = [Decimal(str(value)) for value in tuning["C_grid"]]
            if (any(not value.is_finite() or not 0 < value <= 100 for value in grid)
                    or len(grid) != len(set(grid))):
                raise ValueError("Invalid or duplicate logistic tuning candidate")
        except ArithmeticError as error:
            raise ValueError("Invalid regularization grid") from error
        previous = None
        for fold in tuning["folds"]:
            if not isinstance(fold, dict) or set(fold) != {"fit_cutoff", "holdout_landmark_end", "evaluation_cutoff"}:
                raise ValueError("Invalid predeclared temporal fold")
            fit, end, evaluation = [day(fold[k]) for k in ("fit_cutoff", "holdout_landmark_end", "evaluation_cutoff")]
            if (any(value is None for value in (fit, end, evaluation))
                    or not fit < end <= evaluation <= day(settings["train_cutoff"])
                    or previous is not None and previous >= fit):
                raise ValueError("Tuning folds must lie within outer training time")
            previous = fit
    try:
        values = [Decimal(str(value)) for value in edges]
        if any(not value.is_finite() for value in values):
            raise ValueError("Nonfinite reliability bin")
        if values[0] != 0 or values[-1] != 1 or any(a >= b for a, b in zip(values, values[1:])):
            raise ValueError("Reliability bins must increase from zero to one")
    except ArithmeticError as error:
        raise ValueError("Invalid reliability bins") from error
    from crsl.models.challenger import BoostingChallenger
    if settings["challenger_parameters"] is not None:
        BoostingChallenger({"numeric": [], "categorical": []}, settings["challenger_parameters"])
    return settings


def verify_result(result, records, output):
    """Reload JSON models, rescore identical validation loans and rederive metrics."""
    from crsl.models.baseline import Baseline
    from crsl.models.challenger import BoostingChallenger
    from crsl.models.calibration import SigmoidCalibration
    from crsl.models.evaluation import evaluate_probabilities
    from crsl.policy.engine import fingerprint
    validation = sorted((r for r in records if r["partition"] == "validation"), key=lambda r: r["loan_id"])
    identities = {r["loan_id"] for r in validation}
    checked = 0
    for kind, item in result["models"].items():
        model = item["model"]
        payload = {"schema_version": 1, "feature_config": model["features"],
                   "model": model["state"], "encoder": model["encoder"]}
        model_file = output / (kind + "-model.json")
        write_new(model_file, payload)
        component = (BoostingChallenger if kind == "challenger" else Baseline).load(
            model_file, expected_sha256=sha256(model_file))
        digest = fingerprint(model)
        if digest != item["model_content_sha256"]:
            raise ValueError("Development model content digest mismatch")
        native_scores = item["private_validation_scores"]["raw"]
        if {r["loan_id"] for r in native_scores} != identities or len(native_scores) != len(validation):
            raise ValueError("Development models must share the exact validation cohort")
        loaded = component.predict(validation)
        if any(abs(a - b["pd"]) > 1e-12 for a, b in zip(loaded, native_scores, strict=True)):
            raise ValueError("Persisted model predictions differ from native scores")
        calibration_file = output / (kind + "-calibration.json")
        write_new(calibration_file, {"schema_version": 1, "state": item["calibration"]})
        calibrator = SigmoidCalibration.load(calibration_file, expected_sha256=sha256(calibration_file))
        scoring = [{**r, "raw_pd": pd, "model_sha256": digest,
                    "evidence_class": result["evidence_class"]}
                   for r, pd in zip(validation, loaded, strict=True)]
        calibrated = calibrator.predict(scoring)
        for variant, predictions in (("raw", loaded), ("calibrated", calibrated)):
            saved = item["private_validation_scores"][variant]
            if len(saved) != len(validation) or any(
                    row["loan_id"] != source["loan_id"] or abs(row["pd"] - value) > 1e-12
                    for row, source, value in zip(saved, validation, predictions, strict=True)):
                raise ValueError("Saved development score ordering or values changed")
            score_digest = fingerprint({"model_sha256": digest, "version": variant,
                "calibration": item["calibration"] if variant == "calibrated" else None, "scores": saved})
            available = result["settings"]["train_cutoff" if variant == "raw" else "calibration_cutoff"]
            metric_rows = [{**row, "pd": value, "score_sha256": score_digest,
                           "score_available_at": available} for row, value in zip(validation, predictions, strict=True)]
            expected = evaluate_probabilities(metric_rows,
                evaluation_cutoff=result["settings"]["evaluation_cutoff"],
                bin_edges=result["settings"]["bin_edges"], minimum_events=result["settings"]["minimum_events"])
            if expected != item["validation_metrics"][variant]:
                # Reloaded tree/calibration arithmetic can differ at machine epsilon.
                source_rows = [{**row, "pd": score["pd"], "score_sha256": score_digest,
                                "score_available_at": available}
                               for row, score in zip(validation, saved, strict=True)]
                if evaluate_probabilities(source_rows,
                    evaluation_cutoff=result["settings"]["evaluation_cutoff"],
                    bin_edges=result["settings"]["bin_edges"],
                    minimum_events=result["settings"]["minimum_events"]) != item["validation_metrics"][variant]:
                    raise ValueError("Saved validation metrics do not reconcile to source outcomes")
            brier = math.fsum((score["pd"] - row["target"]) ** 2
                             for score, row in zip(saved, validation, strict=True)) / len(validation)
            if not math.isclose(brier, item["validation_metrics"][variant]["brier_score"], abs_tol=1e-15):
                raise ValueError("Independent development Brier mismatch")
            checked += 1
    return {"status": "PASS", "score_sets_checked": checked, "validation_loans": len(validation),
            "scope": "persisted_model_calibration_parity_and_source_validation_metrics",
            "final_test_scored": False}

def fit_plan(records, settings, feature_dimension):
    """Account for bounded fits and matrices; preflight inner temporal support."""
    from crsl.policy.engine import day
    train = [row for row in records if row["partition"] == "train"]
    tuning = settings.get("logistic_tuning")
    folds = []
    held = set()
    if tuning is not None:
        for spec in tuning["folds"]:
            fit, end, evaluation = [day(spec[k]) for k in ("fit_cutoff", "holdout_landmark_end", "evaluation_cutoff")]
            fitted = [r for r in train if day(r["label_known_month"]) < fit]
            scored = [r for r in train if fit <= day(r["landmark"]) < end
                      and day(r["label_known_month"]) < evaluation]
            ids = {r["loan_id"] for r in scored}
            if ids & held:
                raise ValueError("Preflight temporal holdouts overlap")
            held.update(ids)
            support = {}
            for role, selected, threshold in (("train", fitted, tuning["minimum_train_class"]),
                                             ("holdout", scored, tuning["minimum_holdout_class"])):
                positives = sum(r["target"] for r in selected)
                support[role] = {"positive": positives, "negative": len(selected) - positives}
                if min(support[role].values()) < threshold:
                    raise ValueError("Preflight internal temporal-fold class support is insufficient")
            folds.append({"definition": spec, "support": support})
    count = 3 if settings["challenger_parameters"] is not None else 2
    inner = len(folds) * len(tuning["C_grid"]) if tuning is not None else 0
    return {"inner_temporal_folds": folds, "inner_candidate_fits": inner,
            "final_model_fits": count, "separate_calibration_fits": count,
            "total_declared_fit_calls": inner + 2 * count,
            "feature_dimension": feature_dimension,
            "train_encoded_matrix_bytes": len(train) * feature_dimension * 8,
            "all_development_encoded_matrix_bytes": len(records) * feature_dimension * 8,
            "memory_estimate_scope": "float64_encoded_matrices_only_excludes_python_rows_and_library_workspaces",
            "final_test_access": False}


def run(root: Path, study_id: str, feature_id: str, review_file: Path | None = None):
    root = root.resolve()
    if root.drive.upper() != "D:" or not isinstance(feature_id, str) or not FEATURE_ID.fullmatch(feature_id):
        raise ValueError("Private D: workspace and valid feature-audit ID required")
    service = ResearchService(root)
    study_folder, study, cases, study_digest = verify_prepared(service, study_id)
    feature_folder = contained(root, "artifacts/private/" + feature_id)
    summary = feature_summary(service, feature_folder, study, study_digest)
    feature_digest = sha256(feature_folder / "feature-complete.json")
    output = root / "artifacts/private" / ("assessment-" + uuid.uuid4().hex[:12])
    output.mkdir()
    started = time.perf_counter()
    provenance = {"schema_version": 1, "assessment_id": output.name, "study_id": study_id,
        "feature_audit_id": feature_id, "study_receipt_sha256": study_digest,
        "feature_receipt_sha256": feature_digest, "case_references": study["case_references"],
        "target": study["target"], "engine_commit": service.upstream["commit"],
        "method_version": VERSION, "method_source_sha256": sha256(Path(__file__)),
        "visibility": "private", "public_release_approved": False,
        "final_test_predictors_materialized": False, "final_test_scored": False,
        "champion_selected": False, "research_ready": False}
    write_new(output / "access-start.json", {
        "started_at": timestamp(), "purpose": "gated_development_assessment",
        "final_test_outcome_counts_may_be_read": bool(set(study["source_years"]) & set(study["protocol"]["test_years"])),
        "final_test_predictors_materialized": False, "final_test_scored": False})
    try:
        from crsl.models.train import require_training_gate, verify_split_assignments
        audit = read_json(study_folder / "split-audit.json")
        split = {"status": "SPLIT_AUDIT_COMPLETE", "training_ready": study["source_and_split_ready"],
                 "config": study["protocol"]}
        blockers = list(audit["blocking_reasons"])
        try:
            require_training_gate(split, audit)
        except ValueError:
            blockers.append("strict_development_training_gate_not_met")
        if summary["all_missing_train"] or not summary["encoder_fitted"]:
            blockers.append("feature_training_coverage_not_qualified")
        if review_file is None:
            blockers.append("development_feature_review_not_provided")
        if blockers:
            receipt = {**provenance, "status": "BLOCKED_BEFORE_FIT", "completed_at": timestamp(),
                       "blocking_reasons": sorted(set(blockers)), "model_training_performed": False,
                       "outputs_sha256": {"access-start.json": sha256(output / "access-start.json")}}
            write_new(output / "assessment-complete.json", receipt)
            return {"assessment_directory": str(output), "status": receipt["status"],
                    "blocking_reasons": receipt["blocking_reasons"], "model_training_performed": False}
        review_digest = sha256(review_file)
        review = read_json(review_file)
        settings = validate_review(review, study, study_digest, feature_id, feature_digest)
        write_new(output / "development-review.json", review)
        config = read_json(feature_folder / "feature-config.json")
        from crsl.features import OriginationEncoder
        encoder = OriginationEncoder(config)
        columns = ",".join("d." + name for name in encoder.numeric + encoder.categorical)
        records, labels = [], []
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            db.execute("SET threads=2")
            db.read_parquet(str(study_folder / "split_manifest.parquet")).create_view("assignments")
            for case in cases:
                for name, key in (("labels", "label_run"), ("dim_loan", "canonical_run")):
                    db.read_parquet(str(contained(root, case["manifest"][key]) / (name + ".parquet"))).create_view(name, replace=True)
                labels.extend(db.sql("SELECT loan_id,origination_year,target,label_known_month,landmark FROM labels").arrow().read_all().to_pylist())
                if db.sql("SELECT COUNT(*)-COUNT(DISTINCT loan_id) FROM dim_loan").fetchone()[0]:
                    raise ValueError("Duplicate feature-source loan keys")
                records.extend(db.sql(f"""SELECT l.loan_id,l.target,l.landmark,l.label_known_month,
                    a.partition,a.included,{columns}
                    FROM assignments a JOIN labels l USING(loan_id) JOIN dim_loan d USING(loan_id)
                    WHERE a.included AND a.partition IN ('train','calibration','validation')
                    ORDER BY a.partition,l.loan_id""").arrow().read_all().to_pylist())
        verify_split_assignments(labels, pq.read_table(study_folder / "split_manifest.parquet").to_pylist(),
                                 study["protocol"], audit)
        del labels
        for role in ("train", "calibration", "validation"):
            selected = [row for row in records if row["partition"] == role]
            if (len(selected) != sum(audit["support"][role].values())
                    or sum(row["target"] for row in selected) != audit["support"][role]["positive"]):
                raise ValueError("Development join does not preserve qualified split support")
        training = sorted((r for r in records if r["partition"] == "train"), key=lambda r: r["loan_id"])
        expected_encoder = OriginationEncoder(config).fit(training).state
        if expected_encoder != read_json(feature_folder / "encoder.json"):
            raise ValueError("Feature-audit encoder differs from the qualified training cohort")
        planning = fit_plan(records, settings, len(expected_encoder["feature_names"]))
        write_new(output / "fit-plan.json", planning)
        write_new(output / "fit-start.json", {**provenance, "started_at": timestamp(), "settings": settings,
                  "review_sha256": review_digest, "model_training_requested": True})
        from crsl.models.assessment import assess
        result = assess(records, config, settings, evidence_class="retrospective_development",
                        split_manifest=split, split_audit=audit)
        write_new(output / "assessment.json", json_ready(result))
        saved = read_json(output / "assessment.json")
        verification = verify_result(saved, records, output)
        write_new(output / "verification.json", verification)
        _, _, _, current_digest = verify_prepared(service, study_id)
        feature_summary(service, feature_folder, study, current_digest)
        if (current_digest != study_digest or sha256(feature_folder / "feature-complete.json") != feature_digest
                or sha256(review_file) != review_digest):
            raise ValueError("Development assessment inputs changed during fit")
        outputs = [p.name for p in output.iterdir() if p.is_file()]
        receipt = {**provenance, "status": "DEVELOPMENT_ASSESSMENT_VERIFIED", "completed_at": timestamp(),
                   "model_training_performed": True, "wall_seconds": time.perf_counter() - started,
                   "review_sha256": review_digest, "cohort_counts": saved["cohort_counts"],
                   "feature_contract_qualified_for_development": True,
                   "outputs_sha256": {name: sha256(output / name) for name in outputs}}
        write_new(output / "assessment-complete.json", receipt)
        return {"assessment_directory": str(output), "status": receipt["status"],
                "model_training_performed": True, "champion_selected": False, "final_test_scored": False}
    except Exception as error:
        from crsl.models.tuning import TuningFailed
        if isinstance(error, TuningFailed):
            write_new(output / "training-selection-failed.json", json_ready(error.result))
        write_new(output / "assessment-failed.json", {**provenance, "status": "FAIL",
                  "failed_at": timestamp(), "exception_type": type(error).__name__,
                  "fit_started": (output / "fit-start.json").exists()})
        raise
