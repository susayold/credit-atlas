"""SBA FOIA record-level canonical adapter, dictionary evidence and descriptive marts."""
from __future__ import annotations

import re
import uuid
import zipfile
from decimal import Decimal
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

import duckdb
import pyarrow.parquet as pq

from .public_suite import verify_acquisition
from .workspace import contained, read_json, sha256, timestamp, write_new

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
STATUS = {"7A": {"CANCLD": "cancelled", "CHGOFF": "charged_off", "COMMIT": "undisbursed",
                  "EXEMPT": "disbursed_status_withheld", "PIF": "paid_in_full", "P I F": "paid_in_full"},
          "504": {"CANCLD": "cancelled", "CHGOFF": "charged_off", "NOT FUNDED": "undisbursed",
                  "EXEMPT": "disbursed_status_withheld", "PIF": "paid_in_full", "CLOSED": "closed_other_legacy"}}
CONTRACT = {"version": "sba-foia-source-record-descriptive-v1", "snapshot_date": "2026-06-30",
            "grain": "source snapshot CSV record; no released unique loan/entity ID",
            "record_key": "source_id + original data row ordinal, bound to raw source SHA256",
            "location_id": "SBA unique lender ID, not loan or borrower ID",
            "currency": "USD", "money_type": "DECIMAL(38,18)",
            "source_precision_policy": "preserve decimal source precision; flag fractional-cent records, do not silently round to cents",
            "approval_amount_scope": {"7A": "total loan amount", "504": "SBA/CDC loan component"},
            "chargeoff_amount_scope": {"7A": "includes guaranteed and non-guaranteed loan balance", "504": "SBA/CDC balance"},
            "status_mapping": STATUS, "duplicate_policy": "retain and flag exact source duplicate records; no inferred entity deduplication",
            "fiscal_year": "October 1 through September 30, ending-year convention",
            "publication_time": "unknown; snapshot/extraction times do not establish historical feature availability",
            "amounts_are_current_exposure": False, "fixed_horizon_default_target_qualified": False,
            "model_training_performed": False,
            "interpretation_sources": ["https://data.sba.gov/dataset/7a-504-foia",
                "https://legacy.sba.gov/document/report-small-business-administration-loan-program-performance"]}
DATES = {"AsOfDate": "snapshot_date", "ApprovalDate": "approval_date", "FirstDisbursementDate": "first_disbursement_date",
         "PaidInFullDate": "paid_in_full_date", "ChargeOffDate": "charge_off_date"}
MONEY = {"GrossApproval": "reported_approval_amount", "GrossChargeOffAmount": "reported_chargeoff_amount",
         "SBAGuaranteedApproval": "guaranteed_approval_amount", "ThirdPartyDollars": "third_party_amount"}
INTEGERS = {"ApprovalFY": "approval_fiscal_year", "TermInMonths": "term_months", "JobsSupported": "jobs_supported"}
TEXT = {"LocationID": "lender_source_id", "ProjectState": "project_state", "NaicsCode": "naics_code",
        "BusinessType": "business_type", "BusinessAge": "business_age", "ProcessingMethod": "processing_method"}


def status_name(program, raw):
    if program not in STATUS or not isinstance(raw, str):
        raise ValueError("Reviewed SBA program/status strings required")
    return STATUS[program].get(raw.strip(), "unmapped")


