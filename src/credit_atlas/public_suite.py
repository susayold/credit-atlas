"""Reproducible source-native warehouse; qualification remains source-specific."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .public_sources import catalog
from .workspace import contained, read_json, sha256, timestamp, write_new

SUITE_ID = re.compile(r"suite-[0-9a-f]{12}\Z")


def verify_acquisition(root, suite_id):
    if not isinstance(suite_id, str) or not SUITE_ID.fullmatch(suite_id):
        raise ValueError("Invalid suite acquisition ID")
    folder = contained(root, "data/private/public-suite/" + suite_id)
    receipt = read_json(folder / "acquisition-complete.json")
    expected = {source["source_id"]: source for source in catalog()}
    if (receipt.get("schema_version") != 1 or receipt.get("visibility") != "private"
            or receipt.get("public_release_approved") is not False
            or receipt.get("model_training_performed") is not False
            or len(receipt["sources"]) != len(expected)
            or {source["source_id"] for source in receipt["sources"]} != set(expected)):
        raise ValueError("Acquisition receipt contract changed")
    failed = [source["source_id"] for source in receipt["sources"] if source["status"] == "FAILED"]
    if (receipt.get("status") != ("PARTIAL" if failed else "COMPLETE")
            or receipt.get("failed_sources") != failed):
        raise ValueError("Batch completeness status does not reconcile")
    for source in receipt["sources"]:
        spec = expected[source["source_id"]]
        if any(source.get(key) != value for key, value in spec.items()):
            raise ValueError("Official acquisition source contract changed")
        if read_json(folder / (source["source_id"] + "-receipt.json")) != source:
            raise ValueError("Per-source receipt differs from batch")
        if source.get("model_qualified") is not False or source.get("public_release_approved") is not False:
            raise ValueError("Source qualification or visibility changed")
        if source["status"] == "FAILED":
            continue
        if source["status"] != "DOWNLOADED_AND_PROFILED":
            raise ValueError("Unknown acquisition state")
        name = source["source_id"] + "." + source["kind"]
        if source.get("file") != name or source.get("model_qualified") is not False:
            raise ValueError("Source filename or qualification changed")
        path = contained(root, str((folder / name).relative_to(root)))
        if path.stat().st_size != source["bytes"] or sha256(path) != source["sha256"]:
            raise ValueError("Raw source content changed")
    return folder, receipt


def build_source_warehouse(root: Path, suite_id: str):
    root = root.resolve()
    source_folder, acquisition = verify_acquisition(root, suite_id)
    output = contained(root, "artifacts/private/source-warehouse-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    source_digest = sha256(source_folder / "acquisition-complete.json")
    write_new(output / "run-start.json", {"started_at": timestamp(), "suite_id": suite_id,
              "source_receipt_sha256": source_digest})
    tables = []
    try:
        with duckdb.connect() as db:
            db.execute("SET memory_limit='768MB'")
            db.execute("SET threads=2")
            db.execute("SET temp_directory=?", [str(output / "duckdb-temp")])
            for source in acquisition["sources"]:
                if source["status"] != "DOWNLOADED_AND_PROFILED" or source["kind"] == "xlsx":
                    continue
                source_id = source["source_id"]
                raw = source_folder / source["file"]
                target = output / (source_id + ".parquet")
                if source["kind"] == "csv":
                    # Source-native strings preserve sentinels, codes and date formats
                    # until a reviewed source-specific typed adapter is available.
                    relation = db.sql("SELECT * FROM read_csv(?, header=true, all_varchar=true, "
                                      "strict_mode=true, nullstr=?, sample_size=-1)",
                                      params=[str(raw), "__NO_NATIVE_NULL_" + output.name + "__"])
                    relation.to_parquet(str(target), compression="zstd")
                    null_fields = " OR ".join('"' + name.replace('"', '""') + '" IS NULL'
                                               for name in source["profile"]["fields"])
                    if db.sql("SELECT count(*) FROM read_parquet(?) WHERE " + null_fields,
                              params=[str(target)]).fetchone()[0]:
                        raise ValueError("Native CSV sentinel must not become SQL null")
                elif source_id.startswith("fdic-"):
                    records = [item["data"] for item in read_json(raw)["data"]]
                    pq.write_table(pa.Table.from_pylist(records), target, compression="zstd")
                else:
                    continue
                metadata = pq.read_metadata(target)
                if metadata.num_rows != source["profile"]["rows"]:
                    raise ValueError("Source-native row count does not reconcile")
                tables.append({"source_id": source_id, "modules": source["modules"],
                               "file": target.name, "sha256": sha256(target), "rows": metadata.num_rows,
                               "columns": metadata.num_columns, "source_sha256": source["sha256"],
                               "grain_and_semantics": source["scope"], "typed_feature_qualified": False})
                print(source_id + ": source-native Parquet verified", flush=True)
        verify_acquisition(root, suite_id)
        if sha256(source_folder / "acquisition-complete.json") != source_digest:
            raise ValueError("Acquisition changed during warehouse build")
        write_new(output / "warehouse-complete.json", {
            "schema_version": 1, "status": "SOURCE_NATIVE_WAREHOUSE_COMPLETE", "completed_at": timestamp(),
            "suite_id": suite_id, "source_receipt_sha256": source_digest,
            "method_source_sha256": sha256(Path(__file__)), "tables": tables,
            "skipped_sources": [x["source_id"] for x in acquisition["sources"] if x["status"] != "DOWNLOADED_AND_PROFILED"],
            "visibility": "private", "public_release_approved": False, "model_training_performed": False,
            "limitations": ["Source-native storage is not typed canonical/model qualification.",
                            "No cross-source borrower/entity identity joins.",
                            "Latest source snapshots are not historical publication archives.",
                            "Dictionary and source metadata remain original evidence, not warehouse facts."]})
        return {"directory": str(output), "status": "SOURCE_NATIVE_WAREHOUSE_COMPLETE",
                "tables": len(tables), "model_training_performed": False}
    except Exception as error:
        write_new(output / "run-failed.json", {"status": "FAIL", "exception_type": type(error).__name__,
                  "failed_at": timestamp(), "model_training_performed": False})
        raise
