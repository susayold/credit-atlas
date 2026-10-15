"""Verified aggregate-only serving snapshot for the suite and retail benchmark."""
from __future__ import annotations

import re
import sqlite3
import uuid
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from .public_suite import verify_acquisition
from .retail_freeze import verify_freeze
from .retail_assessment import metrics
from .business_sba import verify_sba
from .workspace import contained, read_json, sha256, timestamp, write_new

ID = re.compile(r"suite-view-[0-9a-f]{12}\Z")
METHODS = ["suite_snapshot", "public_sources", "public_suite", "retail", "retail_features",
           "retail_assessment", "retail_comparison", "retail_freeze", "retail_holdout", "business_sba", "workspace"]
METRIC_FIELDS = ("loans", "events", "roc_auc", "average_precision", "brier_score", "log_loss", "reliability_bins")


def aggregate_metrics(value):
    return {key: value[key] for key in METRIC_FIELDS}


def business_projection(root, identifier, suite_id):
    folder, receipt, aggregates, digest = verify_sba(root, identifier)
    if receipt["suite_id"] != suite_id:
        raise ValueError("Business and suite acquisition lineage differ")
    quality = read_json(folder / "quality.json")
    return folder, {"business_id": identifier, "receipt_sha256": digest, "records": receipt["rows"],
        "aggregates": aggregates, "quality": quality, "contract": read_json(folder / "contract.json"),
        "dictionary": read_json(folder / "dictionary.json"),
        "fixed_horizon_default_target_qualified": False, "model_training_performed": False}


def business_report(snapshot, query):
    """Scope business aggregates explicitly; quality findings stay whole-source."""
    import copy
    business = snapshot.get("business")
    if business is None:
        raise ValueError("This verified snapshot has no business case")
    if set(query) - {"view_id", "program", "dimension", "bucket"}:
        raise ValueError("Unsupported business report filter")
    program, dimension, bucket = query.get("program", "all"), query.get("dimension", "program_status"), query.get("bucket", "all")
    if (program not in ("all", "7A", "504") or dimension not in business["aggregates"]["dimensions"]
            or not isinstance(bucket, str) or len(bucket) > 100):
        raise ValueError("Invalid business report scope")
    population = business["aggregates"]["dimensions"][dimension]
    if bucket != "all" and bucket not in {r["bucket"] for r in population}:
        raise ValueError("Business bucket is unavailable")
    selected = [r for r in population if (program == "all" or r["program"] == program) and (bucket == "all" or r["bucket"] == bucket)]
    return {"schema_version": 1, "view_id": snapshot["view_id"], "business_id": business["business_id"],
            "business_receipt_sha256": business["receipt_sha256"], "visibility": "private", "public_release_approved": False,
            "filters": {"program": program, "dimension": dimension, "bucket": bucket},
            "selected_record_count": sum(r["records"] for r in selected), "rows": copy.deepcopy(selected),
            "amount_scope": copy.deepcopy(business["aggregates"]["amount_scope"]),
            "quality_scope": "whole_source_all_six_segments_not_filtered_by_aggregate_controls",
            "quality": copy.deepcopy(business["quality"]), "contract": copy.deepcopy(business["contract"]),
            "limitations": copy.deepcopy(business["aggregates"]["limitations"]),
            "fixed_horizon_default_target_qualified": False, "model_training_performed": False}


