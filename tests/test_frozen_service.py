"""Independent small synthetic contracts exercise private serving boundaries."""
import copy
import json
import os

import pytest

from credit_atlas import service
from credit_atlas.snapshot import TARGET
from credit_atlas.workspace import contained, sha256, write_new


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "load_engine", lambda root: {"commit": "SYNTHETIC-QA"})
    case_id = "d01-0123456789ab"
    case = tmp_path / "artifacts/private" / case_id
    case.mkdir(parents=True)
    monthly = [{"period": "2020-01-01", "loans": 3}, {"period": "2020-02-01", "loans": 2}]
    snapshot = {"case_id": case_id, "pipeline_run": "SYNTHETIC-pipeline",
                "target": TARGET, "visibility": "private", "snapshot": {"monthly": monthly, "loans": 3},
                "source_quality": {"technical_profile": {
                    "duplicate_origination_keys": 0, "duplicate_monthly_keys": 0,
                    "orphan_performance_rows": 0, "loans_without_performance": 0, "loans_with_gaps": 0},
                    "canonical_missing_counts": {"classic_fico": 0}},
                "model_readiness": {"actual_model_fit": False, "missing_years": [2014],
                                    "blocking_reasons": ["missing_required_vintages"]},
                "monthly_by_segment": {"relief": [{"period": "2020-02-01", "loans": 1}]},
                "segment_outcomes": [{"segment": "relief", "outcome": "d3_event", "loans": 1}]}
    report = {"pipeline_run": "SYNTHETIC-pipeline", "tables": [
        {"table_id": "portfolio_monthly", "rows": monthly},
        {"table_id": "state_transitions", "rows": [{"pairs": 9}]},
        {"table_id": "observed_loss_summary", "rows": [{"reported_loss": 13}]},
        {"table_id": "vintage_competing_risk", "rows": [
            {"segment": "relief", "observation_age": 12, "events": 1},
            {"segment": "relief", "observation_age": 24, "events": 2}]},
        {"table_id": "label_outcomes", "rows": [{"outcome": "d3_event", "loans": 2}]}]}
    write_new(case / "snapshot.json", snapshot)
    write_new(case / "report.json", report)
    (case / "loan-index.parquet").write_bytes(b"SYNTHETIC-QA-NOT-USED-AS-PARQUET")
    write_new(case / "foundation-complete.json", {"source_kind": "SYNTHETIC-QA"})
    manifest = {"status": "D01_DESCRIPTIVE_COMPLETE", "visibility": "private",
                "case_id": case_id, "target_version": TARGET["version"],
                "public_release_approved": False, "engine_commit": "SYNTHETIC-QA",
                "pipeline_run": "SYNTHETIC-pipeline", "verified_inputs": [],
                "outputs_sha256": {n: sha256(case / n) for n in
                                  ["snapshot.json", "report.json", "loan-index.parquet", "foundation-complete.json"]}}
    write_new(case / "case-complete.json", manifest)
    api = service.ResearchService(tmp_path)
    # Synthetic saved episode aggregate stands in for real panel queries.
    monkeypatch.setattr(api, "episode_followup", lambda identifier: {
        "case_id": identifier, "pipeline_run": "SYNTHETIC-pipeline", "method_version": "SYNTHETIC-QA",
        "rows": [{"segment": segment, "horizon_months": horizon, "events": 1}
                 for segment in ("all", "relief", "non_relief") for horizon in (6, 12)]})
    monkeypatch.setattr(api, "period_transitions", lambda identifier: {
        "case_id": identifier, "pipeline_run": "SYNTHETIC-pipeline", "method_version": "SYNTHETIC-QA",
        "rows": [{"segment": segment, "reporting_year": year, "pairs": 1}
                 for segment in ("all", "relief", "non_relief") for year in (2020, 2021)],
        "lifetime_rows": [{"segment": segment, "pairs": 2} for segment in ("all", "relief", "non_relief")]})
    return api, case_id, case


def test_export_applies_only_supported_filters_without_mutating_frozen_case(frozen):
    api, identifier, _ = frozen
    original = copy.deepcopy(api.case(identifier)["report"])
    result = api.report(identifier, {"segment": "relief", "from": "2020-02", "to": "2020-02", "horizon": "24"})
    tables = {t["table_id"]: t for t in result["report"]["tables"]}
    assert tables["portfolio_monthly"]["rows"] == [{"period": "2020-02-01", "loans": 1}]
    assert tables["vintage_competing_risk"]["rows"] == [{"segment": "relief", "observation_age": 24, "events": 2}]
    assert tables["state_transitions"]["rows"] == []
    assert tables["observed_loss_summary"]["rows"] == [{"reported_loss": 13}]
    assert tables["observed_loss_summary"]["filters_applied"] == []
    assert result["scope_notes"]["loss"].startswith("Whole-sample")
    assert result["public_release_approved"] is False
    assert result["schema_version"] == 2
    support = result["supplemental_evidence"]["episode_followup"]
    assert {r["segment"] for r in support["rows"]} == {"relief"}
    assert {r["horizon_months"] for r in support["rows"]} == {6, 12}
    assert result["supplemental_evidence"]["quality_monitoring"]["filters_applied"] == []
    assert result == api.report(identifier, {"segment": "relief", "from": "2020-02", "to": "2020-02", "horizon": "24"})
    assert api.case(identifier)["report"] == original


