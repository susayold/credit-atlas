"""Verified domain artifacts -> one private CreditAtlas evidence contract.

Risk definitions/calculations remain in the pinned crsl engine. This adapter
projects its verified outputs and adds traceable application views.
"""
from __future__ import annotations

import datetime as dt
import decimal
import hashlib
import json
import secrets
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .workspace import contained, engine_root, load_engine, read_json, sha256, timestamp, write_new

TARGET = {
    "version": "d01-early-entry-d3-before-prepay-12m-v1",
    "name": "First-observed early-entry D3 before prepaid/matured, 12 months",
    "horizon_months": 12, "landmark": "first_observed_month",
    "event": "numeric_delinquency_03_through_99",
    "prepayment_estimand": "event_before_prepayment",
    "censored_means": "unavailable_not_negative",
    "probability_kind": "D3_event_risk_not_regulatory_default_PD",
    "source_claim": "retrospective_latest_release_not_strict_historical_PIT",
}


def serial(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def json_ready(value):
    return json.loads(json.dumps(value, default=serial, ensure_ascii=False, allow_nan=False))


def rows(db, query, parameters=None):
    result = db.execute(query, parameters or [])
    names = [item[0] for item in result.description]
    return [dict(zip(names, row)) for row in result.fetchall()]


def segment_expr(alias="d"):
    return (f"CASE WHEN {alias}.is_relief_refinance THEN 'relief' "
            f"WHEN {alias}.is_relief_refinance IS FALSE THEN 'non_relief' ELSE 'unknown' END")


def verified_pipeline(root: Path, foundation: dict):
    from crsl.pipeline import STAGES
    vendor = engine_root(root)
    pipeline = contained(root, foundation["pipeline_run"])
    if sha256(pipeline / "run-complete.json") != foundation["pipeline_manifest_sha256"]:
        raise ValueError("Foundation pipeline receipt changed")
    manifest = read_json(pipeline / "run-complete.json")
    if (manifest.get("status") != "DEVELOPMENT_PIPELINE_COMPLETE" or
            [r["stage"] for r in manifest["stages"]] != [r[0] for r in STAGES] or
            any(r["status"] != "PASS" for r in manifest["stages"])):
        raise ValueError("Complete eight-stage foundation is required")
    base = vendor / "artifacts/private"
    stages = {}
    inputs = []

    def verify(path, expected):
        if sha256(path) != expected:
            raise ValueError(f"Changed evidence: {path.name}")
        inputs.append({"path": str(path.relative_to(root)), "sha256": expected})

    for stage in manifest["stages"]:
        path = contained(base, stage["output_run"])
        if path.parent != base.resolve():
            raise ValueError("Invalid stage directory")
        stages[stage["stage"]] = path
        receipt_path = path / "run-complete.json"
        if receipt_path.exists():
            receipt = read_json(receipt_path)
            verify(receipt_path, sha256(receipt_path))
            for name, expected in receipt.get("outputs_sha256", {}).items():
                file = contained(path, name)
                if file.parent != path:
                    raise ValueError("Invalid output filename")
                verify(file, expected)
        if stage["stage"] == "vintage":
            verify(path / "run-complete.json", stage["output_manifest_sha256"])
            verify(path / "verification.json", stage["verification_sha256"])
            if read_json(path / "verification.json").get("status") != "PASS":
                raise ValueError("Vintage independent checks are required")
    source = contained(root, foundation["source_run"])
    verify(source / "run-complete.json", foundation["source_manifest_sha256"])
    canonical = read_json(stages["canonical"] / "run-complete.json")
    for name, expected in canonical["staging_sha256"].items():
        verify(source / name / "staging.parquet", expected)
    metrics = read_json(stages["metrics"] / "validation.json")
    if metrics.get("status") != "PASS":
        raise ValueError("Portfolio metrics did not pass verification")
    verify(stages["portfolio"] / "monthly.parquet", metrics["monthly_sha256"])
    for path in [source / "result.json", stages["labels"] / "summary.json",
                 stages["portfolio"] / "summary.json", stages["metrics"] / "validation.json",
                 stages["metrics"] / "registry.json"]:
        verify(path, sha256(path))
    return pipeline, stages, source, inputs


def build_case(root: Path, case_dir: Path) -> dict:
    root, case_dir = root.resolve(), case_dir.resolve()
    if not case_dir.is_relative_to(root / "artifacts/private"):
        raise ValueError("Case must belong to this private workspace")
    if (case_dir / "case-complete.json").exists():
        raise FileExistsError("Completed cases are immutable; build a new case")
    upstream = load_engine(root)
    from crsl.evidence_checks import require_outcome_totals
    from crsl.losses import summarize as summarize_losses
    from crsl.portfolio_profile_export import load as load_profile
    from crsl.segmented_transition_export import load as load_segmented
    from crsl.vintage_export import load as load_vintage
    from crsl.reporting.export import build as build_report

    foundation = read_json(case_dir / "foundation-complete.json")
    if (foundation.get("status") != "D01_FOUNDATION_REBUILT" or
            foundation["engine_commit"] != upstream["commit"]):
        raise ValueError("Pinned rebuilt foundation is required")
    pipeline, stages, source, inputs = verified_pipeline(root, foundation)
    vendor = engine_root(root)
    source_profile = read_json(source / "result.json")
    label_summary = read_json(stages["labels"] / "summary.json")
    split = read_json(stages["splits"] / "audit.json")
    segmented = contained(root, foundation["segmented_run"])
    profile = contained(root, foundation["profile_run"])
    for directory, key in [(segmented, "segmented"), (profile, "profile")]:
        if sha256(directory / "run-complete.json") != foundation[key + "_manifest_sha256"]:
            raise ValueError("Extension receipt changed")
        receipt = read_json(directory / "run-complete.json")
        if receipt["canonical_run"] != stages["canonical"].name:
            raise ValueError("Extension is from a different canonical run")
        for filename, expected in receipt["outputs_sha256"].items():
            path = contained(directory, filename)
            if sha256(path) != expected:
                raise ValueError("Extension artifact changed")
            inputs.append({"path": str(path.relative_to(root)), "sha256": expected})
        inputs.append({"path": str((directory / "run-complete.json").relative_to(root)),
                       "sha256": sha256(directory / "run-complete.json")})

    snapshot = {"visibility": "private", "public_release_approved": False,
                "pipeline_run": pipeline.name,
                "loans": source_profile["summary"]["origination_loans"],
                "monthly_rows": source_profile["summary"]["performance_rows"]}
    secret = secrets.token_bytes(32)
    loan_index = []
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        db.execute("SET threads=2")
        for name in ("dim_loan", "fact_loan_month"):
            db.read_parquet(str(stages["canonical"] / (name + ".parquet"))).create_view(name)
        for view, stage, filename in [("labels", "labels", "labels.parquet"),
                                      ("monthly", "portfolio", "monthly.parquet"),
                                      ("transitions", "portfolio", "transition_matrix.parquet"),
                                      ("loss_audit", "audit", "loss_audit.parquet"),
                                      ("episodes", "portfolio", "episodes.parquet")]:
            db.read_parquet(str(stages[stage] / filename)).create_view(view)
        snapshot["outcomes"] = rows(db, "SELECT outcome,COUNT(*) AS loans FROM labels GROUP BY 1 ORDER BY 1")
        if snapshot["outcomes"] != [{"outcome": r["outcome"], "loans": r["loans"]} for r in label_summary["outcomes"]]:
            raise ValueError("Label summary does not match saved Parquet")
        require_outcome_totals(snapshot["outcomes"], snapshot["loans"])
        snapshot["monthly"] = rows(db, "SELECT * FROM monthly ORDER BY period")
        snapshot["transitions"] = rows(db, "SELECT * FROM transitions ORDER BY origin,destination")
        snapshot["loss_summary"] = summarize_losses(rows(db, "SELECT * FROM loss_audit ORDER BY loan_id,period"))
        snapshot["loss_reported"] = snapshot["loss_summary"]["reported_loss_loans"]
        snapshot["months"] = len(snapshot["monthly"])
        years = [r[0] for r in db.execute("SELECT DISTINCT origination_year FROM dim_loan ORDER BY 1").fetchall()]
        coverage = rows(db, "SELECT " + ",".join(
            f"COUNT(*) FILTER(WHERE {name} IS NULL) AS {name}" for name in
            ["classic_fico", "original_dti", "original_ltv", "original_cltv", "vantagescore", "property_valuation_method"]) + " FROM dim_loan")[0]
        observed_support = rows(db, f"""SELECT {segment_expr('l')} AS segment,
            COUNT(*) AS source_loans, COUNT(*) FILTER(WHERE eligibility_reason='eligible') AS eligible_loans,
            COUNT(*) FILTER(WHERE target=1) AS positive,
            COUNT(*) FILTER(WHERE target=0) AS negative,
            COUNT(*) FILTER(WHERE target IS NULL) AS unavailable
            FROM labels l GROUP BY 1 ORDER BY 1""")
        segment_outcomes = rows(db, f"SELECT {segment_expr('l')} AS segment,outcome,COUNT(*) AS loans FROM labels l GROUP BY 1,2 ORDER BY 1,2")
        episode_counts = rows(db, f"SELECT {segment_expr()} AS segment,event_type,COUNT(*) AS events,COUNT(DISTINCT e.loan_id) AS distinct_loans FROM episodes e JOIN dim_loan d USING(loan_id) GROUP BY 1,2 ORDER BY 1,2")
        monthly_by_segment = {}
        for segment in [r["segment"] for r in observed_support]:
            if segment not in {"relief", "non_relief", "unknown"}:
                raise ValueError("Unknown canonical segment")
            db.sql(f"SELECT f.* FROM fact_loan_month f JOIN dim_loan d USING(loan_id) WHERE {segment_expr()}='{segment}'").create_view("segment_months", replace=True)
            sql = (vendor / "sql/portfolio_monthly.sql").read_text(encoding="utf-8").replace("FROM fact_loan_month", "FROM segment_months")
            monthly_by_segment[segment] = rows(db, sql)
        private_rows = rows(db, f"""SELECT d.loan_id,d.origination_year,{segment_expr()} AS segment,
            d.classic_fico,d.original_ltv,l.outcome,l.target
            FROM dim_loan d JOIN labels l USING(loan_id) ORDER BY d.loan_id""")
        for row in private_rows:
            token = hashlib.sha256(secret + row["loan_id"].encode()).hexdigest()[:24]
            loan_index.append({"loan_key": token, **row})
    if len({r["loan_key"] for r in loan_index}) != snapshot["loans"]:
        raise ValueError("Private loan keys must be unique")
    pq.write_table(pa.Table.from_pylist(loan_index), case_dir / "loan-index.parquet", compression="zstd")
    snapshot["vintage_evidence"] = load_vintage(vendor, stages["canonical"], stages["vintage"])
    snapshot["segmented_transitions"] = load_segmented(vendor, segmented)
    snapshot["portfolio_profile"] = load_profile(vendor, stages["canonical"], profile)
    snapshot = json_ready(snapshot)
    report = build_report(snapshot)
    model_readiness = {"status": "qualified_for_fit" if split["training_ready"] else "not_qualified",
                       "actual_model_fit": False, "support": split["support"],
                       "missing_years": split["missing_years"], "blocking_reasons": split["blocking_reasons"],
                       "exclusions": split["excluded"], "target": TARGET}
    payload = json_ready({"schema_version": 1, "module_id": "P2", "case_id": case_dir.name,
              "name": "Residential Mortgage Lifecycle & Loss Lab", "visibility": "private",
              "public_release_approved": False, "engine_commit": upstream["commit"],
              "pipeline_run": pipeline.name, "source_release": 47, "source_years": years,
              "source_url": "https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset",
              "target": TARGET, "snapshot": snapshot, "model_readiness": model_readiness,
              "source_quality": {"technical_profile": source_profile["summary"],
                                 "canonical_missing_counts": coverage, "source_blank_counts": {
                                     table: {field: count for field, count in values.items() if field != "loan_id"}
                                     for table, values in source_profile["blank_counts"].items()}},
              "observed_support": observed_support, "segment_outcomes": segment_outcomes,
              "monthly_by_segment": monthly_by_segment, "episode_counts": episode_counts,
              "episode_notes": read_json(stages["portfolio"] / "summary.json"),
              "metric_registry": report["metric_registry"],
              "definitions": {"stock": "Active sample loan states at each reporting month; not incidence.",
                  "transitions": "Adjacent observed loan-month pairs; count or opening-principal denominator.",
                  "cure": "Sustained cure is confirmed only on the third consecutive nonterminal current month.",
                  "loss": "Observed terminal-loan signed component bridge; unresolved is not zero.",
                  "vintage": "Origination year; first observed reporting month defines entry.",
                  "sample": "One authorized annual sample; not the full lender or market population."},
              "limitations": ["Retrospective latest-release research; not strict historical public point-in-time data.",
                  "No completed multi-vintage model validation, lender approval policy or accounting ECL.",
                  "Private source and derived-data rights remain attached to this case."]})
    from crsl.reporting.export import _assert_safe
    _assert_safe(payload)
    write_new(case_dir / "snapshot.json", payload)
    write_new(case_dir / "report.json", report)
    complete = {"status": "D01_DESCRIPTIVE_COMPLETE", "completed_at": timestamp(),
                "case_id": case_dir.name, "pipeline_run": pipeline.name,
                "source_years": years, "engine_commit": upstream["commit"],
                "raw_sha256": foundation["raw_sha256"], "visibility": "private",
                "public_release_approved": False, "actual_model_fit": False,
                "descriptive_source_rebuilt": True, "target_version": TARGET["version"],
                "verified_inputs": inputs,
                "canonical_run": str(stages["canonical"].relative_to(root)),
                "label_run": str(stages["labels"].relative_to(root)),
                "portfolio_run": str(stages["portfolio"].relative_to(root)),
                "outputs_sha256": {name: sha256(case_dir / name) for name in
                                   ["snapshot.json", "report.json", "loan-index.parquet", "foundation-complete.json"]}}
    write_new(case_dir / "case-complete.json", complete)
    return {"case_id": case_dir.name, "loans": snapshot["loans"],
            "loan_months": snapshot["monthly_rows"], "descriptive_status": "verified_rebuild",
            "research_model_status": model_readiness["status"], "visibility": "private"}
