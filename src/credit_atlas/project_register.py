"""Public-safe project progress and research-register projection.

The capability ledger remains authoritative for completion. The curated register
records dataset and method provenance, and never implies model qualification.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def project_register() -> dict:
    repo = Path(__file__).resolve().parents[2]
    ledger = _read_json(repo / "docs" / "COMPLETION_REQUIREMENTS_50.json")
    register = _read_json(repo / "docs" / "data" / "creditatlas-project-register-2026-10-17.json")
    source_register = _read_json(repo / "docs" / "data" / "creditatlas-source-release-register-2026-10-17.json")
    trace_map = _read_json(repo / "docs" / "data" / "n02-source-to-kpi-map-2026-10-17.json")
    requirements = ledger.get("requirements")
    if not isinstance(requirements, list) or len(requirements) != 50:
        raise ValueError("CreditAtlas capability ledger must contain exactly 50 requirements")
    ids = [row.get("id") for row in requirements]
    if len(set(ids)) != 50 or any(not isinstance(item, str) for item in ids):
        raise ValueError("CreditAtlas capability IDs must be unique strings")
    expected_prefixes = {f"P{domain}" for domain in range(1, 6)}
    if {item.split(".", 1)[0] for item in ids} != expected_prefixes:
        raise ValueError("CreditAtlas capability domains changed")
    counts = {prefix: sum(row["id"].startswith(prefix + ".") and row.get("full_completion_proven") is True
                          for row in requirements) for prefix in sorted(expected_prefixes)}
    totals = {prefix: sum(row["id"].startswith(prefix + ".") for row in requirements)
              for prefix in sorted(expected_prefixes)}
    gates = register.get("d01_release_gates")
    if [row.get("id") for row in gates or []] != ["R0", "R1", "R2", "R3", "R4"]:
        raise ValueError("D01 release register must preserve R0–R4")
    datasets, methods = register.get("datasets"), register.get("methods")
    if (not isinstance(datasets, list) or not datasets
            or any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in datasets)
            or len({row["id"] for row in datasets}) != len(datasets)):
        raise ValueError("Dataset registry must contain uniquely identified reviewed source groups")
    source_records = source_register.get("source_records")
    if (not isinstance(source_records, list) or not source_records
            or any(not isinstance(row, dict) or not isinstance(row.get("source_id"), str)
                   or not isinstance(row.get("publisher_publication_date"), (str, type(None)))
                   or not isinstance(row.get("retrieved_at_utc"), (str, type(None)))
                   for row in source_records)
            or len({row["source_id"] for row in source_records}) != len(source_records)):
        raise ValueError("Source release register must contain unique IDs and separate publication/retrieval fields")
    if source_register.get("record_count") != len(source_records):
        raise ValueError("Source release register count does not match its records")
    source_ids = {row["source_id"] for row in source_records}
    if not isinstance(methods, list) or len(methods) != 7 or len({row.get("id") for row in methods}) != len(methods):
        raise ValueError("Method registry must contain seven unique provenance types")
    method_cards = register.get("method_cards")
    if not isinstance(method_cards, list) or len(method_cards) < 8 or len({row.get("id") for row in method_cards}) != len(method_cards):
        raise ValueError("Method registry must contain concrete documented method cards")
    method_card_ids = {row["id"] for row in method_cards}
    dataset_ids = {row["id"] for row in datasets}
    if any(not set(row.get("datasets", [])).issubset(dataset_ids) for row in method_cards):
        raise ValueError("Method cards must reference registered dataset IDs")

    def validate_refs(rows, field, label, allowed_ids, *, singular=False):
        if not isinstance(rows, list):
            raise ValueError(f"{label} must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{label} rows must be objects")
            refs = row.get(field, [])
            if singular:
                refs = [] if refs is None else [refs]
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                raise ValueError(f"{label} source references must be string IDs")
            if missing := set(refs) - allowed_ids:
                raise ValueError(f"{label} references unknown IDs: {sorted(missing)}")

    validate_refs(datasets, "source_release_record_ids", "Dataset registry", source_ids)
    validate_refs(method_cards, "source_release_record_ids", "Method cards", source_ids)
    validate_refs(source_records, "method_card_ids", "Source release register", method_card_ids)
    validate_refs(source_records, "registry_group_id", "Source release register", dataset_ids, singular=True)
    validate_refs(trace_map.get("registered_record_trace"), "source_release_record_ids", "N02 registered-record trace", source_ids)
    validate_refs(trace_map.get("registered_record_trace"), "registry_id", "N02 registered-record trace", dataset_ids, singular=True)
    validate_refs(trace_map.get("supplemental_source_record_crosswalk"), "source_release_record_id", "N02 supplemental crosswalk", source_ids, singular=True)
    validate_refs(trace_map.get("registry_source_id_crosswalk"), "source_release_record_id", "N02 registry-source crosswalk", source_ids, singular=True)
    validate_refs(trace_map.get("registry_source_id_crosswalk"), "parent_registry_id", "N02 registry-source crosswalk", dataset_ids, singular=True)
    supplemental = trace_map.get("supplemental_source_record_crosswalk")
    if trace_map.get("source_release_register", {}).get("record_count") != len(source_records):
        raise ValueError("N02 source-release count does not match the source register")
    if trace_map.get("source_release_register", {}).get("supplemental_source_records") != len(supplemental):
        raise ValueError("N02 supplemental count does not match its crosswalk")
    dispositions = trace_map.get("source_group_dispositions")
    unbound_registry_ids = {
        row["registry_id"] for row in trace_map.get("registered_record_trace", [])
        if not row.get("source_release_record_ids")
    }
    if not isinstance(dispositions, list) or {
            row.get("registry_id") for row in dispositions if isinstance(row, dict)
    } != unbound_registry_ids:
        raise ValueError("N02 source-group dispositions must cover every unbound registry group exactly once")
    disposition_ids = [row.get("registry_id") for row in dispositions]
    if len(disposition_ids) != len(set(disposition_ids)):
        raise ValueError("N02 source-group disposition IDs must be unique")
    allowed_disposition_classes = {"source_data", "private_input", "derived_output", "access_pending"}
    for row in dispositions:
        if (row.get("classification") not in allowed_disposition_classes
                or not isinstance(row.get("data_state"), str)
                or not isinstance(row.get("formal_binding"), str)
                or not isinstance(row.get("evidence_refs"), list)
                or not row["evidence_refs"]
                or any(not isinstance(ref, str) for ref in row["evidence_refs"])):
            raise ValueError("N02 source-group dispositions require a classified state and evidence references")
    validate_refs(dispositions, "upstream_registry_ids", "N02 source-group dispositions", dataset_ids)
    disposition_counts = {
        "groups": len(dispositions),
        "private_source_or_input_present": sum(
            row["classification"] in {"source_data", "private_input"} for row in dispositions
        ),
        "derived_output_present": sum(row["classification"] == "derived_output" for row in dispositions),
        "access_pending_no_production": sum(row["classification"] == "access_pending" for row in dispositions),
    }
    disposition_metadata = trace_map.get("counts", {})
    expected_disposition_counts = {
        "groups": disposition_metadata.get("registry_groups_with_explicit_disposition"),
        "private_source_or_input_present": disposition_metadata.get("disposition_private_source_or_input_present"),
        "derived_output_present": disposition_metadata.get("disposition_derived_output_present"),
        "access_pending_no_production": disposition_metadata.get("disposition_access_pending_no_production"),
    }
    if disposition_counts != expected_disposition_counts:
        raise ValueError("N02 source-group disposition counts do not match the source-to-KPI map")
    return {
        "schema_version": 1,
        "as_of": register["as_of"],
        "scope_note": register["scope_note"],
        "current_plan_implementation": register["current_plan_implementation"],
        "source_group_dispositions": dispositions,
        "source_group_disposition_summary": disposition_counts,
        "progress": {
            "source_of_truth": "docs/COMPLETION_REQUIREMENTS_50.json",
            "completed": sum(counts.values()),
            "requirements": len(requirements),
            "fraction": sum(counts.values()) / len(requirements),
            "domains": [{"id": prefix, "completed": counts[prefix], "requirements": totals[prefix]}
                        for prefix in sorted(expected_prefixes)],
            "d01_release_gates": gates,
            "acceptance_note": "Completion flags represent the ledger scope only; additional intended-use, temporal and deployment qualifications remain described in the acceptance records.",
        },
        "datasets": datasets,
        "source_register_scope_note": source_register["scope_note"],
        "source_records": source_records,
        "methods": methods,
        "method_cards": method_cards,
        "capabilities": [{key: row[key] for key in
                          ("id", "title", "checkpoint_status", "full_completion_proven", "acceptance", "next")}
                         for row in requirements],
    }
