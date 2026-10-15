"""Private technical profile. Never equates formatting success with model readiness."""
from __future__ import annotations
from pathlib import Path
import duckdb
from .contracts import fields_for

def profile(origination: Path, performance: Path, sql_dir: Path) -> dict:
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        db.read_parquet(str(origination)).create_view("origination")
        db.read_parquet(str(performance)).create_view("performance")
        integrity = db.execute((sql_dir / "profile_integrity.sql").read_text(encoding="utf-8"))
        summary = dict(zip([d[0] for d in integrity.description], integrity.fetchone()))
        db.execute("CREATE TEMP VIEW coverage AS " +
                   (sql_dir / "profile_coverage.sql").read_text(encoding="utf-8").rstrip(";\n"))
        row = db.execute("""SELECT
          COUNT(*) FILTER (WHERE gap_pairs>0),
          COUNT(*) FILTER (WHERE months_observed>=13 AND gap_pairs=0 AND duplicate_months=0),
          MIN(months_observed), MAX(months_observed)
          FROM coverage""").fetchone()
        summary.update(dict(zip(("loans_with_gaps", "loans_with_13_contiguous_observed_months",
                                 "min_observed_months", "max_observed_months"), row)))
        # Field completeness is separate from source sentinels and business applicability.
        missing = {}
        for table in ("origination", "performance"):
            columns = fields_for(table)
            counts = db.execute("SELECT " + ", ".join(
                f'COUNT(*) FILTER (WHERE TRIM("{column}")=\'\')' for column in columns)
                + " FROM " + table).fetchone()
            missing[table] = dict(zip(columns, counts))
        summary["orphan_performance_share"] = (
            summary["orphan_performance_rows"] / summary["performance_rows"]
            if summary["performance_rows"] else None)
        summary["no_performance_loan_share"] = (
            summary["loans_without_performance"] / summary["origination_rows"]
            if summary["origination_rows"] else None)
        return {"summary": summary, "blank_counts": missing,
                "coverage_note": "13 contiguous observations is a technical screen, not a validated 12m label",
                "event_note": "D3+ row counts are repeated monthly states, NOT incident defaults",
                "loss_note": "Populated loss rows do not certify usable loss labels or complete recoveries"}

def qualify(data_kind: str, ingestion: list[dict], result: dict) -> dict:
    summary = result["summary"]
    parse_ok = all(item["status"] == "PASS" for item in ingestion)
    integrity_ok = (summary["duplicate_origination_keys"] == 0
                    and summary["duplicate_monthly_keys"] == 0
                    and summary["orphan_performance_rows"] == 0)
    annual = data_kind == "annual_sample"
    monthly = summary["loans_with_13_contiguous_observed_months"] > 0
    source_ready = parse_ok and integrity_ok and annual and monthly
    gates = {
        "format_parse": "PASS" if parse_ok else "FAIL",
        "referential_integrity": "PASS" if integrity_ok else "FAIL",
        "research_sample_identity": "PASS_USER_ATTESTED" if annual else "BLOCKED_FORMAT_EXAMPLE_ONLY",
        "history_presence_screen": "PASS" if monthly else "FAIL",
        "source_qualification": "CANDIDATE_FOR_COHORT_REVIEW" if source_ready else "BLOCKED",
        "labels_and_temporal_splits": "NOT_IMPLEMENTED",
        "loss_model": "BLOCKED_PENDING_LABEL_AND_LOSS_AUDIT",
        "model_training": "BLOCKED",
        "public_real_data_release": "BLOCKED_PENDING_RIGHTS_REVIEW",
    }
    return {"gates": gates, "research_ready": False,
            "reason": ("Annual source passed initial screen; cohort, label, maturity, "
                       "multi-vintage and rights reviews remain." if source_ready else
                       "Formatting evidence is insufficient for research. Obtain an authorized "
                       "annual sample and resolve source integrity/coverage issues first.")}

