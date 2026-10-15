"""Bounded-memory ZIP-to-Parquet staging, with immutable attempts and failures."""
from __future__ import annotations
import io
import json
import time
import zipfile
from collections import Counter
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from .contracts import fields_for, validate_row

def stage_member(archive_path: Path, member: str, table: str,
                 destination: Path, batch_size: int = 10000,
                 *, format_example: bool = False) -> dict:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    destination.mkdir(parents=True, exist_ok=False)
    path = destination / "staging.parquet"
    schema = pa.schema([(name, pa.string()) for name in fields_for(table)]
                       + [("_source_line", pa.int64())])
    total, accepted, rejected, batch, error_counts = 0, 0, 0, [], Counter()
    started = time.perf_counter()
    # No invalid record text or real IDs printed. Original archive is immutable.
    with zipfile.ZipFile(archive_path) as archive, archive.open(member) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", errors="strict", newline="") as text:
            with pq.ParquetWriter(path, schema, compression="zstd") as writer:
                with (destination / "quarantine.jsonl").open("x", encoding="utf-8") as quarantine:
                    for total, line in enumerate(text, 1):
                        values = line.rstrip("\r\n").split("|")
                        errors = validate_row(values, table, format_example=format_example)
                        if errors:
                            rejected += 1
                            error_counts.update(errors)
                            quarantine.write(json.dumps({"line": total, "errors": errors}) + "\n")
                            continue
                        accepted += 1
                        record = dict(zip(fields_for(table), values))
                        record["_source_line"] = total
                        batch.append(record)
                        if len(batch) >= batch_size:
                            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                            batch.clear()
                    if batch:
                        writer.write_table(pa.Table.from_pylist(batch, schema=schema))
    return {
        "table": table, "source_member": member, "rows": total, "accepted": accepted,
        "rejected": rejected, "error_counts": dict(sorted(error_counts.items())),
        "reconciliation_pass": total == accepted + rejected,
        "status": "PASS" if total > 0 and rejected == 0 else "FAIL",
        "seconds": round(time.perf_counter() - started, 4),
        "batch_size": batch_size, "staging_file": str(path),
        "format_example_id_exception_enabled": format_example,
        "note": "Staging strings preserved; no canonical normalization/labels performed"}
