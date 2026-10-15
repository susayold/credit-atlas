"""Receipt-backed source declarations; acquisition dates are not publication dates."""
from __future__ import annotations

import re

from .workspace import contained, read_json, sha256


def report(service, query: dict) -> dict:
    if set(query) != {"run"}:
        raise ValueError("Mortgage provenance requires run only")
    case = service.case(query["run"])
    manifest = case["manifest"]
    foundation = read_json(case["path"] / "foundation-complete.json")
    digest = manifest["raw_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid source digest")
    if foundation["raw_sha256"] != digest:
        raise ValueError("Source lineage digest mismatch")
    receipt_path = contained(service.root, f"vendor/credit_risk_strategy_lab/data/private/raw/{digest}.receipt.json")
    receipt_hash = sha256(receipt_path)
    if receipt_hash != foundation["source_use_receipt_sha256"]:
        raise ValueError("Source-use receipt changed")
    receipt = read_json(receipt_path)
    source_path = contained(service.root, foundation["source_run"]) / "run-complete.json"
    if sha256(source_path) != foundation["source_manifest_sha256"]:
        raise ValueError("Source run receipt changed")
    source = read_json(source_path)
    if receipt["sha256"] != digest or source["source_sha256"] != digest:
        raise ValueError("Receipt source digest mismatch")
    if receipt["release"] != source["release"] or receipt["data_kind"] != source["data_kind"]:
        raise ValueError("Source declarations conflict")
    return {
        "schema_version": "mortgage-source-provenance-v1",
        "case_id": manifest["case_id"],
        "pipeline_run": manifest["pipeline_run"],
        "source_years": manifest["source_years"],
        "raw_sha256": digest,
        "source_use_receipt_sha256": receipt_hash,
        "source_run_receipt_sha256": foundation["source_manifest_sha256"],
        "receipt_declared_release": receipt["release"],
        "receipt_declared_data_kind": receipt["data_kind"],
        "release_confirmation": receipt.get("release_confirmation"),
        "publisher_release_authenticated": False,
        "publisher_publication_at": None,
        "research_use_declared": receipt.get("research_use_confirmed") is True,
        "receipt_received_at": receipt.get("received_at"),
        "extraction_started_at": source["started_at"],
        "extraction_completed_at": source["completed_at"],
        "foundation_completed_at": foundation["completed_at"],
        "case_completed_at": manifest["completed_at"],
        "visibility": "private",
        "public_release_approved": False,
        "population_scope": "Supplied annual sample; not the whole mortgage market",
        "limitations": [
            "Receipt declarations and byte lineage do not authenticate publisher release identity.",
            "Received/extraction/rebuild timestamps are not publisher publication timestamps.",
            "Research-use declaration is not independent verification of licensing or source fidelity.",
            "One supplied vintage does not qualify a multi-vintage out-of-time model.",
        ],
    }