@pytest.mark.parametrize("query", [
    {"metric": "pd12"}, {"use": "ECL"}, {"cash_flow": "expected"},
    {"run": "d01-aaaaaaaaaaaa"},
])
def test_report_rejects_unsupported_uses_and_wrong_run_scope(frozen, query):
    api, identifier, _ = frozen
    with pytest.raises(ValueError, match="Unsupported report parameter|must match"):
        api.report(identifier, query)


def test_supplemental_evidence_from_another_pipeline_cannot_be_exported(frozen, monkeypatch):
    api, identifier, _ = frozen
    original = api.episode_followup(identifier)
    original["pipeline_run"] = "OTHER-PIPELINE"
    monkeypatch.setattr(api, "episode_followup", lambda case_id: original)
    with pytest.raises(ValueError, match="Supplemental"):
        api.report(identifier, {})

def test_year_export_retains_explicit_lifetime_comparator_and_does_not_filter_episodes(frozen):
    api, identifier, _ = frozen
    package = api.report(identifier, {"segment": "relief", "transition_year": "2021"})
    periods = package["supplemental_evidence"]["period_transitions"]
    assert periods["rows"] == [{"segment": "relief", "reporting_year": 2021, "pairs": 1}]
    assert periods["lifetime_rows"] == [{"segment": "relief", "pairs": 2}]
    assert periods["filters_applied"] == ["segment", "transition_year"]
    assert len(package["supplemental_evidence"]["episode_followup"]["rows"]) == 2
    empty = api.report(identifier, {"transition_year": "2019"})["supplemental_evidence"]["period_transitions"]
    assert empty["rows"] == [] and empty["lifetime_rows"]


def test_tampered_contract_with_preserved_file_metadata_is_rejected(frozen):
    api, identifier, case = frozen
    api.case(identifier)
    file = case / "snapshot.json"
    stat = file.stat()
    data = file.read_bytes()
    assert b'"loans": 3' in data
    file.write_bytes(data.replace(b'"loans": 3', b'"loans": 9'))
    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(service.EvidenceChanged):
        api.snapshot(identifier)


def test_wrong_pipeline_is_rejected_even_with_updated_digest(frozen):
    api, identifier, case = frozen
    file = case / "report.json"
    report = json.loads(file.read_text())
    report["pipeline_run"] = "another-case"
    file.write_text(json.dumps(report), encoding="utf-8")
    receipt_path = case / "case-complete.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["outputs_sha256"]["report.json"] = sha256(file)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="lineage"):
        api.case(identifier)


def test_snapshot_callers_cannot_change_served_frozen_state(frozen):
    api, identifier, _ = frozen
    returned = api.snapshot(identifier)
    returned["target"]["version"] = "wrong"
    assert api.snapshot(identifier)["target"] == TARGET


def test_changed_serving_method_cannot_claim_previous_export_provenance(frozen, tmp_path):
    api, identifier, _ = frozen
    method = tmp_path / "SYNTHETIC-serving-method.py"
    method.write_text("# SYNTHETIC version one", encoding="utf-8")
    api.method_sources["synthetic_method"] = {"path": method, "sha256": sha256(method)}
    api.snapshot(identifier)
    method.write_text("# SYNTHETIC version two", encoding="utf-8")
    with pytest.raises(service.EvidenceChanged, match="Serving method"):
        api.report(identifier, {})


def test_cross_case_receipt_and_missing_private_digest_are_rejected(frozen):
    api, identifier, case = frozen
    path = case / "case-complete.json"
    manifest = json.loads(path.read_text())
    manifest["case_id"] = "d01-aaaaaaaaaaaa"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        api.case(identifier)
    manifest["case_id"] = identifier
    del manifest["outputs_sha256"]["loan-index.parquet"]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="digests"):
        api.case(identifier)


def test_workspace_boundary_and_review_storage_reject_escape(frozen, tmp_path):
    api, _, _ = frozen
    with pytest.raises(ValueError):
        contained(tmp_path, "../outside.json")
    with pytest.raises(ValueError):
        service.ResearchService(api.root, review_path=tmp_path / "public/reviews.sqlite3")


@pytest.mark.parametrize("query", [
    {"segment": "invented"}, {"basis": "original_upb"}, {"horizon": "18"},
    {"from": "2020-13"}, {"from": "2020-03", "to": "2020-02"},
    {"transition_year": "2020-01"}, {"transition_year": "all; DROP TABLE"}, {"transition_year": 2020},
])
def test_invalid_filters_do_not_silently_change_research_scope(query):
    with pytest.raises(ValueError):
        service.filters_from(query)
