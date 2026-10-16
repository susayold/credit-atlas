"""Read bounded, verified prepared studies as aggregate application evidence."""
from __future__ import annotations

import re
import math
from pathlib import Path

from .study_features import verify_prepared
from .workspace import contained, engine_root, read_json, sha256

FEATURE_ID = re.compile(r"feature-audit-[0-9a-f]{12}\Z")
ASSESSMENT_ID = re.compile(r"assessment-[0-9a-f]{12}\Z")
DTI_AUDIT_ID = re.compile(r"dti-mask-audit-[0-9a-f]{12}\Z")


def assessment_summary(service, folder, study, study_digest):
    """Verify private development artifacts, then expose aggregate fields only."""
    folder = contained(service.root, "artifacts/private/" + folder.name)
    receipt = read_json(folder / "assessment-complete.json")
    if (not isinstance(receipt, dict) or not ASSESSMENT_ID.fullmatch(folder.name)
            or receipt.get("assessment_id") != folder.name or receipt.get("schema_version") != 1
            or receipt.get("study_id") != study["study_id"]
            or receipt.get("study_receipt_sha256") != study_digest
            or receipt.get("case_references") != study["case_references"]
            or receipt.get("target") != study["target"]
            or receipt.get("engine_commit") != service.upstream["commit"]
            or receipt.get("method_version") != "d01-gated-development-assessment-v1"
            or receipt.get("method_source_sha256") != sha256(Path(__file__).with_name("assessment.py"))
            or receipt.get("visibility") != "private"
            or any(receipt.get(key) is not False for key in (
                "public_release_approved", "final_test_predictors_materialized", "final_test_scored",
                "champion_selected", "research_ready"))):
        raise ValueError("Assessment lineage or development contract changed")
    feature_id = receipt.get("feature_audit_id")
    if not isinstance(feature_id, str) or not FEATURE_ID.fullmatch(feature_id):
        raise ValueError("Invalid assessment feature reference")
    feature_folder = contained(service.root, "artifacts/private/" + feature_id)
    features = feature_summary(service, feature_folder, study, study_digest)
    if sha256(feature_folder / "feature-complete.json") != receipt.get("feature_receipt_sha256"):
        raise ValueError("Assessment feature receipt changed")
    status = receipt.get("status")
    expected = {"access-start.json"}
    if status == "BLOCKED_BEFORE_FIT":
        if receipt.get("model_training_performed") is not False:
            raise ValueError("Blocked assessment cannot claim training")
        blockers = receipt.get("blocking_reasons")
        if not isinstance(blockers, list) or not blockers or any(
                not isinstance(reason, str) or not re.fullmatch(r"[a-z_]{1,100}", reason) for reason in blockers):
            raise ValueError("Bounded blocker codes required")
    elif status == "DEVELOPMENT_ASSESSMENT_VERIFIED":
        if (receipt.get("model_training_performed") is not True
                or receipt.get("feature_contract_qualified_for_development") is not True
                or study.get("source_and_split_ready") is not True
                or features["encoder_fitted"] is not True or features["all_missing_train"]):
            raise ValueError("Explicit development training status required")
        expected |= {"development-review.json", "fit-plan.json", "fit-start.json",
                     "assessment.json", "verification.json"}
        result = read_json(folder / "assessment.json")
        models = result["models"]
        if (not {"constant", "logistic"} <= set(models) <= {"constant", "logistic", "challenger"}
                or result.get("status") != "development_assessment_complete"
                or result["cohort_counts"] != receipt["cohort_counts"]
                or result.get("evidence_class") != "retrospective_development"
                or any(result.get(key) is not False for key in (
                    "champion_selected", "final_test_access", "public_release_approved", "research_ready"))):
            raise ValueError("Development result contract changed")
        for name in models:
            expected |= {name + "-model.json", name + "-calibration.json"}
    else:
        raise ValueError("Unknown assessment stage")
    if set(receipt["outputs_sha256"]) != expected:
        raise ValueError("Complete assessment artifact digests required")
    for name, digest in receipt["outputs_sha256"].items():
        if sha256(folder / name) != digest:
            raise ValueError("Assessment evidence changed")
    access = read_json(folder / "access-start.json")
    if (access.get("purpose") != "gated_development_assessment"
            or access.get("final_test_predictors_materialized") is not False
            or access.get("final_test_scored") is not False):
        raise ValueError("Development access contract changed")
    summary = {key: receipt[key] for key in ("assessment_id", "feature_audit_id", "status",
               "completed_at", "model_training_performed", "final_test_scored", "champion_selected", "research_ready")}
    if status == "BLOCKED_BEFORE_FIT":
        summary["blocking_reasons"] = blockers
        return summary
    counts = result["cohort_counts"]
    from .assessment import validate_review
    settings = validate_review(read_json(folder / "development-review.json"), study,
                               study_digest, feature_id, receipt["feature_receipt_sha256"])
    fit_start = read_json(folder / "fit-start.json")
    if (settings != result["settings"] or settings != fit_start.get("settings")
            or fit_start.get("review_sha256") != receipt.get("review_sha256")
            or fit_start.get("model_training_requested") is not True):
        raise ValueError("Assessment settings differ from the reviewed fit")
    if counts != {role: sum(study["support"][role].values()) for role in ("train", "calibration", "validation")}:
        raise ValueError("Assessment cohort differs from prepared study")
    verification = read_json(folder / "verification.json")
    if (verification.get("status") != "PASS" or verification.get("final_test_scored") is not False
            or verification.get("score_sets_checked") != 2 * len(models)
            or verification.get("validation_loans") != counts["validation"]):
        raise ValueError("Persisted development verification incomplete")
    summary["cohort_counts"] = counts
    summary["validation_metrics"] = []
    for name, item in models.items():
        for variant in ("raw", "calibrated"):
            metrics = item["validation_metrics"][variant]
            if (metrics["loans"] != counts["validation"]
                    or metrics["events"] != study["support"]["validation"]["positive"]):
                raise ValueError("Validation denominator changed")
            row = {key: metrics[key] for key in ("loans", "events", "roc_auc", "average_precision", "brier_score", "log_loss")}
            for key in ("roc_auc", "average_precision", "brier_score", "log_loss"):
                value = row[key]
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value)
                        or value < 0 or key != "log_loss" and value > 1 + 1e-12):
                    raise ValueError("Invalid aggregate development metric")
            summary["validation_metrics"].append({"model": name, "variant": variant, **row})
    return summary