def build_suite_view(root: Path, warehouse_id: str, freeze_id: str, holdout_id: str, business_id: str | None = None):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("Private D: workspace required")
    if not re.fullmatch(r"source-warehouse-[0-9a-f]{12}", warehouse_id) or not re.fullmatch(r"retail-holdout-[0-9a-f]{12}", holdout_id):
        raise ValueError("Valid warehouse and holdout identifiers required")
    warehouse_folder = contained(root, "artifacts/private/" + warehouse_id)
    warehouse = read_json(warehouse_folder / "warehouse-complete.json")
    if (warehouse.get("status") != "SOURCE_NATIVE_WAREHOUSE_COMPLETE" or warehouse.get("visibility") != "private"
            or warehouse.get("public_release_approved") is not False or warehouse.get("model_training_performed") is not False
            or warehouse.get("method_source_sha256") != sha256(Path(__file__).with_name("public_suite.py"))):
        raise ValueError("Warehouse contract changed")
    source_folder, acquisition = verify_acquisition(root, warehouse["suite_id"])
    if sha256(source_folder / "acquisition-complete.json") != warehouse["source_receipt_sha256"]:
        raise ValueError("Warehouse acquisition lineage changed")
    sources = {s["source_id"]: s for s in acquisition["sources"]}
    if len({t["source_id"] for t in warehouse["tables"]}) != len(warehouse["tables"]):
        raise ValueError("Duplicate warehouse source")
    for table in warehouse["tables"]:
        source = sources[table["source_id"]]
        path = contained(warehouse_folder, table["file"])
        if (sha256(path) != table["sha256"] or source["sha256"] != table["source_sha256"]
                or pq.read_metadata(path).num_rows != table["rows"] or table["rows"] != source["profile"]["rows"]):
            raise ValueError("Warehouse source/table evidence changed")
    bundle, frozen, freeze_digest, case_folder, case = verify_freeze(root, freeze_id)
    holdout_folder = contained(root, "artifacts/private/" + holdout_id)
    holdout = read_json(holdout_folder / "evaluation-complete.json")
    if (holdout.get("schema_version") != 1 or holdout.get("evaluation_id") != holdout_id
            or holdout.get("status") != "RETAIL_FROZEN_HOLDOUT_EVALUATED" or holdout.get("freeze_id") != freeze_id
            or holdout.get("freeze_receipt_sha256") != freeze_digest or holdout.get("case_id") != case["case_id"]
            or holdout.get("selected_model") != frozen["selected_model"] or holdout.get("selected_variant") != frozen["selected_variant"]
            or holdout.get("partition") != "final_test" or holdout.get("final_test_scored") is not True
            or holdout.get("visibility") != "private" or any(holdout.get(k) is not False for k in
                ("public_release_approved", "model_training_performed", "model_selection_performed", "qualified_for_production", "temporal_out_of_time"))
            or holdout.get("method_source_sha256") != sha256(Path(__file__).with_name("retail_holdout.py"))
            or set(holdout["outputs_sha256"]) != {"access-start.json", "private-holdout-scores.parquet", "holdout-metrics.json", "verification.json"}):
        raise ValueError("Frozen holdout lineage/contract changed")
    for name, digest in holdout["outputs_sha256"].items():
        if sha256(holdout_folder / name) != digest:
            raise ValueError("Holdout artifact changed")
    saved = pq.read_table(holdout_folder / "private-holdout-scores.parquet").to_pylist()
    # Read identities/labels only for saved-score lineage; never reopen predictors or rescore the holdout.
    with duckdb.connect() as db:
        db.read_parquet(str(case_folder / "clients.parquet")).create_view("clients")
        db.read_parquet(str(case_folder / "partitions.parquet")).create_view("partitions")
        identities = db.sql("SELECT c.source_client_id,c.target FROM clients c JOIN partitions p USING(source_client_id) WHERE p.partition='final_test' ORDER BY c.source_client_id").fetchall()
    if identities != [(r["source_client_id"], r["target"]) for r in saved]:
        raise ValueError("Holdout score identities/labels do not match reserved cohort")
    holdout_metrics = read_json(holdout_folder / "holdout-metrics.json")
    if metrics([r["target"] for r in saved], [r["probability"] for r in saved]) != holdout_metrics:
        raise ValueError("Holdout metric recomputation failed")
    with sqlite3.connect(contained(root, "artifacts/private/retail-holdout-access.sqlite")) as db:
        claim = db.execute("SELECT status,freeze_digest,output FROM evaluations WHERE fingerprint=?", (holdout["holdout_fingerprint"],)).fetchone()
    if claim != ("completed", freeze_digest, str(holdout_folder)):
        raise ValueError("Completed holdout access claim required")
    assessment_folder = contained(root, "artifacts/private/" + frozen["assessment_id"])
    comparison_folder = contained(root, "artifacts/private/" + frozen["comparison_id"])
    feature_folder = contained(root, "artifacts/private/" + frozen["feature_id"])
    validation = read_json(assessment_folder / "validation-metrics.json")
    comparison = read_json(comparison_folder / "comparison.json")
    modules = [
        {"id": "P1", "name": "Retail credit", "state": "behavioral_benchmark_evaluated", "supported": "Historical behavioral model, validation, frozen random holdout", "remaining": "Application-time data, intended use, fairness, decision policy, monitoring"},
        {"id": "P2", "name": "Mortgage & real estate", "state": "context_downloaded", "supported": "Mortgage macro context; D01 descriptive workspace accessible separately", "remaining": "Additional Freddie vintages require Clarity login; model qualification remains blocked"},
        {"id": "P3", "name": "Business credit", "state": "source_native_downloaded", "supported": "SBA snapshots, bankruptcy benchmark and source dictionary", "remaining": "Dictionary parsing, typed grain/target adapters, descriptive marts and models"},
        {"id": "P4", "name": "Portfolio & observatory", "state": "source_native_downloaded", "supported": "One FDIC bank quarter, failure/assistance records and unemployment context", "remaining": "Historical bank panel, metric definitions, exposure imports and peer analytics"},
        {"id": "P5", "name": "Structured & market", "state": "market_context_downloaded", "supported": "Treasury yields, mortgage rate and private corporate OAS context", "remaining": "Security/deal data, bond benchmark and scenario waterfall"}]
    for module in modules:
        selected = [s for s in acquisition["sources"] if module["id"] in s["modules"]]
        module["downloaded_files"] = sum(s["status"] == "DOWNLOADED_AND_PROFILED" for s in selected)
        module["model_qualified_for_production"] = False
    projection = {"schema_version": 1, "visibility": "private", "public_release_approved": False,
        "suite_id": warehouse["suite_id"], "warehouse_id": warehouse_id, "modules": modules,
        "downloaded_bytes": sum(s.get("bytes", 0) for s in acquisition["sources"]),
        "warehouse_tables": len(warehouse["tables"]), "warehouse_rows": sum(t["rows"] for t in warehouse["tables"]),
        "sources": [{k: s[k] for k in ("source_id", "modules", "status", "url", "metadata_url", "rights", "scope")} |
                    {"bytes": s.get("bytes"), "rows": s.get("profile", {}).get("rows"), "model_qualified": False} for s in acquisition["sources"]],
        "retail": {"case_id": case["case_id"], "freeze_id": freeze_id, "holdout_id": holdout_id,
                   "clients": case["clients"], "support": case["support"], "selected_model": frozen["selected_model"],
                   "selected_variant": frozen["selected_variant"], "target": case["target"],
                   "feature_dimension": read_json(bundle / "model.json")["feature_dimension"],
                   "selection": read_json(bundle / "selection.json"), "rubric": read_json(bundle / "rubric.json"),
                   "validation": [{"model": model, "variant": variant, **aggregate_metrics(value)}
                                  for model, variants in validation.items() for variant, value in variants.items()],
                   "holdout": aggregate_metrics(holdout_metrics), "paired_improvements": comparison["paired_improvements"],
                   "temporal_out_of_time": False, "qualified_for_production": False,
                   "limits": read_json(holdout_folder / "verification.json")["caveats"]}}
    folders = [source_folder, warehouse_folder, bundle, case_folder, assessment_folder, comparison_folder, feature_folder, holdout_folder]
    if business_id:
        business_folder, projection["business"] = business_projection(root, business_id, warehouse["suite_id"])
        folders.append(business_folder)
        modules[2].update(state="sba_descriptive_prepared", supported="SBA typed source records, four descriptive marts and quality review",
                          remaining="Polish/SEC adapters, model target/availability, issuer memo and business workflows")
    inputs = {}
    for folder in folders:
        for path in folder.iterdir():
            if path.is_file():
                inputs[str(path.relative_to(root))] = sha256(path)
    output = contained(root, "artifacts/private/suite-view-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    projection["view_id"] = output.name
    write_new(output / "snapshot.json", projection)
    # Recheck all captured input hashes to avoid publishing a mixed-input snapshot.
    if any(sha256(contained(root, name)) != digest for name, digest in inputs.items()):
        raise ValueError("Suite inputs changed while constructing projection")
    write_new(output / "view-complete.json", {"schema_version": 1, "view_id": output.name,
              "status": "SUITE_AGGREGATE_VIEW_VERIFIED", "completed_at": timestamp(),
              "visibility": "private", "public_release_approved": False, "inputs_sha256": inputs,
              "snapshot_sha256": sha256(output / "snapshot.json"),
              "method_sources_sha256": {n: sha256(Path(__file__).with_name(n + ".py")) for n in METHODS}})
    return {"directory": str(output), "status": "SUITE_AGGREGATE_VIEW_VERIFIED", "holdout_predictors_reopened": False}


class SuiteViews:
    """Validate once; invalidate cached projections when evidence changes."""
    def __init__(self, root):
        self.root = root.resolve()
        self.cache = {}

    def view(self, identifier):
        import copy
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            raise ValueError("Valid suite view identifier required")
        folder = contained(self.root, "artifacts/private/" + identifier)
        receipt_path = folder / "view-complete.json"
        receipt_digest = sha256(receipt_path)
        receipt = read_json(receipt_path)
        if (receipt.get("view_id") != identifier or receipt.get("schema_version") != 1
                or receipt.get("status") != "SUITE_AGGREGATE_VIEW_VERIFIED" or receipt.get("visibility") != "private"
                or receipt.get("public_release_approved") is not False or set(receipt["method_sources_sha256"]) != set(METHODS)):
            raise ValueError("Suite serving contract changed")
        for name, digest in receipt["method_sources_sha256"].items():
            if sha256(Path(__file__).with_name(name + ".py")) != digest:
                raise ValueError("Suite method changed; rebuild projection")
        if identifier in self.cache and self.cache[identifier]["receipt_digest"] != receipt_digest:
            raise ValueError("Suite completion receipt changed")
        snapshot_path = folder / "snapshot.json"
        if sha256(snapshot_path) != receipt["snapshot_sha256"]:
            raise ValueError("Suite aggregate snapshot changed")
        stats = {}
        for name, digest in receipt["inputs_sha256"].items():
            path = contained(self.root, name)
            stat = path.stat()
            stats[name] = (stat.st_size, stat.st_mtime_ns)
            if identifier in self.cache:
                if stats[name] != self.cache[identifier]["stats"][name]:
                    raise ValueError("Suite input evidence changed")
            if identifier not in self.cache or path.suffix == ".json":
                if sha256(path) != digest:
                    raise ValueError("Suite input hash changed")
        snapshot = read_json(snapshot_path)
        if snapshot.get("view_id") != identifier or snapshot.get("visibility") != "private" or snapshot.get("public_release_approved") is not False:
            raise ValueError("Suite aggregate privacy/identity changed")
        self.cache[identifier] = {"receipt_digest": receipt_digest, "stats": stats}
        return copy.deepcopy(snapshot)

    def catalog(self):
        records = []
        base = self.root / "artifacts/private"
        for folder in sorted(base.glob("suite-view-*")):
            if not ID.fullmatch(folder.name) or not (folder / "view-complete.json").is_file():
                continue
            try:
                view = self.view(folder.name)
                records.append({"view_id": folder.name, "status": "verified", "suite_id": view["suite_id"]})
            except (OSError, ValueError, KeyError, TypeError):
                records.append({"view_id": folder.name, "status": "evidence_unavailable_or_changed"})
        return {"views": records, "visibility": "private", "public_release_approved": False}
