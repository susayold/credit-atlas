"""Train-only audit of Freddie's original-DTI sentinel and segment coverage."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import uuid

import duckdb

from .service import ResearchService
from .study_features import verify_prepared
from .workspace import contained, sha256, timestamp, write_new

FAQ_URL = "https://www.freddiemac.com/fmac-resources/research/pdf/faq.pdf"


def require_no_final_test_source(study):
    test_years = set(study["protocol"]["test_years"])
    if test_years.intersection(study["source_years"]):
        raise ValueError("DTI audit refuses studies containing final-test vintages")
    if any(study["support"]["test"].values()):
        raise ValueError("DTI audit refuses nonempty final-test support")


def aggregate_train_rows(rows):
    """Validate and summarize training-only records without returning loan IDs."""
    seen = set()
    counts = Counter()
    for row in rows:
        identity = row.get("loan_id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("DTI audit requires unique source loans")
        seen.add(identity)
        if row.get("partition") != "train" or row.get("included") is not True:
            raise ValueError("DTI audit accepts included training rows only")
        target = row.get("target")
        if type(target) is not int or target not in (0, 1):
            raise ValueError("DTI audit target must be a binary included label")
        if type(row.get("is_relief_refinance")) is not bool:
            raise ValueError("Relief segment must be explicitly known")

        raw = (row.get("raw_original_dti") or "").strip()
        value = row.get("original_dti")
        if raw == "999":
            if value is not None:
                raise ValueError("DTI sentinel 999 must remain null in the canonical field")
            status = "sentinel_999_censored_or_unavailable"
        elif value is None:
            status = "blank_or_other_missing"
        else:
            if raw == "" or str(value) != raw:
                # Integer DTI values are disclosed as integer percentages.
                if type(value) is not int or raw != str(value):
                    raise ValueError("Raw and canonical DTI values do not reconcile")
            if type(value) is not int or not 0 <= value <= 65:
                raise ValueError("Observed DTI must be an integer percentage from 0 through 65")
            status = "observed"

        segment = "Relief" if row["is_relief_refinance"] else "Non-Relief"
        counts[(segment, status, target)] += 1

    keys = sorted({(segment, status) for segment, status, _target in counts})
    return [{
        "segment": segment,
        "dti_status": status,
        "loans": counts[(segment, status, 0)] + counts[(segment, status, 1)],
        "positive": counts[(segment, status, 1)],
        "negative": counts[(segment, status, 0)],
    } for segment, status in keys]


def run(root: Path, study_id: str):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("DTI audit artifacts must remain on D:")
    service = ResearchService(root)
    folder, study, cases, study_digest = verify_prepared(service, study_id)
    if study.get("model_training_performed") is not False:
        raise ValueError("The DTI mask audit cannot inspect a fitted study")
    require_no_final_test_source(study)

    output = root / "artifacts/private" / ("dti-mask-audit-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "access-start.json", {
        "started_at": timestamp(), "study_id": study_id,
        "purpose": "train_only_dti_sentinel_and_segment_coverage_audit",
        "partition_filter": "included train rows only",
        "final_test_predictors_materialized": False,
        "final_test_labels_read": False,
        "model_training_performed": False,
        "note": "No loan identifiers or row-level data are included in the result."})

    try:
        db = duckdb.connect()
        db.execute("SET memory_limit='1GB'")
        db.execute("SET threads=2")
        all_groups = Counter()
        input_hashes = {"split_manifest.parquet": sha256(folder / "split_manifest.parquet")}
        for case, case_reference in zip(cases, study["case_references"]):
            label_path = contained(root, str(Path(case["manifest"]["label_run"]) / "labels.parquet"))
            loan_path = contained(root, str(Path(case["manifest"]["canonical_run"]) / "dim_loan.parquet"))
            case_id = case_reference["case_id"]
            input_hashes[f"{case_id}:labels.parquet"] = sha256(label_path)
            input_hashes[f"{case_id}:dim_loan.parquet"] = sha256(loan_path)
            query = db.execute("""
                SELECT l.loan_id, a.partition, a.included, l.target,
                       d.is_relief_refinance, d.raw_original_dti, d.original_dti
                FROM read_parquet(?) a
                JOIN read_parquet(?) l USING (loan_id)
                JOIN read_parquet(?) d USING (loan_id)
                WHERE a.partition='train' AND a.included
                ORDER BY l.loan_id
            """, [str(folder / "split_manifest.parquet"), str(label_path), str(loan_path)])
            for group in aggregate_train_rows(query.fetch_arrow_table().to_pylist()):
                key = (group["segment"], group["dti_status"])
                all_groups[(*key, 0)] += group["negative"]
                all_groups[(*key, 1)] += group["positive"]

        support = study["support"]["train"]
        if sum(all_groups.values()) != support["positive"] + support["negative"]:
            raise ValueError("DTI audit grain does not reconcile to the prepared train support")
        group_keys = sorted({key[:2] for key in all_groups})
        groups = [
            {"segment": segment, "dti_status": status,
             "loans": all_groups[(segment, status, 0)] + all_groups[(segment, status, 1)],
             "positive": all_groups[(segment, status, 1)],
             "negative": all_groups[(segment, status, 0)]}
            for segment, status in group_keys
        ]
        audit = {
            "schema_version": 1,
            "status": "TRAIN_ONLY_DTI_MASK_AUDIT_COMPLETE",
            "study_id": study_id,
            "method_version": "d01-train-dti-mask-audit-v1",
            "method_source_sha256": sha256(Path(__file__)),
            "study_receipt_sha256": study_digest,
            "target": study["target"],
            "source_years": study["source_years"],
            "case_references": study["case_references"],
            "protocol_sha256": study["protocol_sha256"],
            "train_support": support,
            "groups": groups,
            "source_semantics": {
                "source_token": "999",
                "canonical_value": None,
                "non_relief_meaning": "DTI greater than 65 percent OR not available; source does not distinguish these",
                "relief_meaning": "always disclosed as 999; Freddie says DTI is masked due to differing streamlined-refinance income-verification requirements",
                "official_faq": FAQ_URL,
            },
            "access": {"partition": "train", "final_test_labels_read": False,
                       "final_test_predictors_materialized": False,
                       "model_training_performed": False},
            "input_sha256": input_hashes,
            "visibility": "private",
            "public_release_approved": False,
        }
        write_new(output / "audit.json", audit)
        receipt = {
            "schema_version": 1,
            "status": audit["status"],
            "audit_id": output.name,
            "completed_at": timestamp(),
            "audit_sha256": sha256(output / "audit.json"),
            "access_start_sha256": sha256(output / "access-start.json"),
            "study_receipt_sha256": study_digest,
            "model_training_performed": False,
            "visibility": "private",
            "public_release_approved": False,
        }
        write_new(output / "receipt.json", receipt)
        return {"status": receipt["status"], "audit_id": output.name,
                "receipt": str(output / "receipt.json"), "groups": groups,
                "model_training_performed": False}
    except Exception as error:
        write_new(output / "failed.json", {
            "status": "FAIL", "failed_at": timestamp(),
            "exception_type": type(error).__name__,
            "model_training_performed": False,
        })
        raise

