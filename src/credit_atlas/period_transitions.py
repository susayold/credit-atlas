"""Reporting-year matrices from the pinned adjacent-pair definition."""
from __future__ import annotations

import tempfile

import duckdb

from .snapshot import json_ready, rows
from .workspace import contained, engine_root

VERSION = "d01-opening-reporting-year-transitions-v1"


def aggregate(db, sql_dir):
    """Filter only after LEAD; December -> January belongs to December's year."""
    if db.execute("SELECT COUNT(*)-COUNT(DISTINCT loan_id) FROM dim_loan").fetchone()[0]:
        raise ValueError("Duplicate dimension loan keys")
    if db.execute("""SELECT COUNT(*) FROM fact_loan_month f
                     ANTI JOIN dim_loan d USING(loan_id)""").fetchone()[0]:
        raise ValueError("Missing dimension loan keys")
    if db.execute("""SELECT COUNT(*) FROM (
        SELECT loan_id,period FROM fact_loan_month GROUP BY ALL HAVING COUNT(*)>1
    )""").fetchone()[0]:
        raise ValueError("Monthly grain must be unique")
    db.execute("CREATE TEMP VIEW period_pairs AS " + (sql_dir / "transitions.sql").read_text())
    db.execute("""CREATE TEMP TABLE period_cells AS
        WITH paired AS (
            SELECT YEAR(p.period)::INTEGER AS reporting_year,
                CASE WHEN d.is_relief_refinance THEN 'relief'
                     WHEN d.is_relief_refinance IS FALSE THEN 'non_relief'
                     ELSE 'unknown' END AS segment,
                p.delinquency_state AS origin,p.destination,p.loan_id,p.current_upb
            FROM period_pairs p JOIN dim_loan d USING(loan_id) WHERE p.adjacent
        ), grouped AS (
            SELECT reporting_year,COALESCE(segment,'all') AS segment,origin,destination,
                COUNT(*) AS pairs,COUNT(DISTINCT loan_id) AS distinct_loans,
                SUM(current_upb) AS opening_upb,
                COUNT(*) FILTER(WHERE current_upb IS NULL) AS missing_balance_pairs
            FROM paired GROUP BY GROUPING SETS (
                (reporting_year,segment,origin,destination),
                (segment,origin,destination),
                (reporting_year,origin,destination),
                (origin,destination))
        )
        SELECT *,SUM(pairs) OVER(PARTITION BY reporting_year,segment,origin) AS origin_pairs,
            SUM(opening_upb) OVER(PARTITION BY reporting_year,segment,origin) AS origin_opening_upb,
            pairs / SUM(pairs) OVER(PARTITION BY reporting_year,segment,origin)::DOUBLE AS count_probability,
            opening_upb / NULLIF(SUM(opening_upb) OVER(PARTITION BY reporting_year,segment,origin),0)::DOUBLE AS balance_probability,
            distinct_loans < 30 AS sparse_cell
        FROM grouped""")
    bad = db.execute("""SELECT COUNT(*) FROM (
        SELECT reporting_year,segment,origin FROM period_cells GROUP BY ALL
        HAVING ABS(SUM(count_probability)-1)>1e-10
          OR ABS(SUM(balance_probability)-1)>1e-10)""").fetchone()[0]
    if bad:
        raise ValueError("Year matrix probability reconciliation failed")
    # Decimal sums stay in SQL for exact reconciliation, before JSON conversion.
    columns = "segment,origin,destination,pairs,opening_upb,missing_balance_pairs"
    pooled = """SELECT segment,origin,destination,SUM(pairs) AS pairs,
        SUM(opening_upb) AS opening_upb,SUM(missing_balance_pairs) AS missing_balance_pairs
        FROM period_cells WHERE reporting_year IS NOT NULL GROUP BY ALL"""
    lifetime = f"SELECT {columns} FROM period_cells WHERE reporting_year IS NULL"
    differences = db.execute(f"""SELECT COUNT(*) FROM (
        ({pooled} EXCEPT ALL {lifetime}) UNION ALL
        ({lifetime} EXCEPT ALL {pooled}))""").fetchone()[0]
    if differences:
        raise ValueError("Year cells must reconcile exactly to lifetime counts and opening UPB")
    total = db.execute("SELECT COUNT(*) FROM period_pairs WHERE adjacent").fetchone()[0]
    result = json_ready(rows(db, """SELECT * FROM period_cells
        ORDER BY reporting_year NULLS FIRST,segment,origin,destination"""))
    return result, total


