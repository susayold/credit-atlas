"""One-time, frozen-model evaluation of the reserved random retail cohort."""
from __future__ import annotations

import hashlib
import math
import sqlite3
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.special import expit

from .retail import NUMERIC_FEATURES, CATEGORICAL_FEATURES
from .retail_features import RetailEncoder
from .retail_assessment import predict_json, metrics, logit
from .retail_freeze import verify_freeze
from .workspace import contained, read_json, sha256, timestamp, write_new


def frozen_transform(state, rows, role="final_test"):
    """Explicit evaluation codec: reuse saved state, never fit or learn categories."""
    encoder = RetailEncoder.restore(state)
    if role not in ("validation", "final_test") or any(r.get("partition") != role for r in rows):
        raise ValueError("Frozen evaluation requires one explicit permitted partition")
    matrix = np.zeros((len(rows), len(state["feature_names"])), dtype=np.float64)
    for i, row in enumerate(rows):
        for j, name in enumerate(NUMERIC_FEATURES):
            value = row[name]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Finite numeric holdout value required")
            stats = state["numeric"][name]
            matrix[i, j] = (value - stats["mean"]) / stats["scale"]
        offset = len(NUMERIC_FEATURES)
        for name in CATEGORICAL_FEATURES:
            values = state["categorical"][name]
            category = encoder.category(row[name])
            matrix[i, offset + values.index(category if category in values else "__unseen__")] = 1
            offset += len(values)
    if not np.isfinite(matrix).all():
        raise ValueError("Invalid frozen holdout matrix")
    return matrix


def check_codec(state):
    # Exercise every source status including unseen buckets before any holdout read.
    probes = [{"partition": "validation", **{n: state["numeric"][n]["mean"] + k * state["numeric"][n]["scale"]
               for n in NUMERIC_FEATURES}, **{n: k for n in CATEGORICAL_FEATURES}} for k in range(-2, 10)]
    if not np.array_equal(frozen_transform(state, probes, "validation"), RetailEncoder.restore(state).transform(probes)):
        raise ValueError("Frozen codec differs from development encoder")


def claim_holdout(ledger, fingerprint, freeze_digest, output):
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ledger, timeout=30) as db:
        db.execute("CREATE TABLE IF NOT EXISTS evaluations (fingerprint TEXT PRIMARY KEY, freeze_digest TEXT NOT NULL, output TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL)")
        try:
            db.execute("INSERT INTO evaluations VALUES (?,?,?,'started',?)", (fingerprint, freeze_digest, str(output), timestamp()))
        except sqlite3.IntegrityError as error:
            raise ValueError("This source/split holdout has already been claimed; use saved evidence, do not reselect or rescore") from error


def finish_claim(ledger, fingerprint, status):
    with sqlite3.connect(ledger, timeout=30) as db:
        changed = db.execute("UPDATE evaluations SET status=? WHERE fingerprint=? AND status='started'", (status, fingerprint)).rowcount
        if changed != 1:
            raise ValueError("Holdout access ledger state changed")


