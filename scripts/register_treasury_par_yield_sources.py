"""Bind a verified private Treasury par-yield receipt to the public-safe registers."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "docs/data/creditatlas-source-release-register-2026-10-17.json"
PROJECT = REPO / "docs/data/creditatlas-project-register-2026-10-17.json"
TRACE = REPO / "docs/data/n02-source-to-kpi-map-2026-10-17.json"
GROUP_ID = "treasury-direct-par-yield-curve"
DEFAULT_WORKSPACE = REPO.parent / "credit-atlas"
ARCHIVE_PAGE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives"
CURRENT_PAGE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView"
METHODOLOGY = "https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology"
STATISTICS = "https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics"
FAQ = "https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions"
N02_DOC = "docs/TREASURY_DIRECT_PAR_YIELD_SOURCE_REVIEW_VI.md"
RUN_PREFIX = "treasury-par-yield-"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update(workspace: Path, run_id: str):
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:" or not run_id.startswith(RUN_PREFIX):
        raise ValueError("Receipt registration requires a D: workspace and Treasury run ID")
    folder = workspace / "data/private/market-context/treasury-par-yields" / run_id
    receipt_path = folder / "acquisition-audit.json"
    receipt = load(receipt_path)
    if (receipt.get("run_id") != run_id or receipt.get("status") != "DOWNLOADED_AND_AUDITED"
            or receipt.get("visibility") != "private" or receipt.get("public_release_approved") is not False
            or receipt.get("model_qualified") is not False):
        raise ValueError("Treasury receipt is not complete, private, and unqualified")
    acquisition_method = REPO / "scripts/acquire_treasury_par_yields.py"
    if receipt.get("acquisition_method_sha256") != hash_file(acquisition_method):
        raise ValueError("Treasury receipt was produced by a different acquisition method")
    manifest = {item["file"]: item for item in receipt["files"]}
    for item in receipt["files"]:
        path = folder / item["file"]
        if not path.is_file() or hash_file(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError("Treasury receipt file hash or size changed")
    normalized = load_normalized(folder / receipt["normalized_file"]["file"])
    if (len(normalized) != receipt["native_rows"] or not normalized
            or normalized[0]["observation_date"].isoformat() != receipt["first_date"]
            or normalized[-1]["observation_date"].isoformat() != receipt["last_date"]):
        raise ValueError("Treasury normalized observations disagree with the acquisition receipt")
    for source in receipt["source_files"]:
        if source["file"] not in manifest or source["sha256"] != manifest[source["file"]]["sha256"]:
            raise ValueError("Treasury source partition is not bound to the acquisition file manifest")

    raw_counts = {}
    for source in receipt["source_files"]:
        period = source["source_id"].removeprefix("treasury-daily-par-yield-")
        first, last = date.fromisoformat(source["first_date"]), date.fromisoformat(source["last_date"])
        scoped = [row for row in normalized if first <= row["observation_date"] <= last]
        if len(scoped) != source["row_count"]:
            raise ValueError("Treasury partition row count does not match normalized data")
        if period != "1990-2023" and any(row["observation_date"].year != int(period) for row in scoped):
            raise ValueError("Treasury annual partition contains a foreign-year observation")
        missing = sum(row[key] is None for row in scoped for key in ("TREASURY2Y", "TREASURY10Y", "TREASURY30Y"))
        raw_counts[period] = missing

    register = load(REGISTER)
    project = load(PROJECT)
    trace = load(TRACE)
    source_records = register["source_records"]
    source_by_id = {row["source_id"]: row for row in source_records}
    new_records = []
    source_ids = []
    retrieved_at = receipt["retrieved_at_utc"]
    parity_summary = (
        "Treasury/FRED exact snapshot parity for all overlapping known values: "
        "2Y and 10Y 9,197/9,197; 30Y 8,203/8,203. FRED ends 2026-10-06; Treasury adds seven later native dates through 2026-10-16. "
        "Treasury 30Y is null for 994 native dates inside its documented discontinuation window; 994 FRED values in that overlap are excluded from the direct P5 route. One separate common missing date is 2010-10-11 across all three tenors."
    )
    for source in receipt["source_files"]:
        period = source["source_id"].removeprefix("treasury-daily-par-yield-")
        source_id = "treasury-par-yield-" + period
        source_ids.append(source_id)
        rights_evidence = [STATISTICS, ARCHIVE_PAGE if period == "1990-2023" else source["source_page_url"],
                           METHODOLOGY, FAQ]
        row = {
            "source_id": source_id,
            "registry_group_id": GROUP_ID,
            "publisher": "U.S. Department of the Treasury",
            "publisher_page_url": ARCHIVE_PAGE if period == "1990-2023" else source["source_page_url"],
            "source_object_url": source["source_object_url"],
            "format": "CSV; official Treasury daily par-yield curve",
            "release_label": f"Daily Treasury par yield curve; source partition {period}",
            "publisher_publication_date": None,
            "publication_date_status": "No release timestamp is embedded per row; retrieval time and last observed market date are recorded separately.",
            "snapshot_as_of": source["last_date"],
            "observed_period_start": source["first_date"],
            "observed_period_end": source["last_date"],
            "native_row_count": source["row_count"],
            "grain": "U.S. market observation date × Treasury par-curve maturity; source values are percent and remain at daily native dates.",
            "modules": ["P5"],
            "consumer_trace": [
                "scripts/acquire_treasury_par_yields.py → private raw partitions, normalized native-date CSV, acquisition-audit.json and exact FRED comparator.",
                "scripts/prepare_market.py --treasury-run → src/credit_atlas/market_data.py; Treasury 2Y/10Y/30Y is primary from 1990-01-02; FRED is retained only for the pre-1990 extension and comparator.",
                "src/credit_atlas/market_views.py → /api/market-view and /api/market-report; row-level source_id/source_sha256 are returned for private inspection/export.",
            ],
            "kpi_or_output": "Daily 2Y/10Y/30Y Treasury constant-maturity par-yield context and same-date slope calculations; not a zero curve, executable quote, security price, borrower outcome, or qualified PD predictor.",
            "method_card_ids": [],
            "rights_use_gate": "Official Treasury CSV is publicly accessible. The reviewed Treasury pages describe source/method and provide downloads but did not establish a separate raw-data redistribution grant for this project; raw data and outputs remain private, no public rehosting approval is recorded, and no model use is qualified.",
            "rights_review_status": "DIRECT_TREASURY_PUBLIC_DOWNLOAD; PRIVATE_RAW; PUBLIC_RAW_REHOSTING_UNAPPROVED; NO_MODEL_QUALIFICATION",
            "receipt_status": f"DOWNLOADED_AND_VALIDATED; partition {period}; {parity_summary}",
            "retrieved_at_utc": retrieved_at,
            "receipt_completed_at_utc": retrieved_at,
            "receipt_reference": "local-private-id:" + run_id,
            "sha256_prefix": source["sha256"][:12],
            "component_sha256_prefixes": {"normalized_three_tenor_panel": receipt["normalized_file"]["sha256"][:12]},
            "missing_cell_count": raw_counts[period],
            "model_qualified_in_receipt": False,
            "public_release_approved_in_receipt": False,
            "scope_note": (f"{source['row_count']} source-native rows from {source['first_date']} to {source['last_date']}; "
                f"{raw_counts[period]} blank cells across 2Y/10Y/30Y are retained as missing. {parity_summary} "
                "The 2021-12-06 methodology break and the 30Y 2002–2006 discontinuation remain explicit. Latest-revised snapshot only, not PIT."),
            "missing_cell_count_basis": "Number of blank cells in the three normalized native tenor columns for this source partition; source blanks remain null and are never imputed.",
            "distributor": None,
            "distributor_url": None,
            "rights_research_as_of": "2026-10-18",
            "rights_evidence_urls": rights_evidence,
            "current_use_status": "Selected as the P5 primary source from 1990-01-02 in local private market case; FRED DGS2/DGS10/DGS30 are used only before 1990 and as exact-overlap comparators. 30Y discontinuation stays unavailable. Public rehosting, scenario calibration and model qualification remain unapproved.",
            "source_series_id": "Daily Treasury Par Yield Curve Rates: 2-year, 10-year, 30-year",
        }
        new_records.append(row)
        source_by_id[source_id] = row
    register["source_records"] = [row for row in source_records if row["source_id"] not in source_ids] + new_records
    register["record_count"] = len(register["source_records"])
    register["supplemental_source_records"] = register["record_count"] - 20
    register["scope_note"] = (
        f"{register['record_count']} source records: 20 public-suite objects and {register['record_count'] - 20} supplemental objects "
        "across 18 broad families, including the direct U.S. Treasury daily par-yield curve partitions 1990–2026. "
        "Concrete records stay edition/grain-specific. This register binds provenance and does not itself complete rights, model, route or capability acceptance. "
        "Raw restricted/uncleared payloads remain private. HMDA exact/cross-vintage, BLS/FHFA parity, Treasury direct parity and remaining family-specific limitations are recorded in their source reviews."
    )

    dataset = {
        "id": GROUP_ID,
        "name": "Direct U.S. Treasury Daily Par Yield Curve",
        "domain": "P5",
        "grain": "Daily market observation date × 2Y/10Y/30Y par-yield tenor; Treasury native dates from 1990, with FRED historical extension only before 1990.",
        "period": "1990-01-02–2026-10-16 direct Treasury; older DGS2/DGS10/DGS30 extension remains FRED-only before the boundary.",
        "status": "Downloaded, profiled, exact-overlap audited and integrated into a receipt-bound private P5 market case/view; raw remains private and model/security-price qualification is false.",
        "access": "Treasury official historical archive 1990–2023 and selected yearly CSV downloads 2024–2026. The private receipt contains 9,205 rows and four original source partitions.",
        "use": "P5 descriptive yield/slopes context at daily native dates. Does not represent a borrower rate, actual security quote, zero-coupon discount curve, PD driver or model-calibrated scenario.",
        "next": "Complete normal-app browser render acceptance and recurring-refresh behavior; keep 30Y missing during the publisher discontinuation; resolve publication/reuse rights before any external raw or derived release.",
        "evidence": N02_DOC,
        "publisher": "U.S. Department of the Treasury; FRED is only the pre-1990 extension/comparator distributor.",
        "rights_review": "Public Treasury download is available; no separate raw-data redistribution grant was identified on pages reviewed. Raw/output private; no model qualification.",
        "source_release_record_ids": source_ids,
    }
    project_datasets = project["datasets"]
    project["datasets"] = [row for row in project_datasets if row["id"] != GROUP_ID] + [dataset]
    project["scope_note"] = (
        "Current review maps 30 dataset groups, binds 129 source records and separates source, method and capability acceptance. "
        "The 50-item ledger remains the sole completion denominator; source counts do not increase capability completion. "
        "API/static smoke counts and browser acceptance are recorded separately. N02/N03 remain scoped to explicit links and selected workflow traces, not every raw row or line of the repository."
    )
    for item in project["current_plan_implementation"]:
        if item["id"] == "N02":
            item["status"] = "In progress: 129-record source-release register; 25/30 parent groups have source-object records. Treasury daily par yields are now direct-source primary in a private P5 case from 1990; exact source overlap passes, while rights and full normal-app browser acceptance remain open."
            item["scope"] = (
                "30 dataset/domain groups traced; all 20 public_sources.catalog IDs match their local receipt. "
                "The 129-record source-release register has 20 public-suite plus 109 supplemental objects across 18 broad families. "
                "Direct BLS/FHFA sources remain distinct from FRED/ALFRED snapshots. Treasury's 1990–2026 daily par yields match the private FRED comparator exactly on 9,197/9,197 common known observations for 2Y and 10Y, and 8,203/8,203 for 30Y; 30Y publisher discontinuation cells remain null. "
                "Rights, release-time vintages, ICE OAS and the remaining output-level KPI traces stay open."
            )
            item["remaining"] = (
                "Complete browser and refresh acceptance for the direct P5 route; bind each remaining material KPI to source field/formula/filter/unit and rights decision. "
                "Keep the five existing source-group dispositions explicit; raw Treasury and ICE payloads stay private."
            )
    save(PROJECT, project)

    trace["scope_note"] = (
        trace["scope_note"].replace("29 parent dataset groups", "30 parent dataset groups")
        .replace("29 parent groups", "30 parent groups")
        .replace("24 groups have source-level objects bound", "25 groups have source-level objects bound")
        .replace("On 2026-10-18, direct BLS UNRATE was added", "On 2026-10-18, direct Treasury daily par yields (1990–2026) were added as a P5 source group after exact Treasury/FRED overlap checks; direct BLS UNRATE was added")
    )
    trace["counts"].update({
        "registered_dataset_domain_records": len(project["datasets"]),
        "mapped_registry_records": len(project["datasets"]),
        "source_level_records": len(register["source_records"]) - 20,
        "supplemental_source_records": len(register["source_records"]) - 20,
        "registry_groups_with_source_objects": 25,
        "registry_groups_without_source_objects": 5,
    })
    trace["source_release_register"].update({
        "record_count": len(register["source_records"]),
        "supplemental_source_records": len(register["source_records"]) - 20,
        "supplemental_source_families": 18,
        "note": register["scope_note"],
        "treasury_direct_group_added": GROUP_ID,
    })
    group_trace = {
        "registry_id": GROUP_ID,
        "source_release_record_ids": source_ids,
        "code_and_consumer": "`scripts/acquire_treasury_par_yields.py` → receipt-bound private source partitions; `src/credit_atlas/market_data.py` → Treasury primary from 1990 plus FRED pre-1990 extension → `market_views.py` → `/api/market-view` and `/api/market-report` → P5 Market & Bond UI/JSON export.",
        "kpi_or_output": "Daily Treasury 2Y/10Y/30Y CMT context; same-date 10Y–2Y and 30Y–10Y slopes where both tenor values exist; descriptive only.",
        "status_and_limits": "9,205 direct Treasury rows (1990-01-02–2026-10-16); 9,197/9,197 exact 2Y and 10Y overlap, 8,203/8,203 exact 30Y observed overlap; seven Treasury native dates post-date the FRED snapshot. Treasury 30Y is missing during the official 2002-02-18–2006-02-08 discontinuation, not filled from 20Y; data stay latest-revised and private; rights/rehosting and model calibration remain open.",
        "evidence_type": "direct_publisher_private_receipt_exact_overlap_and_p5_case",
    }
    trace["registered_record_trace"] = [row for row in trace["registered_record_trace"] if row.get("registry_id") != GROUP_ID] + [group_trace]
    additions = []
    for source in new_records:
        period = source["release_label"].rsplit(" ", 1)[-1]
        additions.append({
            "source_release_record_id": source["source_id"],
            "publisher": source["publisher"],
            "source_id": source["source_series_id"],
            "source_family": "Direct U.S. Treasury daily par yield curve",
            "current_use_status": source["current_use_status"],
            "note": f"CSV partition {period}; {source['native_row_count']} native rows, {source['observed_period_start']}–{source['observed_period_end']}; {source['missing_cell_count']} blank tenor cells retained. {parity_summary}"
        })
    crosswalk = trace["supplemental_source_record_crosswalk"]
    trace["supplemental_source_record_crosswalk"] = [row for row in crosswalk if row["source_release_record_id"] not in source_ids] + additions
    save(REGISTER, register)
    save(TRACE, trace)
    return {"source_records": register["record_count"], "supplemental": register["supplemental_source_records"],
            "groups": len(project["datasets"]), "groups_with_source_objects": trace["counts"]["registry_groups_with_source_objects"],
            "treasury_source_ids": source_ids, "receipt_run_id": run_id}


def load_normalized(path: Path):
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["observation_date", "TREASURY2Y", "TREASURY10Y", "TREASURY30Y"]:
            raise ValueError("Treasury normalized header changed")
        for row in reader:
            rows.append({"observation_date": date.fromisoformat(row["observation_date"]),
                         **{key: None if not row[key] else row[key] for key in ("TREASURY2Y", "TREASURY10Y", "TREASURY30Y")}})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(update(args.workspace, args.run_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