def feature_summary(service, folder, study, study_digest):
    folder = contained(service.root, "artifacts/private/" + folder.name)
    receipt = read_json(folder / "feature-complete.json")
    if not isinstance(receipt, dict):
        raise ValueError("Feature receipt must be an object")
    if (not FEATURE_ID.fullmatch(folder.name)
            or receipt.get("feature_audit_id") != folder.name
            or receipt.get("status") != "FEATURE_AUDIT_NOT_MODEL_READY"
            or receipt.get("schema_version") != 1
            or receipt.get("study_id") != study["study_id"]
            or receipt.get("study_receipt_sha256") != study_digest
            or receipt.get("case_references") != study["case_references"]
            or receipt.get("target") != study["target"]
            or receipt.get("engine_commit") != service.upstream["commit"]
            or receipt.get("method_source_sha256") != sha256(Path(__file__).with_name("study_features.py"))
            or receipt.get("feature_contract_qualified") is not False
            or receipt.get("model_fit_ready") is not False
            or receipt.get("model_training_performed") is not False
            or receipt.get("final_test_predictors_materialized") is not False
            or receipt.get("final_test_scored") is not False
            or receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False):
        raise ValueError("Feature audit lineage or private research contract changed")
    expected = {"access-start.json", "feature-coverage.json", "feature-config.json"}
    if receipt.get("encoder_fitted") is True:
        expected.add("encoder.json")
    elif receipt.get("encoder_fitted") is not False:
        raise ValueError("Explicit encoder status required")
    if set(receipt["outputs_sha256"]) != expected:
        raise ValueError("Complete feature artifact digests required")
    for name, digest in receipt["outputs_sha256"].items():
        if sha256(folder / name) != digest:
            raise ValueError("Feature audit evidence changed")
    config_file = engine_root(service.root) / "configs/features_origination.json"
    if (sha256(config_file) != receipt["feature_config_sha256"]
            or read_json(config_file) != read_json(folder / "feature-config.json")):
        raise ValueError("Pinned feature contract changed")
    coverage = read_json(folder / "feature-coverage.json")
    if (coverage["rows_by_partition"] != receipt["rows_by_partition"]
            or coverage["all_missing_train"] != receipt["all_missing_train"]):
        raise ValueError("Feature audit summary does not reconcile")
    config = read_json(config_file)
    names = set(config["numeric"] + config["categorical"])
    roles = {"train", "calibration", "validation"}
    for row in coverage["coverage"]:
        if (row["feature"] not in names or row["partition"] not in roles
                or row["kind"] not in {"numeric", "categorical"}
                or any(type(row[key]) is not int or row[key] < 0 for key in ("rows", "known", "missing"))
                or row["known"] + row["missing"] != row["rows"]
                or row["rows"] != coverage["rows_by_partition"][row["partition"]]):
            raise ValueError("Feature coverage uses an invalid grain or denominator")
    support = study["support"]
    if any(coverage["rows_by_partition"].get(role, 0) != sum(support[role].values())
           for role in ("train", "calibration", "validation")):
        raise ValueError("Feature population differs from prepared study")
    # Whitelist output fields; no private source loan IDs, notes or paths.
    return {"feature_audit_id": folder.name, "status": receipt["status"],
            "completed_at": receipt["completed_at"],
            "rows_by_partition": receipt["rows_by_partition"],
            "encoder_fitted": receipt["encoder_fitted"],
            "encoder_fit_partition": coverage.get("encoder_fit_partition"),
            "encoder_fit_rows": coverage.get("encoder_fit_rows", 0),
            "transform_parity": coverage["transform_parity"],
            "all_missing_train": receipt["all_missing_train"],
            "coverage": [{key: row[key] for key in
                         ("partition", "feature", "kind", "rows", "known", "missing", "missing_rate")}
                         for row in coverage["coverage"]],
            "blocking_reasons": receipt["blocking_reasons"],
            "model_fit_ready": False, "feature_contract_qualified": False,
            "final_test_predictors_materialized": False}


