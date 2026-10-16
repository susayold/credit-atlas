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
    if not isinstance(datasets, list) or len(datasets) != 24 or len({row.get("id") for row in datasets}) != len(datasets):
        raise ValueError("Dataset registry must contain 24 unique reviewed source groups")
    if not isinstance(methods, list) or len(methods) != 7 or len({row.get("id") for row in methods}) != len(methods):
        raise ValueError("Method registry must contain seven unique provenance types")
    method_cards = register.get("method_cards")
    if not isinstance(method_cards, list) or len(method_cards) < 8 or len({row.get("id") for row in method_cards}) != len(method_cards):
        raise ValueError("Method registry must contain concrete documented method cards")
    dataset_ids = {row["id"] for row in datasets}
    if any(not set(row.get("datasets", [])).issubset(dataset_ids) for row in method_cards):
        raise ValueError("Method cards must reference registered dataset IDs")
    return {
        "schema_version": 1,
        "as_of": register["as_of"],
        "scope_note": register["scope_note"],
        "current_plan_implementation": register["current_plan_implementation"],
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
        "methods": methods,
        "method_cards": method_cards,
        "capabilities": [{key: row[key] for key in
                          ("id", "title", "checkpoint_status", "full_completion_proven", "acceptance", "next")}
                         for row in requirements],
    }
