"""Prepare auditable temporal-study inputs; this command never fits a model."""
from __future__ import annotations

import time
import hashlib
import json
import uuid
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .service import ResearchService
from .workspace import contained, engine_root, read_json, sha256, timestamp, write_new


def prepare(root: Path, case_ids: list[str], protocol_file: Path | None = None):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("New study artifacts must remain on D:")
    if not 1 <= len(case_ids) <= 12 or len(case_ids) != len(set(case_ids)):
        raise ValueError("One to twelve distinct verified cases are required")
    service = ResearchService(root)
    cases = [service.case(identifier) for identifier in case_ids]
    years = []
    for case in cases:
        years.extend(case["snapshot"]["source_years"])
        if case["snapshot"]["source_release"] != 47:
            raise ValueError("Study sources must share the supported Release 47 contract")
    if len(years) != len(set(years)):
        raise ValueError("Overlapping annual source vintages cannot be pooled as independent samples")
    protocol_file = protocol_file or engine_root(root) / "configs/split.json"
    protocol_bytes = protocol_file.read_bytes()
    protocol_digest = hashlib.sha256(protocol_bytes).hexdigest()
    protocol = json.loads(protocol_bytes)
    from crsl.splits import split_records
    # Validate protocol chronology even before opening source label files.
    split_records([], protocol)
    output = root / "artifacts/private" / ("study-" + uuid.uuid4().hex[:12])
    output.mkdir()
    start = time.perf_counter()
    test_years = set(protocol["test_years"])
    test_sources = [identifier for identifier, case in zip(case_ids, cases)
                    if test_years.intersection(case["snapshot"]["source_years"])]
    write_new(output / "access-start.json", {
        "started_at": timestamp(), "purpose": "pre_fit_support_and_timing_audit",
        "final_test_source_cases": test_sources, "final_test_outcome_counts_may_be_read": bool(test_sources),
        "model_selection_performed": False, "protocol_sha256": protocol_digest,
        "upstream_analytical_access_history": "not_established_by_this_command",
        "note": "Support audit is logged; inspected cohorts must not later be described as completely untouched."})
    records = []
    try:
        with (output / "protocol.json").open("xb") as stream:
            stream.write(protocol_bytes)
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            db.execute("SET threads=2")
            for case in cases:
                path = contained(root, case["manifest"]["label_run"]) / "labels.parquet"
                records.extend(db.read_parquet(str(path)).project(
                    "loan_id,origination_year,target,label_known_month,landmark").arrow().read_all().to_pylist())
        for identifier in case_ids:
            service.case(identifier)
        if sha256(protocol_file) != protocol_digest:
            raise ValueError("Study protocol changed during preparation")
        assignments, audit = split_records(records, protocol)
        schema = pa.schema([("loan_id", pa.string()), ("partition", pa.string()),
                            ("reason", pa.string()), ("included", pa.bool_()), ("test_locked", pa.bool_())])
        pq.write_table(pa.Table.from_pylist(assignments, schema=schema),
                       output / "split_manifest.parquet", compression="zstd")
        write_new(output / "split-audit.json", audit)
        # Split readiness alone cannot certify the feature/selection/serving study.
        blocking = sorted(set(audit["blocking_reasons"] + ["feature_contract_not_qualified", "study_not_frozen"]))
        receipt = {"schema_version": 2, "status": "PREPARED_NOT_FIT_READY", "completed_at": timestamp(),
                   "study_id": output.name, "engine_commit": service.upstream["commit"],
                   "target": cases[0]["snapshot"]["target"], "source_years": sorted(years),
                   "case_references": [{"case_id": identifier, "case_receipt_sha256": case["complete_hash"],
                                        "pipeline_run": case["manifest"]["pipeline_run"]}
                                       for identifier, case in zip(case_ids, cases)],
                   "protocol": protocol, "protocol_sha256": protocol_digest,
                   "method_version": "d01-temporal-study-preparation-v1",
                   "method_source_sha256": sha256(Path(__file__)),
                   "source_and_split_ready": audit["training_ready"], "model_fit_ready": False,
                   "blocking_reasons": blocking, "support": audit["support"],
                   "label_rows": len(records), "model_training_performed": False,
                   "wall_seconds": time.perf_counter() - start,
                   "outputs_sha256": {name: sha256(output / name) for name in
                                      ["split_manifest.parquet", "split-audit.json", "access-start.json", "protocol.json"]},
                   "visibility": "private", "public_release_approved": False}
        write_new(output / "study-complete.json", receipt)
        return {"study_directory": str(output), "status": receipt["status"],
                "source_and_split_ready": audit["training_ready"], "model_fit_ready": False,
                "support": audit["support"], "blocking_reasons": blocking}
    except Exception as error:
        write_new(output / "study-failed.json", {"status": "FAIL", "exception_type": type(error).__name__,
                                               "failed_at": timestamp(), "model_training_performed": False})
        raise
