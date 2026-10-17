"""Register receipt-backed SEC auto-ABS filing sets without reading raw loan rows.

The script reads acquisition-complete.json metadata from the sibling private
workspace and writes only source/receipt metadata to the public registers.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = Path(os.environ.get("CREDIT_ATLAS_PRIVATE_ROOT", ROOT.parent / "credit-atlas")).resolve()
SOURCE_REGISTER = ROOT / "docs/data/creditatlas-source-release-register-2026-10-17.json"
PROJECT_REGISTER = ROOT / "docs/data/creditatlas-project-register-2026-10-17.json"
TRACE_MAP = ROOT / "docs/data/n02-source-to-kpi-map-2026-10-17.json"

SOURCE_FAMILY = "SEC EDGAR auto ABS filing sets"
# The register groups fine-grained per-object source labels into broad families.
SUPPLEMENTAL_BROAD_FAMILY_COUNT = 17
CONFIGS = [
    {
        "source_id": "sec-toyota-2022b-abs-ee-history",
        "group_id": "toyota-2022b-absee",
        "receipt": "data/private/structured/toyota-2022b-absee-history-435918e7209a/acquisition-complete.json",
        "component": None,
        "form": "ABS-EE",
        "file_key": "xml",
        "attachment_description": "EX-102 asset data; supplementary EX-103 files are separately receipt-bound where acquired.",
    },
    {
        "source_id": "sec-toyota-2022b-10d-certificates",
        "group_id": "toyota-2022b-absee",
        "receipt": "data/private/structured/toyota-2022b-10d-certificates-941fa44791c8/acquisition-complete.json",
        "component": None,
        "form": "10-D",
        "file_key": "certificate",
        "attachment_description": "EX-99.1 certificate attachment; aggregate contractual comparator, not loan-level outcome data.",
    },
    {
        "source_id": "sec-toyota-2024b-abs-ee-history",
        "group_id": "toyota-2024b-absee",
        "receipt": "data/private/structured/toyota-2024b-validation-panel-5286fb3cae94/acquisition-complete.json",
        "component": "abs_ee",
        "form": "ABS-EE",
        "file_key": "ex102",
        "attachment_description": "EX-102 asset data, with the associated EX-103 explanatory attachment when present.",
    },
    {
        "source_id": "sec-toyota-2024b-10d-certificates",
        "group_id": "toyota-2024b-absee",
        "receipt": "data/private/structured/toyota-2024b-validation-panel-5286fb3cae94/acquisition-complete.json",
        "component": "10d",
        "form": "10-D",
        "file_key": "ex99_1",
        "attachment_description": "EX-99.1 certificate attachment; aggregate contractual comparator, not loan-level outcome data.",
    },
    {
        "source_id": "sec-nissan-2024b-abs-ee-history",
        "group_id": "nissan-2024b-absee",
        "receipt": "data/private/structured/nissan-2024b-validation-panel-7cd3605b4e07/acquisition-complete.json",
        "component": "abs_ee",
        "form": "ABS-EE",
        "file_key": "ex102",
        "attachment_description": "EX-102 asset data, with the associated EX-103 explanatory attachment when present.",
    },
    {
        "source_id": "sec-nissan-2024b-10d-certificates",
        "group_id": "nissan-2024b-absee",
        "receipt": "data/private/structured/nissan-2024b-validation-panel-7cd3605b4e07/acquisition-complete.json",
        "component": "10d",
        "form": "10-D",
        "file_key": "ex99_1",
        "attachment_description": "EX-99.1 certificate attachment; aggregate contractual comparator, not loan-level outcome data.",
    },
    {
        "source_id": "sec-woart-2025a-abs-ee-history",
        "group_id": "world-omni-2025a",
        "receipt": "data/private/structured/woart-absee-history-948a4d8e4f18/acquisition-complete.json",
        "component": None,
        "form": "ABS-EE",
        "file_key": "xml",
        "attachment_description": "EX-102 asset data; EX-103 and certificate filings remain separate source objects when acquired.",
    },
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def utc_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def accession_from_index(index_url: str | None) -> str | None:
    if not index_url:
        return None
    parts = [part for part in urlparse(index_url).path.split("/") if part]
    if len(parts) < 2:
        return None
    accession = parts[-2]
    return accession if accession.isdigit() else None


def extract_component(report: dict, config: dict) -> tuple[dict, dict | None, list[dict]]:
    component_key = config["component"]
    if component_key:
        component = report.get(component_key)
        if not isinstance(component, dict):
            raise ValueError(f"Missing {component_key} component in {config['source_id']}")
        index = component.get("index")
        payloads = [value for key, value in component.items()
                    if key in {config["file_key"], "ex103"} and isinstance(value, dict)]
        return component, index, payloads

    index = report.get("index")
    payload = report.get(config["file_key"])
    return report, index, [payload] if isinstance(payload, dict) else []


def build_record(config: dict) -> tuple[dict, dict]:
    receipt_path = PRIVATE_ROOT / config["receipt"]
    if not receipt_path.is_file():
        raise FileNotFoundError(f"Missing private metadata receipt: {receipt_path}")
    receipt = read_json(receipt_path)
    reports = receipt.get("reports")
    if not isinstance(reports, list) or not reports:
        raise ValueError(f"No report records in {config['source_id']}")
    if receipt.get("public_release_approved") is not False:
        raise ValueError(f"Raw-source release fence changed for {config['source_id']}; stop and review")

    normalized = []
    for report in reports:
        component, index, payloads = extract_component(report, config)
        if not index or not index.get("url"):
            raise ValueError(f"Missing SEC index URL in {config['source_id']}")
        statuses = [index.get("http_status")]
        statuses.extend(payload.get("http_status") for payload in payloads)
        if any(status not in (None, 200) for status in statuses):
            raise ValueError(f"Non-200 SEC attachment in {config['source_id']}")
        report_date = report.get("report_date")
        filing_date = component.get("filing_date") or report.get("filing_date")
        if not report_date:
            raise ValueError(f"Missing report date in {config['source_id']}")
        normalized.append({
            "report_date": report_date,
            "filing_date": filing_date,
            "accession": component.get("accession") or report.get("accession") or accession_from_index(index["url"]),
        })

    report_dates = sorted(row["report_date"] for row in normalized)
    filing_dates = sorted(row["filing_date"] for row in normalized if row["filing_date"])
    accessions = [row["accession"] for row in normalized if row["accession"]]
    if len(normalized) != receipt.get("period_count"):
        raise ValueError(f"Period count does not match report set in {config['source_id']}")

    issuer = receipt.get("issuer")
    cik = str(receipt.get("cik", "")).zfill(10)
    if not issuer or not cik.isdigit() or len(cik) != 10:
        raise ValueError(f"Missing issuer/CIK in {config['source_id']}")
    as_of = report_dates[-1]
    filing_count = len(normalized)
    attachment_types = [config["file_key"].upper()]
    if config["form"] == "ABS-EE":
        attachment_types = ["EX-102", "EX-103 where separately filed"]
    elif config["form"] == "10-D":
        attachment_types = ["EX-99.1 certificate"]

    retrieved = utc_timestamp(receipt["acquired_at"])
    receipt_id = receipt_path.parent.name
    report_start, report_end = report_dates[0], report_dates[-1]
    filing_span = f"{filing_dates[0]}–{filing_dates[-1]}" if filing_dates else "not recorded"
    if config["form"] == "ABS-EE":
        grain = "Issuing trust × monthly report date × Form ABS-EE asset-data filing; EX-102 is the asset-data attachment, with EX-103 explanatory disclosure where filed."
        output = "Deal-level pool, delinquency, charge-off and recovery source observations for surveillance and validation; not a consumer-loan origination PD label."
    else:
        grain = "Issuing trust × monthly report date × Form 10-D certificate/distribution filing; certificate amounts are aggregate deal comparators."
        output = "Certificate comparator for deal-specific balance, delinquency, charge-off and recovery tie-outs; not a loan-level outcome dataset."

    source_record = {
        "source_id": config["source_id"],
        "registry_group_id": config["group_id"],
        "publisher": issuer,
        "distributor": "U.S. Securities and Exchange Commission — EDGAR",
        "publisher_page_url": f"https://www.sec.gov/edgar/browse/?CIK={cik}&owner=exclude",
        "source_object_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
        "format": f"{filing_count} monthly {config['form']} filings; " + ", ".join(attachment_types),
        "release_label": f"{issuer} {config['form']} filing set, report dates {report_start}–{report_end}",
        "publisher_publication_date": None,
        "publication_date_status": f"The set contains individual report and filing dates; filing-date span {filing_span}. See accession-specific URLs in the local acquisition receipt.",
        "snapshot_as_of": as_of,
        "observed_period_start": report_start,
        "observed_period_end": report_end,
        "observed_period_label": f"{filing_count} monthly report dates; {config['form']} filings retrieved {retrieved}.",
        "native_row_count": None,
        "field_count": None,
        "grain": grain,
        "modules": ["P5"],
        "consumer_trace": [
            "src/credit_atlas/absee_profile.py",
            "src/credit_atlas/absee_surveillance.py",
            "src/credit_atlas/abs_views.py",
            "GET /api/absee-profile",
            "GET /api/absee-surveillance",
            "docs/ABS_APP_WORKFLOW.md",
        ],
        "kpi_or_output": output,
        "method_card_ids": [],
        "rights_use_gate": "Official filing links are listed for provenance. Raw SEC payloads remain in local private storage and are not approved for redistribution; review source and depositor terms before bundling or wider use.",
        "rights_review_status": "SOURCE_LINKED_RAW_PAYLOAD_PRIVATE_REVIEW_REQUIRED",
        "receipt_status": f"PASS: {filing_count} {config['form']} report-period records; constituent accession and attachment hashes are retained only in the local private receipt.",
        "retrieved_at_utc": retrieved,
        "receipt_completed_at_utc": retrieved,
        "receipt_reference": f"local-private-id:{receipt_id}:acquisition-complete",
        "sha256_prefix": None,
        "missing_cell_count": None,
        "missing_cell_count_basis": "Not profiled at filing-set level; missingness must be measured in a separately scoped parser audit.",
        "model_qualified_in_receipt": False,
        "public_release_approved_in_receipt": False,
        "file_profiles": [{
            "file": "private SEC filing set; constituent files are not bundled",
            "filing_form": config["form"],
            "report_count": filing_count,
            "accession_count": len(set(accessions)),
            "report_date_start": report_start,
            "report_date_end": report_end,
            "filing_date_start": filing_dates[0] if filing_dates else None,
            "filing_date_end": filing_dates[-1] if filing_dates else None,
            "attachment_types": attachment_types,
        }],
        "scope_note": f"This record describes a receipt-backed SEC filing set, not a redistributed dataset. Individual accessions, URLs, attachment hashes and downloaded payloads remain in local private evidence ID {receipt_id}. EX-102/EX-103 asset data and 10-D certificate comparators remain separate. No cross-deal summation, forecast or imputation is implied.",
    }
    crosswalk = {
        "source_release_record_id": config["source_id"],
        "publisher": issuer,
        "distributor": "U.S. Securities and Exchange Commission — EDGAR",
        "source_id": config["source_id"],
        "source_family": SOURCE_FAMILY,
        "current_use_status": "Receipt-bound private source set; public register exposes provenance metadata only, not raw payloads.",
        "note": f"{config['form']} report-date range {report_start}–{report_end}; {filing_count} periods; local receipt holds individual accessions/hashes. {config['attachment_description']}",
    }
    return source_record, crosswalk


def main() -> None:
    source_register = read_json(SOURCE_REGISTER)
    project_register = read_json(PROJECT_REGISTER)
    trace_map = read_json(TRACE_MAP)
    records = [build_record(config) for config in CONFIGS]
    new_records = [record for record, _ in records]
    new_crosswalk = [crosswalk for _, crosswalk in records]
    new_ids = {row["source_id"] for row in new_records}

    old_ids = {row["source_id"] for row in source_register["source_records"]}
    source_register["source_records"] = [row for row in source_register["source_records"] if row["source_id"] not in new_ids]
    source_register["source_records"].extend(new_records)
    source_register["record_count"] = len(source_register["source_records"])
    source_register["supplemental_source_records"] = source_register["record_count"] - 20
    source_register["scope_note"] = (
        f"{source_register['record_count']} source records: 20 public-suite objects and "
        f"{source_register['record_count'] - 20} supplemental objects across 17 broad source families, "
        "including receipt-bound SEC EDGAR auto-ABS filing sets and one Apple FY2025 10-K with three issuer-hosted artifacts. "
        "Concrete records stay edition/grain-specific. "
        "This register binds source provenance and does not by itself complete rights, route, or capability acceptance."
    )

    supplemental = trace_map["supplemental_source_record_crosswalk"]
    supplemental = [row for row in supplemental if row["source_release_record_id"] not in new_ids]
    supplemental.extend(new_crosswalk)
    trace_map["supplemental_source_record_crosswalk"] = supplemental
    trace_map["source_release_register"]["record_count"] = len(source_register["source_records"])
    trace_map["source_release_register"]["supplemental_source_records"] = len(supplemental)
    trace_map["source_release_register"]["supplemental_source_families"] = SUPPLEMENTAL_BROAD_FAMILY_COUNT
    trace_map["source_release_register"]["note"] = (
        f"20 public-suite objects plus {len(supplemental)} supplemental source objects across "
        f"{SUPPLEMENTAL_BROAD_FAMILY_COUNT} broad families. "
        "This includes 22 World Bank WDI objects, 12 HMDA files, 9 FHFA PUDB/NMDB/NSMO objects, "
        "5 LendingClub/Bondora objects, 22 Treasury HAMP objects, 12 BoC–BoE Sovereign Archive objects, "
        "7 receipt-bound SEC auto-ABS filing sets, three issuer-hosted artifacts for one Apple FY2025 SEC accession, "
        "one private Freddie 2012 cohort bound to a local receipt "
        "but not publisher-authenticated, and separate HUD/Fed/FHFA/Fannie records. Publication, observation, "
        "received and retrieval dates remain distinct; raw private payloads and full hashes are not published."
    )

    dataset_ids = {row["id"] for row in project_register["datasets"]}
    grouped_ids: dict[str, list[str]] = {}
    for row in new_records:
        grouped_ids.setdefault(row["registry_group_id"], []).append(row["source_id"])
    for group_id, source_ids in grouped_ids.items():
        if group_id not in dataset_ids:
            raise ValueError(f"Unknown dataset group {group_id}")
        dataset = next(row for row in project_register["datasets"] if row["id"] == group_id)
        dataset["source_release_record_ids"] = source_ids
        trace = next(row for row in trace_map["registered_record_trace"] if row["registry_id"] == group_id)
        trace["source_release_record_ids"] = source_ids
        trace["evidence_type"] = "receipt_bound_SEC_filing_set_and_static_code_trace"
        trace["status_and_limits"] += " Formal SEC filing-set records now bind each deal's ABS-EE data and 10-D certificate source objects; raw payloads remain private and outcome/LGD qualification stays limited."

    bound_groups = set(grouped_ids)
    trace_map["source_group_dispositions"] = [
        row for row in trace_map["source_group_dispositions"] if row["registry_id"] not in bound_groups
    ]
    remaining = trace_map["source_group_dispositions"]
    trace_map["counts"].update({
        "source_level_records": len(supplemental),
        "supplemental_source_records": len(supplemental),
        "registry_groups_with_source_objects": len({row["registry_id"] for row in trace_map["registered_record_trace"] if row.get("source_release_record_ids")}),
        "registry_groups_without_source_objects": sum(not row.get("source_release_record_ids") for row in trace_map["registered_record_trace"]),
        "registry_groups_with_explicit_disposition": len(remaining),
        "disposition_private_source_or_input_present": sum(row["classification"] in {"source_data", "private_input"} for row in remaining),
        "disposition_derived_output_present": sum(row["classification"] == "derived_output" for row in remaining),
        "disposition_access_pending_no_production": sum(row["classification"] == "access_pending" for row in remaining),
    })
    project_register["source_group_disposition_summary"] = {
        "groups": trace_map["counts"]["registry_groups_with_explicit_disposition"],
        "private_source_or_input_present": trace_map["counts"]["disposition_private_source_or_input_present"],
        "derived_output_present": trace_map["counts"]["disposition_derived_output_present"],
        "access_pending_no_production": trace_map["counts"]["disposition_access_pending_no_production"],
    }
    private_count = trace_map["counts"]["disposition_private_source_or_input_present"]
    derived_count = trace_map["counts"]["disposition_derived_output_present"]
    pending_count = trace_map["counts"]["disposition_access_pending_no_production"]
    bound_count = trace_map["counts"]["registry_groups_with_source_objects"]
    group_count = len(project_register["datasets"])
    remaining_count = len(remaining)
    trace_map["disposition_scope_note"] = (
        f"{remaining_count} groups without bound source objects remain explicitly classified: "
        f"{private_count} private source/input objects, {derived_count} derived aggregate outputs with upstream groups, "
        f"and {pending_count} access-pending group(s) with no production data. The Freddie 2012 user-supplied cohort "
        "is bound to a local receipt and exact private archive hash, but its declared publisher release is not authenticated. "
        f"This status coverage does not change the {bound_count}/{group_count} source-object binding count or the 26/50 capability "
        "completion ratio. Opaque local-private evidence IDs resolve only in the private D: workspace; no private receipt "
        "paths, raw rows or full hashes are published."
    )
    trace_map["scope_note"] = (
        f"N02 review maps {group_count} parent dataset groups and records concrete source objects, local receipt IDs, code consumers, "
        "KPI scope and limitations. "
        f"{bound_count} groups have source-level objects bound, including one private user-supplied Freddie cohort with "
        "explicit publisher-authentication and terms caveats. The remaining "
        f"{remaining_count} are explicitly classified ({private_count} private source/input objects, {derived_count} derived "
        f"outputs, {pending_count} publisher-access pending); source status is not capability completion."
    )

    project_register["scope_note"] = re.sub(
        r"Source-release register has \d+ records \(20 public-suite \+\d+ supplemental across \d+ broad families\)",
        f"Source-release register has {len(source_register['source_records'])} records "
        f"(20 public-suite +{len(supplemental)} supplemental across {SUPPLEMENTAL_BROAD_FAMILY_COUNT} broad families)",
        project_register["scope_note"],
    )
    project_register["scope_note"] = re.sub(
        r"(?:Sixteen|Twenty|Twenty-one|Twenty-two) parent groups have source-level records\.",
        f"{bound_count} parent groups have source-level records.",
        project_register["scope_note"],
    )
    n02 = next(row for row in project_register["current_plan_implementation"] if row["id"] == "N02")
    n02["status"] = (
        f"In progress: {len(source_register['source_records'])}-record source-release register; "
        "7 receipt-backed SEC auto-ABS filing-set records and three Apple FY2025 issuer-hosted artifacts for one accession; "
        "plus private Freddie 2012 receipt/hash binding; "
        "Freddie publisher authentication and terms remain unresolved."
    )
    n02["scope"] = (
        f"{group_count} dataset/domain groups statically traced; all 20 public_sources.catalog IDs match local receipt. "
        f"Source-release register has {len(source_register['source_records'])} records "
        f"(20 public-suite +{len(supplemental)} supplemental across {SUPPLEMENTAL_BROAD_FAMILY_COUNT} broad families). "
        "The private Freddie 2012 cohort is bound to a local archive hash/receipt: 50,000 origination loans and "
        "4,510,559 monthly performance rows through 2026-03. The receipt declares Release 47 and research use but says "
        "publisher release is not authenticated; exact dataset terms remain unverified and raw data remain private. "
        "Seven receipt-backed SEC filing-set records cover Toyota 2022-B (51 ABS-EE +51 10-D periods), "
        "Toyota 2024-B (29+29), Nissan 2024-B (23+23), and World Omni 2025-A (20 ABS-EE). "
        "Three Apple FY2025 issuer-hosted artifacts bind to one SEC accession; byte parity to SEC-hosted copies is not verified. "
        f"{bound_count} of {group_count} parent groups have source-object records; {remaining_count} remain explicitly classified "
        f"({private_count} private source/input, {derived_count} derived outputs, {pending_count} Ginnie access-pending/no production)."
    )
    n02["remaining"] = (
        f"{remaining_count} of {group_count} parent groups remain without bound source objects: {private_count} private source/input "
        f"groups, {derived_count} derived outputs with upstream links, and {pending_count} Ginnie production access-pending; "
        "FRED/ALFRED macro-market parent binding is present but owner/distributor rights and direct-source parity remain open. For Freddie, release authenticity, original download channel, cutoff evidence "
        "and dataset-specific terms remain open; keep 2012 descriptive/private and acquire later vintages only through "
        "authorized Clarity access. Finish source-specific API/UI/Excel parity, remaining KPI formula links and rights review. "
        "HAMP activity gaps remain unexplained; do not forecast or impute. WDI and Sovereign Archive remain context, not "
        "retail/corporate PD or LGD. HUD Table 2 PDF binary returned HTTP 403; report-specific third-party notices remain uninspected."
    )

    write_json(SOURCE_REGISTER, source_register)
    write_json(PROJECT_REGISTER, project_register)
    write_json(TRACE_MAP, trace_map)
    print(json.dumps({
        "source_records": len(source_register["source_records"]),
        "supplemental_records": len(supplemental),
        "new_record_ids": sorted(new_ids),
        "formal_groups": trace_map["counts"]["registry_groups_with_source_objects"],
        "remaining_dispositions": len(remaining),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
