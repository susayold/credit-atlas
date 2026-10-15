"""Trace the pinned Release-47 field contract through D01 canonical outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

import duckdb

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor/credit_risk_strategy_lab"
sys.path.insert(0, str(VENDOR / "src"))
from crsl.canonical import ENUMS, SENTINELS  # noqa: E402
from crsl.contracts import ORIG_DATES, PERF_DATES, ORIG_NUMERIC, PERF_NUMERIC  # noqa: E402
from credit_atlas.workspace import sha256, write_new  # noqa: E402

CASE = ROOT / "artifacts/private/d01-a24484b21a21/case-complete.json"
case = json.loads(CASE.read_text(encoding="utf-8"))
canonical = ROOT / case["canonical_run"]
out = ROOT / "artifacts/private" / f"d01-canonical-semantics-{uuid4().hex[:12]}"
out.mkdir(parents=True, exist_ok=False)
db = duckdb.connect()
db.execute("SET memory_limit='512MB'")
db.execute("SET threads=2")
for table in ("dim_loan", "fact_loan_month"):
    db.read_parquet(str(canonical / f"{table}.parquet")).create_view(table)

# Field-specific sentinel parity: a token becomes null only for its documented field.
sentinel_audit = []
for field, token in SENTINELS.items():
    table = "dim_loan" if field in set(ORIG_NUMERIC) | set(ORIG_DATES) or field in {
        "first_time_homebuyer", "occupancy", "channel", "property_type", "postal_code", "loan_purpose"
    } else "fact_loan_month"
    raw_missing, canonical_missing, zero_count = db.execute(
        f'''SELECT count(*) FILTER (WHERE trim(raw_{field}) IN (?,'')),
                   count(*) FILTER (WHERE {field} IS NULL),
                   count(*) FILTER (WHERE try_cast({field} AS DECIMAL(18,6))=0)
            FROM {table}''', [token]
    ).fetchone()
    if raw_missing != canonical_missing:
        raise AssertionError(f"{field}: raw missing {raw_missing} != canonical null {canonical_missing}")
    sentinel_audit.append({"table": table, "field": field, "token": token,
                           "raw_blank_or_sentinel": raw_missing,
                           "canonical_null": canonical_missing, "canonical_zero": zero_count})

# All observed categories must be covered by the pinned categorical contract.
enum_audit = []
for table_name, enums in ENUMS.items():
    table = "origination" if table_name == "origination" else "performance"
    for field, allowed in enums.items():
        observed = {r[0] for r in db.execute(
            f"SELECT DISTINCT trim(raw_{field}) FROM {'dim_loan' if table == 'origination' else 'fact_loan_month'}"
        ).fetchall()}
        if not observed <= allowed:
            raise AssertionError(f"{table}.{field}: undocumented values {sorted(observed - allowed)}")
        enum_audit.append({"table": table, "field": field,
                           "observed_values": sorted(observed), "allowed_values": sorted(allowed)})

# Independently calculate delinquency and termination labels from raw codes.
mapping_differences = db.execute('''SELECT count(*) FROM fact_loan_month WHERE
 delinquency_state IS DISTINCT FROM CASE
   WHEN trim(raw_delinquency)='00' THEN 'CURRENT'
   WHEN trim(raw_delinquency)='01' THEN 'D1'
   WHEN trim(raw_delinquency)='02' THEN 'D2'
   WHEN trim(raw_delinquency)='RA' THEN 'REO'
   WHEN try_cast(trim(raw_delinquency) AS INTEGER) BETWEEN 3 AND 99 THEN 'D3PLUS'
   ELSE 'UNKNOWN' END
 OR terminal_type IS DISTINCT FROM CASE
   WHEN trim(raw_zero_balance_code)='01' THEN 'PREPAID_OR_MATURED'
   WHEN trim(raw_zero_balance_code) IN ('02','03','09') THEN 'CREDIT_TERMINATION'
   WHEN trim(raw_zero_balance_code) IN ('15','16','96') THEN 'OTHER_TERMINATION'
   ELSE NULL END''').fetchone()[0]
if mapping_differences:
    raise AssertionError(f"{mapping_differences} state/termination mapping differences")

# Verify HARP subset and dates/percentage-point preservation against raw fields.
harp_differences = db.execute("""SELECT count(*) FROM dim_loan WHERE
 is_relief_refinance IS DISTINCT FROM (trim(raw_harp)='Y') OR
 is_harp_subset IS DISTINCT FROM (trim(raw_harp)='Y' AND original_ltv>80)""").fetchone()[0]
date_checks = {}
for field in ORIG_DATES:
    date_checks[f"dim_loan.{field}"] = db.execute(
        f"SELECT count(*) FROM dim_loan WHERE {field} IS DISTINCT FROM "
        f"CASE WHEN trim(raw_{field})='' THEN NULL ELSE strptime(trim(raw_{field}),'%Y%m')::DATE END"
    ).fetchone()[0]
for field in PERF_DATES:
    date_checks[f"fact_loan_month.{field}"] = db.execute(
        f"SELECT count(*) FROM fact_loan_month WHERE {field} IS DISTINCT FROM "
        f"CASE WHEN trim(raw_{field})='' THEN NULL ELSE strptime(trim(raw_{field}),'%Y%m')::DATE END"
    ).fetchone()[0]
if harp_differences or any(date_checks.values()):
    raise AssertionError({"harp_differences": harp_differences, "date_differences": date_checks})

percentage_fields = ["mi_percent", "original_cltv", "original_dti", "original_interest_rate", "original_ltv"]
percentage_values = {}
numeric_cast_differences = {}
for field in percentage_fields:
    percentage_values[field] = db.execute(
        f"SELECT min({field}),max({field}),count(*) FILTER(WHERE {field}=0) FROM dim_loan"
    ).fetchone()
    sentinel_clause = (f"trim(raw_{field}) IN ('','{SENTINELS[field]}')" if field in SENTINELS
                       else f"trim(raw_{field})=''")
    numeric_cast_differences[field] = db.execute(
        f"SELECT count(*) FROM dim_loan WHERE {field} IS DISTINCT FROM "
        f"CASE WHEN {sentinel_clause} THEN NULL "
        f"ELSE try_cast(trim(raw_{field}) AS DECIMAL(18,6)) END"
    ).fetchone()[0]
    if numeric_cast_differences[field]:
        raise AssertionError(f"{field}: source-value cast mismatch")

counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
          for table in ("dim_loan", "fact_loan_month")}
db.close()
receipt = {
    "status": "PASS", "requirement": "M01-003", "scope": "supplied pinned Release-47 2012 corpus",
    "source_authentication": "not established by this semantic audit",
    "case_receipt_sha256": sha256(CASE),
    "canonical_inputs": [
        {"path": str((canonical / f"{table}.parquet").relative_to(ROOT)),
         "sha256": sha256(canonical / f"{table}.parquet")} for table in ("dim_loan", "fact_loan_month")
    ],
    "field_counts": counts, "sentinel_fields_checked": len(sentinel_audit),
    "sentinel_audit": sentinel_audit, "enum_fields_checked": len(enum_audit),
    "enum_audit": enum_audit, "monthly_state_termination_mapping_rows": counts["fact_loan_month"],
    "mapping_differences": mapping_differences, "harp_flag_differences": harp_differences,
    "month_date_mapping_differences": date_checks,
    "percentage_point_fields_min_max_zero_count": {
        key: {"min": str(value[0]), "max": str(value[1]), "zero_count": value[2]}
        for key, value in percentage_values.items()
    },
    "percentage_point_raw_cast_differences": numeric_cast_differences,
    "method_sha256": sha256(Path(__file__)), "status_note": "one-vintage descriptive semantic trace only",
}
write_new(out / "audit.json", receipt)
write_new(out / "receipt.json", {"status": "PASS", "requirement": "M01-003",
    "audit": str((out / "audit.json").relative_to(ROOT)), "sentinel_fields_checked": len(sentinel_audit),
    "enum_fields_checked": len(enum_audit), "mapping_differences": mapping_differences,
    "harp_flag_differences": harp_differences, "date_mapping_differences": date_checks,
    "source_authentication": "not established"})
print(out)
print(json.dumps({"sentinels": len(sentinel_audit), "enum_fields": len(enum_audit),
                  "state_map_differences": mapping_differences, "harp_differences": harp_differences,
                  "date_differences": date_checks}, indent=2))
