"""Private train-only feature audit. Never fits risk models or scores final test."""
from __future__ import annotations

import copy
import hashlib
import math
import re
import struct
import time
import uuid
from collections import Counter
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from .service import ResearchService
from .snapshot import TARGET, json_ready
from .workspace import contained, engine_root, read_json, sha256, timestamp, write_new

VERSION = "d01-development-feature-audit-v1"
STUDY_ID = re.compile(r"study-[0-9a-f]{12}\Z")
ROLES = ("train", "calibration", "validation")


def verify_prepared(service, study_id):
    if not isinstance(study_id, str) or not STUDY_ID.fullmatch(study_id):
        raise ValueError("Invalid prepared study ID")
    folder = contained(service.root, "artifacts/private/" + study_id)
    receipt_path = folder / "study-complete.json"
    receipt = read_json(receipt_path)
    if (receipt.get("schema_version") != 2 or receipt.get("study_id") != study_id
            or receipt.get("status") != "PREPARED_NOT_FIT_READY"
            or receipt.get("engine_commit") != service.upstream["commit"]
            or receipt.get("target") != TARGET or receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False
            or receipt.get("model_training_performed") is not False
            or receipt.get("model_fit_ready") is not False):
        raise ValueError("Verified schema-2 prepared study required; rerun prepare-study if needed")
    expected = {"split_manifest.parquet", "split-audit.json", "access-start.json", "protocol.json"}
    if set(receipt["outputs_sha256"]) != expected:
        raise ValueError("Complete prepared study digests required")
    for name, digest in receipt["outputs_sha256"].items():
        if sha256(folder / name) != digest:
            raise ValueError("Prepared study evidence changed")
    if (sha256(folder / "protocol.json") != receipt["protocol_sha256"]
            or read_json(folder / "protocol.json") != receipt["protocol"]):
        raise ValueError("Frozen protocol does not match prepared study")
    references = receipt["case_references"]
    ids = [reference["case_id"] for reference in references]
    if not 1 <= len(ids) <= 12 or len(ids) != len(set(ids)):
        raise ValueError("Distinct prepared source cases required")
    cases = [service.case(identifier) for identifier in ids]
    years = []
    for case, reference in zip(cases, references):
        if (case["complete_hash"] != reference["case_receipt_sha256"]
                or case["manifest"]["pipeline_run"] != reference["pipeline_run"]
                or case["snapshot"]["source_release"] != 47):
            raise ValueError("Prepared study source lineage changed")
        years.extend(case["snapshot"]["source_years"])
    if sorted(years) != receipt["source_years"] or len(years) != len(set(years)):
        raise ValueError("Prepared annual source vintages do not reconcile")
    return folder, receipt, cases, sha256(receipt_path)