def dti_mask_summary(service, folder, study, cases, study_digest):
    """Verify private DTI mask evidence and return aggregate fields only."""
    from .dti_mask_audit import FAQ_URL, require_no_final_test_source

    folder = contained(service.root, "artifacts/private/" + folder.name)
    receipt = read_json(folder / "receipt.json")
    if (not isinstance(receipt, dict) or not DTI_AUDIT_ID.fullmatch(folder.name)
            or receipt.get("audit_id") != folder.name or receipt.get("schema_version") != 1
            or receipt.get("status") != "TRAIN_ONLY_DTI_MASK_AUDIT_COMPLETE"
            or receipt.get("study_receipt_sha256") != study_digest
            or receipt.get("model_training_performed") is not False
            or receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False):
        raise ValueError("DTI mask receipt lineage changed")
    require_no_final_test_source(study)
    audit_path, access_path = folder / "audit.json", folder / "access-start.json"
    if (sha256(audit_path) != receipt.get("audit_sha256")
            or sha256(access_path) != receipt.get("access_start_sha256")):
        raise ValueError("DTI mask evidence digest changed")
    access = read_json(access_path)
    if (access.get("purpose") != "train_only_dti_sentinel_and_segment_coverage_audit"
            or access.get("final_test_predictors_materialized") is not False
            or access.get("final_test_labels_read") is not False
            or access.get("model_training_performed") is not False):
        raise ValueError("DTI audit access boundary changed")
    audit = read_json(audit_path)
    if (audit.get("schema_version") != 1
            or audit.get("status") != receipt.get("status")
            or audit.get("study_id") != study["study_id"]
            or audit.get("method_version") != "d01-train-dti-mask-audit-v1"
            or audit.get("method_source_sha256") != sha256(Path(__file__).with_name("dti_mask_audit.py"))
            or audit.get("study_receipt_sha256") != study_digest
            or audit.get("target") != study["target"]
            or audit.get("source_years") != study["source_years"]
            or audit.get("case_references") != study["case_references"]
            or audit.get("protocol_sha256") != study["protocol_sha256"]
            or audit.get("train_support") != study["support"]["train"]
            or audit.get("visibility") != "private"
            or audit.get("public_release_approved") is not False
            or audit.get("access") != {"partition": "train", "final_test_labels_read": False,
                                        "final_test_predictors_materialized": False,
                                        "model_training_performed": False}):
        raise ValueError("DTI mask audit lineage or access contract changed")
    expected_inputs = {"split_manifest.parquet": sha256(
        contained(service.root, "artifacts/private/" + study["study_id"]) / "split_manifest.parquet")}
    for case, reference in zip(cases, study["case_references"]):
        case_id = case["manifest"]["case_id"]
        if case_id != reference["case_id"]:
            raise ValueError("DTI audit case order changed")
        expected_inputs[f"{case_id}:labels.parquet"] = sha256(
            contained(service.root, str(Path(case["manifest"]["label_run"]) / "labels.parquet")))
        expected_inputs[f"{case_id}:dim_loan.parquet"] = sha256(
            contained(service.root, str(Path(case["manifest"]["canonical_run"]) / "dim_loan.parquet")))
    if audit.get("input_sha256") != expected_inputs:
        raise ValueError("DTI mask inputs changed")
    semantics = audit.get("source_semantics")
    if semantics != {"source_token": "999", "canonical_value": None,
                     "non_relief_meaning": "DTI greater than 65 percent OR not available; source does not distinguish these",
                     "relief_meaning": "always disclosed as 999; Freddie says DTI is masked due to differing streamlined-refinance income-verification requirements",
                     "official_faq": FAQ_URL}:
        raise ValueError("DTI source semantics changed")
    groups = audit.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("DTI groups missing")
    safe_groups = []
    for row in groups:
        if (not isinstance(row, dict) or set(row) != {"segment", "dti_status", "loans", "positive", "negative"}
                or row["segment"] not in {"Relief", "Non-Relief"}
                or row["dti_status"] not in {"observed", "sentinel_999_censored_or_unavailable", "blank_or_other_missing"}
                or any(type(row[key]) is not int or row[key] < 0 for key in ("loans", "positive", "negative"))
                or row["loans"] != row["positive"] + row["negative"]):
            raise ValueError("DTI group grain invalid")
        safe_groups.append({key: row[key] for key in
                            ("segment", "dti_status", "loans", "positive", "negative")})
    support = study["support"]["train"]
    if (sum(row["loans"] for row in safe_groups) != support["positive"] + support["negative"]
            or sum(row["positive"] for row in safe_groups) != support["positive"]
            or sum(row["negative"] for row in safe_groups) != support["negative"]):
        raise ValueError("DTI audit does not reconcile to prepared train support")
    return {"audit_id": folder.name, "status": receipt["status"],
            "completed_at": receipt["completed_at"], "groups": safe_groups,
            "source_semantics": {key: semantics[key] for key in
                                 ("source_token", "non_relief_meaning", "relief_meaning", "official_faq")},
            "final_test_access": False, "model_training_performed": False}