def build(root, case):
    manifest = case["manifest"]
    scratch = root / ".tmp"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="year-transitions-", dir=scratch) as temp:
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            db.execute("SET threads=2")
            db.execute("SET temp_directory=?", [temp])
            for name in ("dim_loan", "fact_loan_month"):
                db.read_parquet(str(contained(root, manifest["canonical_run"]) /
                                    (name + ".parquet"))).create_view(name)
            result, total = aggregate(db, engine_root(root) / "sql")
            db.read_parquet(str(contained(root, manifest["portfolio_run"]) /
                                "transition_matrix.parquet")).create_view("frozen_matrix")
            columns = "origin,destination,pairs,opening_upb,missing_balance_pairs"
            actual = f"SELECT {columns} FROM period_cells WHERE reporting_year IS NULL AND segment='all'"
            expected = f"SELECT {columns} FROM frozen_matrix"
            differences = db.execute(f"""SELECT COUNT(*) FROM (
                ({actual} EXCEPT ALL {expected}) UNION ALL
                ({expected} EXCEPT ALL {actual}))""").fetchone()[0]
            if differences:
                raise ValueError("Period matrices must match the frozen engine lifetime matrix")
            segment_inputs = [item for item in manifest["verified_inputs"]
                              if contained(root, item["path"]).name == "transitions.parquet"]
            if len(segment_inputs) != 1:
                raise ValueError("One verified segmented transition mart is required")
            db.read_parquet(str(contained(root, segment_inputs[0]["path"]))).create_view("frozen_segmented")
            columns = "segment," + columns
            actual = f"SELECT {columns} FROM period_cells WHERE reporting_year IS NULL AND segment<>'all'"
            expected = f"SELECT {columns} FROM frozen_segmented"
            differences = db.execute(f"""SELECT COUNT(*) FROM (
                ({actual} EXCEPT ALL {expected}) UNION ALL
                ({expected} EXCEPT ALL {actual}))""").fetchone()[0]
            if differences:
                raise ValueError("Period matrices must match the frozen engine segmented matrix")
    return {"schema_version": 1, "method_version": VERSION,
            "case_id": manifest["case_id"], "pipeline_run": manifest["pipeline_run"],
            "reporting_years": sorted({r["reporting_year"] for r in result if r["reporting_year"] is not None}),
            "rows": [r for r in result if r["reporting_year"] is not None],
            "lifetime_rows": [r for r in result if r["reporting_year"] is None],
            "adjacent_pairs": total,
            "reconciliation": {"year_to_lifetime": "PASS", "frozen_engine_lifetime": "PASS",
                               "frozen_engine_segmented": "PASS"},
            "year_attribution": "opening_reporting_month_year",
            "limitations": [
                "Year is the reporting year at t; December to January belongs to December's year.",
                "Only observed adjacent calendar months; no gap bridging or terminal-origin pairs.",
                "Probabilities use the same year/segment/origin denominator; missing UPB is not zero.",
                "Repeated pairs are dependent. Distinct loans cannot be summed across cells or years.",
                "Sparse means fewer than 30 distinct loans; this is a descriptive threshold.",
                "Reporting date range, vintage horizon and episode follow-up filters do not apply."],
            "visibility": "private", "public_release_approved": False}