def encode_audit(records, config):
    """Pure engineering audit: labels/identities are metadata, never predictors."""
    from crsl.features import OriginationEncoder
    encoder = OriginationEncoder(config)
    fields = encoder.numeric + encoder.categorical
    counts = Counter()
    seen = set()
    for row in records:
        identity = row.get("loan_id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("Feature population must contain unique loans")
        seen.add(identity)
        if row.get("partition") not in ROLES or row.get("included") is not True:
            raise ValueError("Only included development rows may enter the feature audit")
        if any(field not in row for field in fields):
            raise ValueError("Missing canonical feature column")
        counts[row["partition"]] += 1
    train = [row for row in records if row["partition"] == "train"]
    if not train:
        return None, {"status": "NO_INCLUDED_TRAIN", "rows_by_partition": dict(counts),
                      "coverage": [], "all_missing_train": [], "transform_parity": "UNAVAILABLE"}
    encoder.fit(train)
    fitted = copy.deepcopy(encoder.state)
    coverage = []
    digest = hashlib.sha256()
    for role in ROLES:
        selected = [row for row in records if row["partition"] == role]
        for field in fields:
            observed = [row[field] for row in selected if row[field] is not None]
            categorical = field in encoder.categorical
            item = {"partition": role, "feature": field,
                    "kind": "categorical" if categorical else "numeric",
                    "rows": len(selected), "known": len(observed),
                    "missing": len(selected) - len(observed),
                    "missing_rate": (len(selected) - len(observed)) / len(selected) if selected else None}
            if categorical:
                vocabulary = fitted["categorical"][field]
                item["unseen"] = sum("value:" + value not in vocabulary for value in observed)
                item["distinct_known_categories"] = len(set(observed))
            else:
                item["minimum"] = min(observed) if observed else None
                item["maximum"] = max(observed) if observed else None
            coverage.append(item)
        for start in range(0, len(selected), 10000):
            vectors = encoder.transform(selected[start:start + 10000])
            for vector in vectors:
                if any(not math.isfinite(value) for value in vector):
                    raise ValueError("Nonfinite encoded feature")
                digest.update(struct.pack("<" + "d" * len(vector), *vector))
    if fitted != encoder.state:
        raise ValueError("Development transform changed fitted training state")
    missing = [item["feature"] for item in coverage if item["partition"] == "train"
               and item["known"] == 0]
    return encoder, json_ready({
        "status": "TRAIN_ONLY_ENCODER_AUDITED", "rows_by_partition": {r: counts[r] for r in ROLES},
        "coverage": coverage, "all_missing_train": missing,
        "encoder_fit_partition": "train", "encoder_fit_rows": len(train),
        "feature_names": fitted["feature_names"], "development_matrix_sha256": digest.hexdigest(),
        "matrix_hash_format": "role_order_train_calibration_validation_then_source_sorted_rows_float64_little_endian",
        "transform_mutates_fit": False,
        "ablation_review": [{"feature": field, "reason": "all_missing_train",
                            "required_action": "review exclusion or separately frozen ablation; not automatically qualified"}
                           for field in missing]})


def prepare_features(root: Path, study_id: str):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("Feature study storage must remain on D:")
    service = ResearchService(root)
    folder, study, cases, receipt_digest = verify_prepared(service, study_id)
    config_file = engine_root(root) / "configs/features_origination.json"
    config = read_json(config_file)
    config_digest = sha256(config_file)
    from crsl.features import OriginationEncoder
    validated = OriginationEncoder(config)
    fields = validated.numeric + validated.categorical
    output = root / "artifacts/private" / ("feature-audit-" + uuid.uuid4().hex[:12])
    output.mkdir()
    start = time.perf_counter()
    write_new(output / "access-start.json", {
        "started_at": timestamp(), "study_id": study_id, "purpose": "split_reverification_and_development_feature_audit",
        "final_test_predictors_materialized": False, "final_test_scored": False,
        "final_test_outcome_counts_may_be_read": bool(set(study["source_years"]) & set(study["protocol"]["test_years"])),
        "model_selection_performed": False,
        "note": "Source split recheck can read final-test label support; this is logged and is not model selection."})
    try:
        from crsl.models.train import verify_split_assignments
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            db.execute("SET threads=2")
            labels = []
            for case in cases:
                labels.extend(db.read_parquet(str(contained(root, case["manifest"]["label_run"]) /
                                                   "labels.parquet")).project(
                    "loan_id,origination_year,target,label_known_month,landmark").arrow().read_all().to_pylist())
            assignments = pq.read_table(folder / "split_manifest.parquet").to_pylist()
            audit = verify_split_assignments(labels, assignments, study["protocol"], read_json(folder / "split-audit.json"))
            if (audit["support"] != study["support"] or len(labels) != study["label_rows"]
                    or audit["training_ready"] != study["source_and_split_ready"]):
                raise ValueError("Prepared study support does not reconcile")
            del labels, assignments
            db.read_parquet(str(folder / "split_manifest.parquet")).create_view("assignments")
            records = []
            for case in cases:
                for name, key in (("labels", "label_run"), ("dim_loan", "canonical_run")):
                    db.read_parquet(str(contained(root, case["manifest"][key]) / (name + ".parquet"))).create_view(name, replace=True)
                if db.execute("SELECT COUNT(*)-COUNT(DISTINCT loan_id) FROM dim_loan").fetchone()[0]:
                    raise ValueError("Duplicate feature source loan keys")
                selected_columns = ",".join("d." + field for field in fields)
                records.extend(db.execute(f"""SELECT l.loan_id,l.origination_year,l.landmark,l.label_known_month,
                    l.target,a.partition,a.included,{selected_columns}
                    FROM assignments a JOIN labels l USING(loan_id) JOIN dim_loan d USING(loan_id)
                    WHERE a.included AND a.partition IN ('train','calibration','validation')
                    ORDER BY l.loan_id""").arrow().read_all().to_pylist())
            records.sort(key=lambda row: (ROLES.index(row["partition"]), row["loan_id"]))
            for role in ROLES:
                selected = [r for r in records if r["partition"] == role]
                if (len(selected) != sum(audit["support"][role].values())
                        or sum(r["target"] for r in selected) != audit["support"][role]["positive"]):
                    raise ValueError("Development feature join must preserve split population and targets")
            encoder, coverage = encode_audit(records, config)
            outputs = ["access-start.json", "feature-coverage.json", "feature-config.json"]
            if encoder is not None:
                write_new(output / "encoder.json", encoder.state)
                restored = OriginationEncoder(config)
                restored.state = read_json(output / "encoder.json")
                for start_at in range(0, len(records), 10000):
                    batch = records[start_at:start_at + 10000]
                    if encoder.transform(batch) != restored.transform(batch):
                        raise ValueError("Saved encoder must reproduce native development vectors")
                coverage["transform_parity"] = "PASS_ALL_DEVELOPMENT_ROWS"
                outputs.append("encoder.json")
            write_new(output / "feature-config.json", config)
            write_new(output / "feature-coverage.json", coverage)
        # Recheck immutable source and study after the audit, before completion.
        _, _, _, current_digest = verify_prepared(service, study_id)
        if current_digest != receipt_digest or sha256(config_file) != config_digest:
            raise ValueError("Feature preparation inputs changed")
        result = {"schema_version": 1, "status": "FEATURE_AUDIT_NOT_MODEL_READY",
                  "method_version": VERSION, "method_source_sha256": sha256(Path(__file__)),
                  "completed_at": timestamp(), "feature_audit_id": output.name,
                  "study_id": study_id, "study_receipt_sha256": receipt_digest,
                  "engine_commit": service.upstream["commit"], "target": TARGET,
                  "source_years": study["source_years"], "case_references": study["case_references"],
                  "feature_config_sha256": config_digest,
                  "rows_by_partition": coverage["rows_by_partition"],
                  "all_missing_train": coverage["all_missing_train"],
                  "source_and_split_ready": study["source_and_split_ready"],
                  "feature_contract_qualified": False, "model_fit_ready": False,
                  "blocking_reasons": sorted(set(study["blocking_reasons"] + ["feature_availability_review_not_frozen"])),
                  "encoder_fitted": encoder is not None, "model_training_performed": False,
                  "final_test_predictors_materialized": False, "final_test_scored": False,
                  "wall_seconds": time.perf_counter() - start,
                  "outputs_sha256": {name: sha256(output / name) for name in outputs},
                  "limitations": ["Engineering preprocessing audit, not a fitted risk model or feature qualification.",
                                  "Latest-release origination values; archival historical availability is unverified.",
                                  "No final-test predictors, model scores or development performance metrics.",
                                  "All-missing fields require reviewed exclusion/ablation before qualified model fitting."],
                  "visibility": "private", "public_release_approved": False}
        write_new(output / "feature-complete.json", result)
        return {"feature_directory": str(output), "status": result["status"],
                "rows_by_partition": result["rows_by_partition"],
                "all_missing_train": result["all_missing_train"], "model_fit_ready": False}
    except Exception as error:
        write_new(output / "feature-failed.json", {"status": "FAIL", "failed_at": timestamp(),
                  "exception_type": type(error).__name__, "model_training_performed": False})
        raise