def evaluate_holdout(root: Path, freeze_id: str):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("Private D: workspace required")
    bundle, frozen, digest, case_folder, case = verify_freeze(root, freeze_id)
    state, model = read_json(bundle / "encoder.json"), read_json(bundle / "model.json")
    check_codec(state)
    fingerprint = hashlib.sha256((case["source_sha256"] + case["outputs_sha256"]["partitions.parquet"]
                                  + case["outputs_sha256"]["protocol.json"]).encode("ascii")).hexdigest()
    ledger = contained(root, "artifacts/private/retail-holdout-access.sqlite")
    output = contained(root, "artifacts/private/retail-holdout-" + uuid.uuid4().hex[:12])
    # Claim before predictor/label queries. A failed evaluation cannot quietly reopen the cohort.
    claim_holdout(ledger, fingerprint, digest, output)
    output.mkdir(parents=True)
    provenance = {"schema_version": 1, "evaluation_id": output.name, "freeze_id": freeze_id,
                  "freeze_receipt_sha256": digest, "case_id": case["case_id"], "holdout_fingerprint": fingerprint,
                  "selected_model": frozen["selected_model"], "selected_variant": frozen["selected_variant"],
                  "method_source_sha256": sha256(Path(__file__)), "partition": "final_test",
                  "temporal_out_of_time": False, "model_training_performed": False,
                  "model_selection_performed": False, "qualified_for_production": False,
                  "visibility": "private", "public_release_approved": False}
    try:
        write_new(output / "access-start.json", {**provenance, "started_at": timestamp(),
                  "purpose": "one_time_frozen_random_cohort_evaluation", "codec_parity": "PASS_ALL_SOURCE_STATUS_PROBES"})
        with duckdb.connect() as db:
            db.read_parquet(str(case_folder / "clients.parquet")).create_view("clients")
            db.read_parquet(str(case_folder / "partitions.parquet")).create_view("partitions")
            columns = ",".join('c."' + n + '"' for n in NUMERIC_FEATURES + CATEGORICAL_FEATURES)
            rows = db.sql("SELECT c.source_client_id,c.target,p.partition," + columns +
                          " FROM clients c JOIN partitions p USING(source_client_id) WHERE p.partition='final_test' ORDER BY c.source_client_id").arrow().read_all().to_pylist()
        y = np.asarray([r["target"] for r in rows], dtype=np.int8)
        if (len({r["source_client_id"] for r in rows}) != len(rows)
                or any(type(r["target"]) is not int or r["target"] not in (0, 1) for r in rows)
                or {"positive": int(np.sum(y == 1)), "negative": int(np.sum(y == 0))} != case["support"]["final_test"]
                or min(np.sum(y == 1), np.sum(y == 0)) < 50):
            raise ValueError("Reserved holdout class support/identities differ from case")
        probabilities = predict_json(model, frozen_transform(state, rows))
        if frozen["selected_variant"] == "calibrated":
            calibration = read_json(bundle / "calibration.json")
            probabilities = expit(calibration["slope"] * logit(probabilities) + calibration["intercept"])
        result = metrics(y, probabilities)
        scores = [{"source_client_id": r["source_client_id"], "target": r["target"], "probability": float(p)}
                  for r, p in zip(rows, probabilities, strict=True)]
        pq.write_table(pa.Table.from_pylist(scores), output / "private-holdout-scores.parquet", compression="zstd")
        saved = pq.read_table(output / "private-holdout-scores.parquet").to_pylist()
        if saved != scores or metrics([r["target"] for r in saved], [r["probability"] for r in saved]) != result:
            raise ValueError("Persisted holdout scores/metrics failed reconciliation")
        write_new(output / "holdout-metrics.json", result)
        write_new(output / "verification.json", {"status": "PASS", "scored_rows": len(rows),
                  "metrics_recomputed_from_saved_scores": True, "refit_performed": False,
                  "caveats": ["Random cohort, not temporal out-of-time", "Selection rubric set after development inspection",
                              "Historical Taiwan credit-card payment target, not universal regulatory default",
                              "No holdout-based model substitution or threshold selection"]})
        if verify_freeze(root, freeze_id)[2] != digest:
            raise ValueError("Frozen bundle changed during holdout evaluation")
        write_new(output / "evaluation-complete.json", {**provenance, "status": "RETAIL_FROZEN_HOLDOUT_EVALUATED",
                  "completed_at": timestamp(), "final_test_scored": True,
                  "outputs_sha256": {p.name: sha256(p) for p in output.iterdir() if p.is_file()}})
        finish_claim(ledger, fingerprint, "completed")
        return {"directory": str(output), "status": "RETAIL_FROZEN_HOLDOUT_EVALUATED",
                "selected_model": frozen["selected_model"], "selected_variant": frozen["selected_variant"],
                "holdout_metrics": {k: v for k, v in result.items() if k != "reliability_bins"},
                "temporal_out_of_time": False, "qualified_for_production": False}
    except Exception as error:
        write_new(output / "evaluation-failed.json", {**provenance, "status": "FAIL", "failed_at": timestamp(),
                  "exception_type": type(error).__name__, "holdout_claim_consumed": True})
        finish_claim(ledger, fingerprint, "failed")
        raise