def list_studies(service, case_id):
    service.case(case_id)
    private = service.root / "artifacts/private"
    studies = sorted(private.glob("study-*/study-complete.json"),
                     key=lambda path: path.stat().st_mtime_ns, reverse=True)
    features = sorted(private.glob("feature-audit-*/feature-complete.json"),
                      key=lambda path: path.stat().st_mtime_ns, reverse=True)
    assessments = sorted(private.glob("assessment-*/assessment-complete.json"),
                         key=lambda path: path.stat().st_mtime_ns, reverse=True)
    dti_audits = sorted(private.glob("dti-mask-audit-*/receipt.json"),
                        key=lambda path: path.stat().st_mtime_ns, reverse=True)
    items = []
    unreadable = set()
    for path in studies[:100]:
        try:
            receipt = read_json(path)
            references = receipt.get("case_references", [])
            if not any(reference.get("case_id") == case_id for reference in references):
                continue
        except (ValueError, KeyError, TypeError, AttributeError, OSError):
            unreadable.add(str(path))
            continue
        try:
            folder, study, cases, digest = verify_prepared(service, path.parent.name)
            feature_items = []
            for feature_path in features[:100]:
                try:
                    feature_receipt = read_json(feature_path)
                    if not isinstance(feature_receipt, dict):
                        raise ValueError("Feature receipt must be an object")
                except (ValueError, KeyError, TypeError, OSError):
                    unreadable.add(str(feature_path))
                    continue
                if feature_receipt.get("study_id") != folder.name:
                    continue
                try:
                    feature_items.append(feature_summary(service, feature_path.parent, study, digest))
                except (ValueError, KeyError, TypeError, OSError):
                    feature_items.append({"feature_audit_id": feature_path.parent.name,
                                          "status": "evidence_unavailable_or_changed"})
            assessment_items = []
            for assessment_path in assessments[:100]:
                try:
                    assessment_receipt = read_json(assessment_path)
                    if not isinstance(assessment_receipt, dict):
                        raise ValueError("Assessment receipt must be an object")
                except (ValueError, KeyError, TypeError, OSError):
                    unreadable.add(str(assessment_path))
                    continue
                if assessment_receipt.get("study_id") != folder.name:
                    continue
                try:
                    assessment_items.append(assessment_summary(service, assessment_path.parent, study, digest))
                except (ValueError, KeyError, TypeError, OSError):
                    assessment_items.append({"assessment_id": assessment_path.parent.name,
                                             "status": "evidence_unavailable_or_changed"})
            dti_items = []
            for audit_path in dti_audits[:100]:
                try:
                    audit_receipt = read_json(audit_path)
                    if not isinstance(audit_receipt, dict):
                        raise ValueError("DTI audit receipt must be an object")
                except (ValueError, KeyError, TypeError, OSError):
                    unreadable.add(str(audit_path))
                    continue
                if audit_receipt.get("study_id") not in (None, folder.name):
                    continue
                # The stable study reference is stored in audit.json, so inspect it
                # only to select this study; the verifier below validates its digest.
                try:
                    audit_doc = read_json(audit_path.parent / "audit.json")
                except (ValueError, KeyError, TypeError, OSError):
                    dti_items.append({"audit_id": audit_path.parent.name,
                                      "status": "evidence_unavailable_or_changed"})
                    continue
                if not isinstance(audit_doc, dict) or audit_doc.get("study_id") != folder.name:
                    continue
                try:
                    dti_items.append(dti_mask_summary(service, audit_path.parent, study, cases, digest))
                except (ValueError, KeyError, TypeError, OSError):
                    dti_items.append({"audit_id": audit_path.parent.name,
                                      "status": "evidence_unavailable_or_changed"})
            items.append({"study_id": folder.name, "status": study["status"],
                          "completed_at": study["completed_at"], "source_years": study["source_years"],
                          "source_and_split_ready": study["source_and_split_ready"],
                          "model_fit_ready": False, "support": study["support"],
                          "blocking_reasons": study["blocking_reasons"], "feature_audits": feature_items,
                          "assessments": assessment_items, "dti_mask_audits": dti_items})
        except (ValueError, KeyError, TypeError, OSError):
            # Legacy schema-1 references require preparation with a saved protocol.
            items.append({"study_id": path.parent.name,
                          "status": "evidence_unavailable_or_legacy"})
    return {"case_id": case_id, "studies": items, "scan_limit_per_artifact_kind": 100,
            "unreadable_artifacts": len(unreadable),
            "scan_truncated": any(len(paths) > 100 for paths in (studies, features, assessments, dti_audits)),
            "visibility": "private", "public_release_approved": False,
            "scope_note": "Preparation, features and development validation remain separate stages; no champion or final out-of-time scores."}
