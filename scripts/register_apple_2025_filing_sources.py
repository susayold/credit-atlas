"""Bind the Apple FY2025 filing artifacts to their SEC accession.

Only public-safe provenance metadata is written to the public registers. The
private issuer-hosted payloads and full hashes remain in the sibling workspace.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = Path(os.environ.get("CREDIT_ATLAS_PRIVATE_ROOT", ROOT.parent / "credit-atlas")).resolve()
DOCS = ROOT / "docs"
SOURCE_REGISTER = DOCS / "data/creditatlas-source-release-register-2026-10-17.json"
PROJECT_REGISTER = DOCS / "data/creditatlas-project-register-2026-10-17.json"
TRACE_MAP = DOCS / "data/n02-source-to-kpi-map-2026-10-17.json"

SEC_INDEX = "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.html"
APPLE_FILINGS = "https://investor.apple.com/sec-filings/"
GROUP_ID = "sec-filings-financials"
ACCESSION = "0000320193-25-000079"
CIK = "0000320193"
FILING_ID = "18880179"
REPORT_END = "2025-09-27"
FILING_DATE = "2025-10-31"

OBJECTS = [
    {
        "source_id": "apple-2025-10k-issuer-html",
        "receipt": "data/private/sec-documents/apple-annual-debt-d2fac541f9a3/acquisition.json",
        "receipt_reference": "local-private-id:apple-annual-debt-d2fac541f9a3:acquisition",
        "filename": "apple-2025-10k.html",
        "format": "HTML",
        "kpi": "Filing-specific financial statements, debt maturity and source-linked issuer analysis.",
        "grain": "One issuer Form 10-K document; reporting period ended 2025-09-27.",
        "row_count": 1,
        "fact_count": None,
    },
    {
        "source_id": "apple-2025-xbrl-issuer-zip",
        "receipt": "data/private/sec-documents/apple-annual-xbrl-a596bfb03297/acquisition.json",
        "receipt_reference": "local-private-id:apple-annual-xbrl-a596bfb03297:acquisition",
        "filename": "apple-2025-xbrl.zip",
        "format": "ZIP (inline XBRL package)",
        "kpi": "As-filed XBRL fact dimensions supporting filing-specific financial/debt analysis.",
        "grain": "One issuer filing package; one instance and 155 profiled facts.",
        "row_count": None,
        "fact_count": 155,
    },
    {
        "source_id": "apple-2025-inline-xbrl-issuer-html",
        "receipt": "data/private/sec-documents/apple-annual-xbrl-a596bfb03297/inline-acquisition.json",
        "receipt_reference": "local-private-id:apple-annual-xbrl-a596bfb03297:inline-acquisition",
        "filename": "apple-2025-inline-xbrl.html",
        "format": "HTML (issuer-hosted inline XBRL rendering)",
        "kpi": "Rendered filing view used for cross-checking XBRL facts; not a separate filing or payment schedule.",
        "grain": "One issuer filing rendering, linked by issuer filing ID 18880179.",
        "row_count": 1,
        "fact_count": None,
    },
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source_register = read_json(SOURCE_REGISTER)
    project_register = read_json(PROJECT_REGISTER)
    trace_map = read_json(TRACE_MAP)
    records = []
    crosswalk = []

    for spec in OBJECTS:
        receipt_path = PRIVATE_ROOT / spec["receipt"]
        receipt = read_json(receipt_path)
        filing_id = receipt.get("issuer_filing_id")
        if (str(receipt.get("http_status")) != "200" or receipt.get("file") != spec["filename"]
                or receipt.get("cik", CIK) != CIK
                or receipt.get("accession", ACCESSION) != ACCESSION
                or filing_id not in (None, FILING_ID, int(FILING_ID))):
            raise ValueError(f"Unexpected filing identity in private receipt: {spec['source_id']}")
        artifact = receipt_path.parent / spec["filename"]
        if (not artifact.is_file() or artifact.stat().st_size != receipt["bytes"]
                or sha256(artifact) != receipt["sha256"]):
            raise ValueError(f"Private artifact does not match its acquisition receipt: {spec['source_id']}")

        digest = receipt["sha256"]
        retrieved = receipt["retrieved_at"]
        url = receipt["url"]
        record = {
            "source_id": spec["source_id"],
            "registry_group_id": GROUP_ID,
            "publisher": "Apple Inc. FY2025 Form 10-K filed with the U.S. Securities and Exchange Commission",
            "distributor": "Apple Investor Relations CloudFront; SEC EDGAR accession is the canonical filing crosswalk",
            "publisher_page_url": APPLE_FILINGS,
            "source_object_url": url,
            "format": spec["format"],
            "release_label": f"Apple FY2025 Form 10-K, accession {ACCESSION}; issuer-hosted artifact",
            "publisher_publication_date": FILING_DATE,
            "publication_date_status": "SEC EDGAR filing date 2025-10-31; fiscal reporting period ended 2025-09-27.",
            "snapshot_as_of": REPORT_END,
            "observed_period_start": None,
            "observed_period_end": REPORT_END,
            "native_row_count": spec["row_count"],
            "field_count": spec["fact_count"],
            "grain": spec["grain"],
            "modules": ["P3"],
            "consumer_trace": [
                "src/credit_atlas/sec_views.py",
                "P3 Issuer Financials workspace",
                "GET /api/sec-*",
                "GET /api/utility-debt-service",
            ],
            "kpi_or_output": spec["kpi"],
            "method_card_ids": [],
            "rights_use_gate": (
                "Filed report is publicly indexed by SEC EDGAR. The acquired bytes are issuer-hosted copies; raw local artifacts "
                "remain private, no public-release approval is recorded, and reuse/attribution/fair-access review remains required."
            ),
            "rights_review_status": "PUBLIC_FILING_CROSSWALKED; ISSUER_COPY_BYTE_PARITY_NOT_VERIFIED; RAW_PRIVATE; OUTPUT_REVIEW_OPEN",
            "receipt_status": "PASS: issuer-hosted artifact returned HTTP 200; local size and SHA-256 match its acquisition receipt; accession crosswalked to SEC EDGAR.",
            "retrieved_at_utc": retrieved,
            "receipt_completed_at_utc": retrieved,
            "receipt_reference": spec["receipt_reference"],
            "sha256_prefix": digest[:12],
            "missing_cell_count": None,
            "missing_cell_count_basis": "Not applicable at filing-object level; debt-series and payment-calendar coverage remain separately qualified.",
            "model_qualified_in_receipt": False,
            "public_release_approved_in_receipt": False,
            "file_profiles": [{
                "file": spec["filename"],
                "bytes": receipt["bytes"],
                "sha256_prefix": digest[:12],
                "cik": CIK,
                "sec_accession": ACCESSION,
                "issuer_filing_id": FILING_ID,
                "report_end": REPORT_END,
                "filing_date": FILING_DATE,
                **({"instance_count": receipt.get("instance_count"), "fact_count": receipt.get("fact_count")}
                   if spec["fact_count"] else {}),
            }],
            "scope_note": (
                f"Identity crosswalk: CIK {CIK}, accession {ACCESSION}, SEC EDGAR filing index {SEC_INDEX}. "
                "The SEC index lists the filed 10-K as aapl-20250927.htm (1,520,208 bytes) and its XBRL ZIP (399,390 bytes); "
                "issuer-hosted local copies have different byte sizes, so byte identity is explicitly unverified. "
                "The three records are artifacts of one filing, not three independent releases or a complete issuer panel."
            ),
            "cik": CIK,
            "sec_accession": ACCESSION,
            "issuer_filing_id": FILING_ID,
            "issuer_copy_byte_parity_verified": False,
            "canonical_sec_filing_index_url": SEC_INDEX,
        }
        records.append(record)
        crosswalk.append({
            "source_release_record_id": spec["source_id"],
            "publisher": record["publisher"],
            "source_id": spec["filename"],
            "source_family": "SEC EDGAR corporate issuer filings (Apple FY2025 10-K artifacts)",
            "current_use_status": "Receipt-bound issuer-hosted artifacts crosswalked to one SEC accession; raw payload private; full issuer panel and debt-service qualification remain open.",
            "note": f"CIK {CIK}; accession {ACCESSION}; report end {REPORT_END}; filing date {FILING_DATE}; byte parity to SEC-hosted copies not verified.",
        })

    ids = {row["source_id"] for row in records}
    source_register["source_records"] = [row for row in source_register["source_records"] if row["source_id"] not in ids] + records
    source_register["record_count"] = len(source_register["source_records"])
    source_register["supplemental_source_records"] = source_register["record_count"] - 20
    family_count = len({row["source_family"] for row in source_register["source_records"]
                        if row.get("source_family")})
    source_register["scope_note"] = (
        f"{source_register['record_count']} source records: 20 public-suite objects and "
        f"{source_register['record_count'] - 20} supplemental objects across {family_count} broad families, including "
        "receipt-bound SEC EDGAR auto-ABS filing sets and one Apple FY2025 10-K with three issuer-hosted artifacts. "
        "Concrete records stay edition/grain-specific; raw private payloads and full hashes are not published. "
        "Source registration does not by itself complete rights, route, debt-service, or capability acceptance."
    )

    crosswalk_rows = trace_map["supplemental_source_record_crosswalk"]
    crosswalk_rows = [row for row in crosswalk_rows if row["source_release_record_id"] not in ids] + crosswalk
    family_count = len({row["source_family"] for row in crosswalk_rows if row.get("source_family")})
    trace_map["supplemental_source_record_crosswalk"] = crosswalk_rows
    trace_map["source_release_register"].update({
        "record_count": len(source_register["source_records"]),
        "supplemental_source_records": len(crosswalk_rows),
        "supplemental_source_families": family_count,
        "note": (
            f"20 public-suite objects plus {len(crosswalk_rows)} supplemental objects across {family_count} broad families. "
            "The SEC EDGAR family includes 7 auto-ABS filing sets and one Apple FY2025 10-K with three issuer-hosted artifacts. "
            "Freddie 2012 is bound to a local private receipt but not publisher-authenticated. "
            "Publication, observation, received and retrieval dates remain distinct; raw private payloads and full hashes are not published."
        ),
    })

    dataset = next(row for row in project_register["datasets"] if row["id"] == GROUP_ID)
    dataset["source_release_record_ids"] = sorted(ids)
    dataset["status"] = "Selected issuer filing analysis; Apple FY2025 filing objects are receipt-bound to one SEC accession; not a complete as-filed panel."
    dataset["next"] = "Bind each additional issuer filing/amendment and map each KPI to accession, period, unit and availability date; finish the facility/payment evidence chain."
    trace = next(row for row in trace_map["registered_record_trace"] if row["registry_id"] == GROUP_ID)
    trace["source_release_record_ids"] = sorted(ids)
    trace["evidence_type"] = "receipt_bound_issuer_filing_artifacts_crosswalked_to_sec_edgar"
    trace["status_and_limits"] = (
        "Three receipt-verified Apple FY2025 issuer-hosted artifacts bind to CIK 0000320193 / accession 0000320193-25-000079. "
        "They are one filing, not a complete issuer panel; byte parity to SEC-hosted copies is not verified, and debt-service/payment qualification remains open."
    )
    trace_map["source_group_dispositions"] = [row for row in trace_map["source_group_dispositions"] if row["registry_id"] != GROUP_ID]

    exposure = next(row for row in project_register["datasets"] if row["id"] == "exposure-actual-2026-03")
    exposure.update({
        "name": "Freddie 2012 sample-derived exposure diagnostic",
        "grain": "Loan-month UPB sample observations; 9,804 February 2026 and 9,698 March 2026 records, not owned portfolio positions",
        "period": "Freddie 2012 sample observed through 2026-02 and 2026-03",
        "status": "Private cohort-derived UPB diagnostic; origin bound to Freddie 2012 sample; actual ownership is not evidenced",
        "use": "Sample-level UPB movement/concentration diagnostics only; not an actual lender book, EAD, PD or ECL",
        "next": "Keep private; rename legacy Actual labeling; require owner/source evidence, obligor identity and contract terms before actual-book or ECL analysis.",
        "publisher": "Freddie Mac sample, upstream local receipt-bound record; not an independently sourced portfolio",
        "rights_review": "Private; no redistribution approval; upstream Freddie release authentication and terms remain unresolved.",
    })
    exposure_disposition = next(row for row in trace_map["source_group_dispositions"] if row["registry_id"] == "exposure-actual-2026-03")
    exposure_disposition.update({
        "data_state": "PRIVATE_FREDDIE_SAMPLE_DERIVED_UPB_DIAGNOSTIC",
        "formal_binding": "upstream_freddie_sample_and_local_import_hashes_verified; ownership_and_actual_book_not_evidenced",
        "verified_facts": [
            "February 2026 and March 2026 private imports contain 9,804 and 9,698 loan-month sample UPB observations, respectively.",
            "Both imports identify Freddie-Mac-2012-annual-sample as their source namespace; each has four output hashes and 39/39 upstream lineage hashes matching local receipts.",
            "Rows carry reported UPB only; PD, LGD and EAD fields are blank. Position/observation keys and a Freddie sampling cohort do not establish lender ownership, borrower-group identity or a securitization pool.",
            "These imports are cohort-derived diagnostics, not independently evidenced actual portfolio holdings; keep private and do not present their amounts as owned exposure or ECL inputs."
        ],
        "next_action": "Rename the legacy Actual label to sample-derived UPB diagnostic; preserve Freddie source lineage and require an owner statement/source, portfolio keys and contractual terms before treating any future import as actual exposure.",
    })

    counts = trace_map["counts"]
    remaining = trace_map["source_group_dispositions"]
    group_count = len(project_register["datasets"])
    bound_groups = sum(bool(row.get("source_release_record_ids")) for row in trace_map["registered_record_trace"])
    counts.update({
        "source_level_records": len(crosswalk_rows),
        "supplemental_source_records": len(crosswalk_rows),
        "registry_groups_with_source_objects": bound_groups,
        "registry_groups_without_source_objects": group_count - bound_groups,
        "registry_groups_with_explicit_disposition": len(remaining),
        "disposition_private_source_or_input_present": sum(row["classification"] in {"source_data", "private_input"} for row in remaining),
        "disposition_derived_output_present": sum(row["classification"] == "derived_output" for row in remaining),
        "disposition_access_pending_no_production": sum(row["classification"] == "access_pending" for row in remaining),
    })
    project_register["source_group_disposition_summary"] = {
        "groups": counts["registry_groups_with_explicit_disposition"],
        "private_source_or_input_present": counts["disposition_private_source_or_input_present"],
        "derived_output_present": counts["disposition_derived_output_present"],
        "access_pending_no_production": counts["disposition_access_pending_no_production"],
    }
    trace_map["disposition_scope_note"] = (
        f"{len(remaining)} groups without standalone source objects remain explicitly classified: "
        f"{counts['disposition_private_source_or_input_present']} private source/input object(s), "
        f"{counts['disposition_derived_output_present']} derived outputs with upstream groups, and "
        f"{counts['disposition_access_pending_no_production']} access-pending group(s). The exposure input is now traced to the Freddie 2012 sample, "
        "but does not evidence owned portfolio positions. The Freddie source record remains publisher-unauthenticated. "
        f"This does not change {bound_groups}/{group_count} source-object coverage or the 26/50 capability ratio."
    )
    trace_map["scope_note"] = (
        f"N02 maps {group_count} parent groups to source/release evidence, receipts, code consumers, KPI scope and limits. "
        f"{bound_groups} groups have source-level objects, including one Apple FY2025 filing with three issuer-hosted artifacts "
        "crosswalked to a single SEC accession and one Freddie 2012 private cohort with publisher-authentication caveats. "
        f"The other {len(remaining)} groups have explicit dispositions; source status is not capability completion."
    )

    n02 = next(row for row in project_register["current_plan_implementation"] if row["id"] == "N02")
    n02["status"] = f"In progress: {len(source_register['source_records'])}-record source register; one Apple FY2025 filing bound through three issuer-hosted artifacts; Freddie release and terms unresolved."
    n02["scope"] = (
        f"{group_count} dataset/domain groups traced; {len(source_register['source_records'])} source records "
        f"(20 public-suite +{len(crosswalk_rows)} supplemental across {family_count} broad families); 7 SEC auto-ABS filing-set records plus three Apple artifacts for one accession. "
        f"{bound_groups}/{group_count} groups have source objects; {len(remaining)} retain explicit dispositions. Freddie 2012 remains local/private and release-unauthenticated. "
        "Apple issuer copy bytes are not identical in size to SEC-hosted objects, so byte parity remains unverified."
    )
    n02["remaining"] = (
        f"{len(remaining)} of {group_count} groups remain without standalone source objects: {counts['disposition_private_source_or_input_present']} private source/input, "
        f"{counts['disposition_derived_output_present']} derived outputs and {counts['disposition_access_pending_no_production']} Ginnie access-pending/no production. "
        "The exposure import is Freddie-sample-derived, not owned portfolio data. Continue filing-level KPI trace, route/UI/export parity, rights review and direct-source parity checks."
    )

    write_json(SOURCE_REGISTER, source_register)
    write_json(PROJECT_REGISTER, project_register)
    write_json(TRACE_MAP, trace_map)
    print(json.dumps({
        "new_source_ids": sorted(ids),
        "source_records": len(source_register["source_records"]),
        "supplemental_records": len(crosswalk_rows),
        "bound_groups": bound_groups,
        "remaining_dispositions": len(remaining),
        "exposure_lineage": "verified upstream; not owned portfolio",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