def parse_dictionary(path):
    """Read only text cells, resolving workbook relationships rather than sheet order."""
    with zipfile.ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 100 * 1024**2 or archive.testzip() is not None:
            raise ValueError("Invalid dictionary archive")
        def xml(name):
            value = archive.read(name)
            if b"<!DOCTYPE" in value or b"<!ENTITY" in value:
                raise ValueError("Dictionary XML entities are unsupported")
            return ET.fromstring(value)
        def text(node):
            return "".join(t.text or "" for t in node.findall("s:t", NS) + node.findall("s:r/s:t", NS))
        shared = [text(n) for n in xml("xl/sharedStrings.xml").findall("s:si", NS)] if "xl/sharedStrings.xml" in archive.namelist() else []
        relations = {n.attrib["Id"]: n.attrib for n in xml("xl/_rels/workbook.xml.rels")}
        result = {}
        for sheet in xml("xl/workbook.xml").findall("s:sheets/s:sheet", NS):
            name = sheet.attrib["name"]
            program = {"7(a) Data Dictionary": "7A", "504 Data Dictionary": "504"}.get(name)
            if program is None or program in result:
                raise ValueError("Expected distinct source dictionary sheets")
            relation = relations[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            target = relation["Target"]
            if relation.get("TargetMode") == "External" or ".." in PurePosixPath(target).parts:
                raise ValueError("Local workbook relationships required")
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            entries = []
            for row in xml(target).findall("s:sheetData/s:row", NS):
                cells = {}
                for cell in row.findall("s:c", NS):
                    if cell.find("s:f", NS) is not None:
                        raise ValueError("Dictionary formulas are unsupported")
                    coordinate = cell.attrib["r"]
                    value = cell.find("s:v", NS)
                    if cell.attrib.get("t") == "s":
                        content = shared[int(value.text)]
                    elif cell.attrib.get("t") == "inlineStr":
                        content = text(cell.find("s:is", NS))
                    else:
                        content = value.text if value is not None else ""
                    if not content or not content.strip():
                        continue
                    cells[re.sub(r"\d+$", "", coordinate)] = (coordinate, content)
                if not cells or all(not value[1] for value in cells.values()):
                    continue
                if set(cells) != {"A", "B"}:
                    raise ValueError("Expected field/definition dictionary columns")
                if not entries and cells["A"][1] == "Field Name" and cells["B"][1] == "Definition":
                    continue
                entries.append({"field": cells["A"][1], "definition": cells["B"][1],
                                "sheet": name, "field_cell": cells["A"][0], "definition_cell": cells["B"][0]})
            if not entries or len({e["field"] for e in entries}) != len(entries):
                raise ValueError("Unique nonempty dictionary fields required")
            result[program] = entries
        if set(result) != {"7A", "504"}:
            raise ValueError("Both program dictionaries required")
        return result


def q(name):
    return '"' + name.replace('"', '""') + '"'


def typed_expression(field, kind):
    value = "NULLIF(TRIM(" + q(field) + "),'')"
    return "TRY_CAST(" + value + " AS " + kind + ")"


def canonical_sql(fields, program, source_id):
    aliases = ["'" + source_id + "' AS source_id", "row_number() OVER ()::BIGINT AS source_row_ordinal",
               "'" + source_id + ":' || row_number() OVER ()::VARCHAR AS source_record_key",
               "TRIM(Program) AS program", "LoanStatus AS status_raw"]
    status = "CASE TRIM(LoanStatus) " + " ".join("WHEN '" + k + "' THEN '" + v + "'" for k, v in STATUS[program].items()) + " ELSE 'unmapped' END"
    aliases.append(status + " AS status")
    for source, name in DATES.items():
        aliases.append(typed_expression(source, "DATE") + " AS " + name)
    for source, name in MONEY.items():
        aliases.append((typed_expression(source, "DECIMAL(38,18)") if source in fields else "NULL::DECIMAL(38,18)") + " AS " + name)
    for source, name in INTEGERS.items():
        aliases.append(typed_expression(source, "BIGINT") + " AS " + name)
    aliases.append((typed_expression("InitialInterestRate", "DECIMAL(38,18)") if "InitialInterestRate" in fields else "NULL::DECIMAL(38,18)") + " AS initial_rate_pct")
    aliases.extend("NULLIF(TRIM(" + q(source) + "),'') AS " + name for source, name in TEXT.items())
    return "SELECT " + ",".join(aliases) + " FROM native"


def source_quality(db, fields):
    counts = {}
    types = {**{k: "DATE" for k in DATES}, **{k: "DECIMAL(38,18)" for k in MONEY}, **{k: "BIGINT" for k in INTEGERS}}
    if "InitialInterestRate" in fields:
        types["InitialInterestRate"] = "DECIMAL(38,18)"
    for field, kind in types.items():
        if field not in fields:
            continue
        raw = q(field)
        parsed = typed_expression(field, kind)
        blank = "TRIM(" + raw + ")=''"
        checks = {"blank": blank, "invalid_nonblank": "NOT (" + blank + ") AND " + parsed + " IS NULL"}
        if kind.startswith("DECIMAL") or kind == "BIGINT":
            numeric = typed_expression(field, "DECIMAL(38,18)")
            checks["precision_loss"] = numeric + " IS NOT NULL AND (" + parsed + " IS NULL OR " + numeric + " <> " + parsed + ")"
            checks["non_decimal_nonblank"] = "NOT (" + blank + ") AND NOT regexp_full_match(TRIM(" + raw + "),'[+-]?[0-9]+([.][0-9]+)?([eE][+-]?[0-9]+)?')"
            checks["excess_fractional_digits"] = "length(split_part(TRIM(" + raw + "),'.',2))>18"
            if field in MONEY:
                checks["fractional_cent_records"] = numeric + "<>round(" + numeric + ",2)"
        if kind == "DATE":
            checks["non_iso_nonblank"] = "NOT (" + blank + ") AND NOT regexp_full_match(" + raw + ",'[0-9]{4}-[0-9]{2}-[0-9]{2}')"
        counts[field] = {name: db.sql("SELECT COUNT(*) FILTER(WHERE " + expression + ") FROM native").fetchone()[0] for name, expression in checks.items()}
        if kind.startswith("DECIMAL") or kind == "BIGINT":
            scientific = db.sql("SELECT " + raw + " AS raw," + parsed + " AS typed,count(*) AS copies FROM native WHERE regexp_matches(" + raw + ",'[eE]') GROUP BY ALL").fetchall()
            counts[field]["scientific_not_exact"] = sum(copies for value, typed, copies in scientific if typed is None or Decimal(value) != typed)
    return counts


def prepare_sba(root: Path, suite_id: str):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("Private D: workspace required")
    source_folder, acquisition = verify_acquisition(root, suite_id)
    specs = sorted([s for s in acquisition["sources"] if s["source_id"].startswith("sba-") and s["kind"] == "csv"], key=lambda s: s["source_id"])
    dictionary_spec = next(s for s in acquisition["sources"] if s["source_id"] == "sba-dictionary")
    if len(specs) != 6 or any(s["status"] != "DOWNLOADED_AND_PROFILED" for s in specs + [dictionary_spec]):
        raise ValueError("Six complete SBA segments and dictionary required")
    dictionary = parse_dictionary(source_folder / dictionary_spec["file"])
    output = contained(root, "artifacts/private/business-sba-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    source_digest = sha256(source_folder / "acquisition-complete.json")
    write_new(output / "access-start.json", {"started_at": timestamp(), "suite_id": suite_id,
              "source_receipt_sha256": source_digest, "purpose": "SBA_source_record_descriptive_adapter"})
    write_new(output / "dictionary.json", dictionary)
    write_new(output / "contract.json", CONTRACT)
    diagnostics, files, control = {}, [], []
    try:
        with duckdb.connect() as db:
            db.execute("SET threads=2")
            db.execute("SET memory_limit='1GB'")
            db.execute("SET temp_directory=?", [str(output / "duckdb-temp")])
            for source in specs:
                identifier = source["source_id"]
                program = "504" if "sba-504-" in identifier else "7A"
                fields = source["profile"]["fields"]
                if fields != [entry["field"] for entry in dictionary[program]]:
                    raise ValueError("CSV columns differ from program dictionary")
                db.sql("SELECT * FROM read_csv(?,header=true,all_varchar=true,strict_mode=true,parallel=false,nullstr=?)",
                       params=[str(source_folder / source["file"]), "__NO_NULL_" + output.name + "__"]).create_view("native", replace=True)
                quality = source_quality(db, fields)
                if any(v.get("invalid_nonblank", 0) or v.get("precision_loss", 0) or v.get("non_iso_nonblank", 0)
                       or v.get("non_decimal_nonblank", 0) or v.get("excess_fractional_digits", 0) or v.get("scientific_not_exact", 0) for v in quality.values()):
                    write_new(output / "parse-problems.json", {"source_id": identifier, "counts": quality})
                    raise ValueError("Malformed or precision-losing source values require review")
                db.sql(canonical_sql(fields, program, identifier)).create_view("typed", replace=True)
                counts = db.sql("SELECT count(*),count(distinct source_record_key),count(*) FILTER(WHERE program<>?),count(*) FILTER(WHERE snapshot_date IS NULL OR snapshot_date<>DATE '2026-06-30') FROM typed", params=[program]).fetchone()
                if counts != (source["profile"]["rows"], source["profile"]["rows"], 0, 0):
                    raise ValueError("SBA count/key/program/snapshot reconciliation failed")
                path = output / (identifier + ".parquet")
                db.sql("SELECT * FROM typed").to_parquet(str(path), compression="zstd")
                db.read_parquet(str(path)).create_view("saved", replace=True)
                raw_amounts, saved_amounts = [], []
                for field, name in MONEY.items():
                    if field in fields:
                        raw_value = "CAST(NULLIF(TRIM(" + q(field) + "),'') AS DECIMAL(38,18))"
                        raw_amounts.extend(["SUM(" + raw_value + ") AS " + name, "COUNT(" + raw_value + ") AS known_" + name])
                        saved_amounts.extend(["SUM(" + name + ") AS " + name, "COUNT(" + name + ") AS known_" + name])
                raw_group = "SELECT TRIM(Program) AS program,LoanStatus AS status_raw,COUNT(*) AS records," + ",".join(raw_amounts) + " FROM native GROUP BY ALL"
                saved_group = "SELECT program,status_raw,COUNT(*) AS records," + ",".join(saved_amounts) + " FROM saved GROUP BY ALL"
                difference = db.sql("SELECT COUNT(*) FROM ((" + raw_group + " EXCEPT ALL " + saved_group + ") UNION ALL (" + saved_group + " EXCEPT ALL " + raw_group + "))").fetchone()[0]
                if difference:
                    raise ValueError("Saved typed counts/status/all money sums and known-value counts differ from raw")
                duplicates = db.sql("SELECT coalesce(sum(copies-1),0)::BIGINT FROM (SELECT " + ",".join(q(f) for f in fields) + ",count(*) AS copies FROM native GROUP BY ALL HAVING count(*)>1)").fetchone()[0]
                flags = db.sql("""SELECT count(*) FILTER(WHERE status='unmapped') AS unmapped_status,
                    count(*) FILTER(WHERE approval_date IS NULL OR approval_fiscal_year IS NULL) AS missing_approval_date_or_year,
                    count(*) FILTER(WHERE approval_fiscal_year<>year(approval_date)+CASE WHEN month(approval_date)>=10 THEN 1 ELSE 0 END) AS fiscal_year_mismatch,
                    count(*) FILTER(WHERE approval_date>snapshot_date OR first_disbursement_date>snapshot_date OR charge_off_date>snapshot_date OR paid_in_full_date>snapshot_date) AS event_date_after_snapshot,
                    count(*) FILTER(WHERE first_disbursement_date<approval_date) AS disbursement_before_approval,
                    count(*) FILTER(WHERE charge_off_date<approval_date OR paid_in_full_date<approval_date) AS outcome_before_approval,
                    count(*) FILTER(WHERE status='charged_off' AND charge_off_date IS NULL) AS charged_off_missing_date,
                    count(*) FILTER(WHERE status<>'charged_off' AND charge_off_date IS NOT NULL) AS other_status_has_chargeoff_date,
                    count(*) FILTER(WHERE reported_approval_amount<0 OR reported_chargeoff_amount<0) AS signed_negative_amount,
                    count(*) FILTER(WHERE reported_chargeoff_amount>reported_approval_amount) AS chargeoff_exceeds_approval,
                    count(distinct lender_source_id) AS distinct_lender_source_ids FROM saved""").arrow().read_all().to_pylist()[0]
                diagnostics[identifier] = {"parse": quality, "exact_duplicate_excess_rows": duplicates,
                    "retained_rows": counts[0], "flags": flags, "raw_saved_reconciliation_differing_groups": difference}
                control.extend(db.sql(raw_group).arrow().read_all().to_pylist())
                files.append({"source_id": identifier, "program": program, "file": path.name, "rows": counts[0], "source_sha256": source["sha256"], "sha256": sha256(path)})
            db.read_parquet([str(output / f["file"]) for f in files]).create_view("records")
            if db.sql("SELECT count(*)-count(distinct source_record_key) FROM records").fetchone()[0]:
                raise ValueError("Source record keys overlap across segments")
            marts = {}
            for dimension, expression in {"program_status": "'all'", "approval_fiscal_year": "approval_fiscal_year::VARCHAR",
                                          "project_state": "coalesce(project_state,'__unavailable__')",
                                          "naics_two_digit": "CASE WHEN regexp_full_match(naics_code,'[0-9]{2,6}') THEN substring(naics_code,1,2) ELSE '__unavailable__' END"}.items():
                result = db.sql("SELECT program," + expression + " AS bucket,status,COUNT(*) AS records,"
                                "SUM(reported_approval_amount)::VARCHAR AS reported_approval_amount,"
                                "COUNT(reported_approval_amount) AS known_approval_amount_records,"
                                "SUM(reported_chargeoff_amount)::VARCHAR AS reported_chargeoff_amount,"
                                "COUNT(reported_chargeoff_amount) AS known_chargeoff_amount_records "
                                "FROM records GROUP BY ALL ORDER BY program,bucket,status").arrow().read_all().to_pylist()
                if sum(r["records"] for r in result) != sum(f["rows"] for f in files):
                    raise ValueError("Aggregate record denominators do not reconcile")
                marts[dimension] = result
            write_new(output / "aggregates.json", {"currency": "USD", "amount_scope": CONTRACT["approval_amount_scope"],
                "source_record_count": sum(f["rows"] for f in files), "dimensions": marts,
                "limitations": ["Counts describe source records, not proven unique loans or borrowers.",
                    "Approval amounts include cancelled/undisbursed records; not current EAD.",
                    "7A total-loan and 504 SBA/CDC component amounts have separate scopes.",
                    "Snapshot status shares are not fixed-horizon default rates.",
                    "EXEMPT is disbursed status withheld, not an observed non-default.",
                    "FY2026 is incomplete at June 30; cohorts have different follow-up.",
                    "No default model fit or historical feature-availability qualification."]})
        write_new(output / "quality.json", diagnostics)
        write_new(output / "reconciliation.json", {"status": "PASS", "raw_saved_status_count_and_decimal_sums": "PASS_ALL_SIX_SOURCES",
                  "aggregate_count_denominators": "PASS_ALL_FOUR_DIMENSIONS", "source_record_keys_unique": True})
        verify_acquisition(root, suite_id)
        if sha256(source_folder / "acquisition-complete.json") != source_digest:
            raise ValueError("Acquisition changed during SBA build")
        write_new(output / "business-complete.json", {"schema_version": 1, "status": "SBA_SOURCE_RECORD_DESCRIPTIVE_PREPARED",
                  "business_id": output.name, "completed_at": timestamp(), "suite_id": suite_id,
                  "source_receipt_sha256": source_digest, "dictionary_source_sha256": dictionary_spec["sha256"],
                  "method_source_sha256": sha256(Path(__file__)), "files": files, "rows": sum(f["rows"] for f in files),
                  "model_training_performed": False, "fixed_horizon_default_target_qualified": False,
                  "visibility": "private", "public_release_approved": False,
                  "outputs_sha256": {p.name: sha256(p) for p in output.iterdir() if p.is_file()}})
        return {"directory": str(output), "status": "SBA_SOURCE_RECORD_DESCRIPTIVE_PREPARED", "rows": sum(f["rows"] for f in files),
                "quality_flags": {k: v["flags"] for k, v in diagnostics.items()}, "model_training_performed": False}
    except Exception as error:
        write_new(output / "business-failed.json", {"status": "FAIL", "failed_at": timestamp(), "exception_type": type(error).__name__,
                  "model_training_performed": False})
        raise


def verify_sba(root, business_id):
    if not isinstance(business_id, str) or not re.fullmatch(r"business-sba-[0-9a-f]{12}", business_id):
        raise ValueError("Valid SBA business identifier required")
    folder = contained(root, "artifacts/private/" + business_id)
    receipt = read_json(folder / "business-complete.json")
    if (receipt.get("schema_version") != 1 or receipt.get("business_id") != business_id
            or receipt.get("status") != "SBA_SOURCE_RECORD_DESCRIPTIVE_PREPARED" or receipt.get("visibility") != "private"
            or receipt.get("method_source_sha256") != sha256(Path(__file__))
            or any(receipt.get(k) is not False for k in ("model_training_performed", "fixed_horizon_default_target_qualified", "public_release_approved"))):
        raise ValueError("SBA method/private descriptive contract changed")
    source_folder, acquisition = verify_acquisition(root, receipt["suite_id"])
    sources = {s["source_id"]: s for s in acquisition["sources"]}
    if (sha256(source_folder / "acquisition-complete.json") != receipt["source_receipt_sha256"]
            or sources["sba-dictionary"]["sha256"] != receipt["dictionary_source_sha256"]):
        raise ValueError("SBA acquisition/dictionary lineage changed")
    expected_sources = {s["source_id"] for s in acquisition["sources"] if s["source_id"].startswith("sba-") and s["kind"] == "csv"}
    if len(receipt["files"]) != 6 or {f["source_id"] for f in receipt["files"]} != expected_sources:
        raise ValueError("Six distinct source segments required")
    expected_outputs = {"access-start.json", "contract.json", "dictionary.json", "quality.json", "aggregates.json", "reconciliation.json"} | {n + ".parquet" for n in expected_sources}
    if set(receipt["outputs_sha256"]) != expected_outputs:
        raise ValueError("Complete SBA evidence digests required")
    for name, digest in receipt["outputs_sha256"].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError("SBA saved evidence changed")
    for file in receipt["files"]:
        source = sources[file["source_id"]]
        if (file["file"] != file["source_id"] + ".parquet" or file["source_sha256"] != source["sha256"]
                or file["sha256"] != receipt["outputs_sha256"][file["file"]]
                or pq.read_metadata(folder / file["file"]).num_rows != file["rows"] or file["rows"] != source["profile"]["rows"]):
            raise ValueError("SBA source/file population changed")
    aggregates = read_json(folder / "aggregates.json")
    if (read_json(folder / "contract.json") != CONTRACT or receipt["rows"] != sum(f["rows"] for f in receipt["files"])
            or aggregates["source_record_count"] != receipt["rows"] or any(sum(r["records"] for r in rows) != receipt["rows"] for rows in aggregates["dimensions"].values())
            or read_json(folder / "reconciliation.json")["status"] != "PASS"):
        raise ValueError("SBA contract/aggregate population does not reconcile")
    return folder, receipt, aggregates, sha256(folder / "business-complete.json")
