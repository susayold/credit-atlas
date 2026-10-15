"""UCI credit-card behavioral benchmark: typed facts and frozen random partitions."""
from __future__ import annotations

import csv
import hashlib
import uuid
from collections import Counter
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

from .public_suite import verify_acquisition
from .workspace import contained, read_json, sha256, timestamp, write_new

FEATURE_NAMES = ["LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
                 "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"] + [
                 "BILL_AMT" + str(i) for i in range(1, 7)] + ["PAY_AMT" + str(i) for i in range(1, 7)]
DEMOGRAPHIC_EXCLUSIONS = ["SEX", "EDUCATION", "MARRIAGE", "AGE"]
CATEGORICAL_FEATURES = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
NUMERIC_FEATURES = ["LIMIT_BAL"] + ["BILL_AMT" + str(i) for i in range(1, 7)] + ["PAY_AMT" + str(i) for i in range(1, 7)]
PROTOCOL = {"version": "uci350-behavioral-random-benchmark-v1", "split_seed": "CreditAtlas-UCI350-v1",
            "method": "class_stratified_sha256_source_id_rank", "fractions": {
                "train": .60, "calibration": .15, "validation": .15, "final_test": .10},
            "target": "source_default_payment_next_month", "temporal_out_of_time": False,
            "feature_allowlist": {"numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES},
            "excluded_predictors": ["source_client_id", "target", *DEMOGRAPHIC_EXCLUSIONS],
            "final_test_predictors_materialized": False,
            "purpose": "historical Taiwan behavioral benchmark, not production underwriting"}


def canonical_rows(raw, metadata):
    expected = ["ID"] + ["X" + str(i) for i in range(1, 24)] + ["Y"]
    variables = metadata["data"]["variables"]
    descriptions = {item["name"]: item["description"] for item in variables if item["role"] == "Feature"}
    if (metadata["data"]["uci_id"] != 350 or descriptions != dict(zip(expected[1:-1], FEATURE_NAMES))
            or metadata["data"]["target_col"] != ["Y"]):
        raise ValueError("UCI350 feature/target metadata contract changed")
    rows, keys = [], set()
    with raw.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != expected:
            raise ValueError("Unexpected retail schema")
        for item in reader:
            if None in item or any(value is None for value in item.values()):
                raise ValueError("Malformed retail record")
            key, target = int(item["ID"]), int(item["Y"])
            if key <= 0 or key in keys or item["Y"] not in {"0", "1"}:
                raise ValueError("Retail key or target invalid")
            keys.add(key)
            row = {"source_client_id": key, "target": target}
            row.update({name: int(item["X" + str(i)]) for i, name in enumerate(FEATURE_NAMES, 1)})
            if (row["LIMIT_BAL"] <= 0 or not 18 <= row["AGE"] <= 120
                    or row["SEX"] not in {1, 2} or not 0 <= row["EDUCATION"] <= 6
                    or not 0 <= row["MARRIAGE"] <= 3
                    or any(not -2 <= row[name] <= 9 for name in CATEGORICAL_FEATURES)
                    or any(row["PAY_AMT" + str(i)] < 0 for i in range(1, 7))):
                raise ValueError("Retail source value outside reviewed domain")
            # Negative statements are retained as signed balances, not clipped.
            rows.append(row)
    if not rows:
        raise ValueError("Empty retail source")
    return rows


def assign_partitions(rows):
    if any(type(row.get("source_client_id")) is not int or row["source_client_id"] <= 0
           or type(row.get("target")) is not int or row["target"] not in (0, 1) for row in rows):
        raise ValueError("Valid private client keys and binary labels required")
    if len({row["source_client_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate retail source keys")
    assignments = []
    for target in (0, 1):
        members = [row for row in rows if row["target"] == target]
        ranked = sorted(members, key=lambda row: hashlib.sha256(
            (PROTOCOL["split_seed"] + ":" + str(row["source_client_id"])).encode()).hexdigest())
        n = len(ranked)
        ends = [int(n * .60), int(n * .75), int(n * .90), n]
        start = 0
        for role, end in zip(PROTOCOL["fractions"], ends, strict=True):
            assignments.extend({"source_client_id": row["source_client_id"], "partition": role,
                                "target": target} for row in ranked[start:end])
            start = end
    return sorted(assignments, key=lambda row: row["source_client_id"])


def build_retail(root: Path, suite_id: str):
    root = root.resolve()
    source_folder, acquisition = verify_acquisition(root, suite_id)
    by_id = {item["source_id"]: item for item in acquisition["sources"]}
    if any(by_id[name]["status"] != "DOWNLOADED_AND_PROFILED" for name in ("uci-retail", "uci-retail-metadata")):
        raise ValueError("Both UCI350 payload and metadata required")
    digest = sha256(source_folder / "acquisition-complete.json")
    raw = source_folder / by_id["uci-retail"]["file"]
    metadata_file = source_folder / by_id["uci-retail-metadata"]["file"]
    rows = canonical_rows(raw, read_json(metadata_file))
    counts = Counter(str(row["target"]) for row in rows)
    if (len(rows) != by_id["uci-retail"]["profile"]["rows"]
            or dict(counts) != by_id["uci-retail"]["profile"]["target_counts"]):
        raise ValueError("Canonical source population does not reconcile")
    assignments = assign_partitions(rows)
    output = contained(root, "artifacts/private/retail-case-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output / "run-start.json", {"started_at": timestamp(), "suite_id": suite_id,
              "source_receipt_sha256": digest, "intent": "canonical_retail_and_frozen_benchmark_partitions"})
    try:
        schema = pa.schema([("source_client_id", pa.int32()), ("target", pa.int8())] + [
                           (name, pa.int64()) for name in FEATURE_NAMES])
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), output / "clients.parquet", compression="zstd")
        history = [{"source_client_id": row["source_client_id"], "reference_month": date(2005, 9-index, 1),
                    "source_payment_status_code": row[CATEGORICAL_FEATURES[index]],
                    "statement_balance_ntd": row["BILL_AMT" + str(index+1)],
                    "previous_payment_ntd": row["PAY_AMT" + str(index+1)]}
                   for row in rows for index in range(6)]
        pq.write_table(pa.Table.from_pylist(history), output / "six_month_history.parquet", compression="zstd")
        pq.write_table(pa.Table.from_pylist(assignments), output / "partitions.parquet", compression="zstd")
        write_new(output / "protocol.json", PROTOCOL)
        support = {role: {"positive": sum(a["target"] for a in assignments if a["partition"] == role),
                          "negative": sum(1-a["target"] for a in assignments if a["partition"] == role)}
                   for role in PROTOCOL["fractions"]}
        quality = {"clients": len(rows), "history_rows": len(history), "target_counts": dict(counts),
                   "support": support, "currency": "TWD/NT dollars from source", "primary_key_unique": True,
                   "negative_statement_values_retained": sum(row["BILL_AMT" + str(i)] < 0 for row in rows for i in range(1, 7)),
                   "source_category_counts": {name: dict(Counter(str(row[name]) for row in rows))
                                              for name in DEMOGRAPHIC_EXCLUSIONS + CATEGORICAL_FEATURES},
                   "warnings": ["PAY status -2 and 0 occur but their meanings are not fully defined by the source description; preserve distinct categories.",
                                "Education codes 0/5/6 and marriage code 0 occur beyond the source's simplified dictionary; retained, excluded from predictors.",
                                "No within-cohort calendar variation supports out-of-time evaluation.",
                                "Six history months are repeated observations of the same client, not independent labelled samples.",
                                "Default label is source-defined next-month payment default, not a validated regulatory default definition.",
                                "Canonical facts retain source IDs privately; identifiers and demographic fields are excluded from the prediction allowlist.",
                                "Source reference months do not establish historical publication availability."]}
        write_new(output / "quality.json", quality)
        # Independent SQL casts and six explicit source-month selections check
        # every typed value, not only totals produced by the Python adapter.
        with duckdb.connect() as db:
            db.read_csv(str(raw), header=True, all_varchar=True).create_view("raw_source")
            casts = ["CAST(ID AS INTEGER) AS source_client_id", "CAST(Y AS TINYINT) AS target"] + [
                'CAST(X' + str(i) + ' AS BIGINT) AS "' + name + '"'
                for i, name in enumerate(FEATURE_NAMES, 1)]
            db.sql("SELECT " + ",".join(casts) + " FROM raw_source").create_view("source_clients")
            db.read_parquet(str(output / "clients.parquet")).create_view("saved_clients")
            history_queries = ["SELECT source_client_id, DATE '2005-" + str(9-i).zfill(2) +
                "-01' AS reference_month, " + CATEGORICAL_FEATURES[i] +
                " AS source_payment_status_code, BILL_AMT" + str(i+1) +
                " AS statement_balance_ntd, PAY_AMT" + str(i+1) + " AS previous_payment_ntd FROM source_clients"
                for i in range(6)]
            db.sql(" UNION ALL ".join(history_queries)).create_view("source_history")
            db.read_parquet(str(output / "six_month_history.parquet")).create_view("saved_history")
            differences = {}
            for name in ("clients", "history"):
                differences[name] = db.sql("SELECT count(*) FROM ((SELECT * FROM source_" + name +
                    " EXCEPT ALL SELECT * FROM saved_" + name + ") UNION ALL (SELECT * FROM saved_" +
                    name + " EXCEPT ALL SELECT * FROM source_" + name + "))").fetchone()[0]
            if any(differences.values()):
                raise ValueError("Typed retail values do not reconcile independently to raw source")
        write_new(output / "reconciliation.json", {"status": "PASS", "method": "bidirectional_full_row_SQL_except_all",
                  "source_clients": len(rows), "source_history_rows": len(history), "differing_rows": differences})
        verify_acquisition(root, suite_id)
        if sha256(source_folder / "acquisition-complete.json") != digest:
            raise ValueError("Acquisition changed during canonical build")
        receipt = {"schema_version": 1, "case_id": output.name, "status": "RETAIL_CANONICAL_BENCHMARK_PREPARED",
                   "completed_at": timestamp(), "suite_id": suite_id, "source_receipt_sha256": digest,
                   "source_sha256": by_id["uci-retail"]["sha256"], "metadata_sha256": by_id["uci-retail-metadata"]["sha256"],
                   "method_source_sha256": sha256(Path(__file__)), "clients": len(rows), "history_rows": len(history),
                   "support": support, "target": PROTOCOL["target"], "temporal_out_of_time": False,
                   "model_training_performed": False, "model_qualified_for_production": False,
                   "final_test_predictors_materialized": False, "final_test_scored": False,
                   "visibility": "private", "public_release_approved": False,
                   "outputs_sha256": {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
        write_new(output / "case-complete.json", receipt)
        return {"directory": str(output), "status": receipt["status"], "clients": len(rows),
                "history_rows": len(history), "support": support, "model_training_performed": False}
    except Exception as error:
        write_new(output / "run-failed.json", {"status": "FAIL", "failed_at": timestamp(),
                  "exception_type": type(error).__name__, "model_training_performed": False})
        raise
