import hashlib
import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.nsmo_views import NsmoViews
from credit_atlas.server import handler_for


def _workspace(root: Path) -> Path:
    csv = root / "data/private/mortgage/nsmo-2026-05-27/puf/nsmo_v70_1324_puf.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text(
        "nsmoid,analysis_weight,perf_status_0313,perf_status_0613\n"
        "private-a,10,P,C\nprivate-b,20,C,1\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    receipts = root / "artifacts/private/nsmo-puf-20261015"
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "download-receipt.json").write_text(json.dumps({
        "dataset_release": "NSMO Public Use File v7.0, page updated 2026-05-27",
        "csv_sha256": digest,
        "csv_bytes": csv.stat().st_size,
    }), encoding="utf-8")
    (receipts / "data-audit.json").write_text(json.dumps({
        "status": "PASS",
        "csv_sha256": digest,
        "csv_bytes": csv.stat().st_size,
        "column_count": 4,
        "row_count": 2,
        "unique_nonblank_nsmoid": 2,
        "duplicate_nsmoid_rows": 0,
        "blank_nsmoid_rows": 0,
        "bad_width_rows": 0,
        "origination_year_counts": {"2013": 2},
        "origination_month_counts": {"1": 1, "2": 1},
        "survey_wave_counts": {"1": 2},
        "analysis_weight": {
            "valid_n": 2, "missing": 0, "invalid": 0, "nonpositive": 0,
            "min": 10, "median": 15, "max": 20, "sum": 30,
        },
        "performance": {
            "column_count": 2,
            "first_quarter_end": "2013-03-31",
            "last_quarter_end": "2013-06-30",
            "cell_count": 4,
            "unknown_status_counts": {},
            "quarterly_counts": [
                {
                    "quarter_end": "2013-03-31",
                    "status_counts_unweighted": {"P": 1, "C": 1},
                    "status_weight_sums_descriptive_only": {"P": 10, "C": 20},
                },
                {
                    "quarter_end": "2013-06-30",
                    "status_counts_unweighted": {"C": 1, "1": 1},
                    "status_weight_sums_descriptive_only": {"C": 10, "1": 20},
                },
            ],
        },
    }), encoding="utf-8")
    return csv


def test_nsmo_profile_is_hash_bound_and_aggregate_only(tmp_path):
    _workspace(tmp_path)
    result = NsmoViews(tmp_path).report()

    assert result["schema_version"] == "nsmo-profile-v1"
    assert result["sample"]["mortgages"] == 2
    assert result["performance"]["cell_count"] == 4
    assert result["performance"]["quarterly_counts"][0]["status_counts"] == {"P": 1, "C": 1}
    assert "private-a" not in json.dumps(result)
    assert "private-b" not in json.dumps(result)
    assert "at-risk denominator" in " ".join(result["limitations"])


def test_nsmo_profile_rejects_changed_source_even_with_cached_view(tmp_path):
    csv = _workspace(tmp_path)
    views = NsmoViews(tmp_path)
    views.report()
    old = csv.read_text(encoding="utf-8")
    csv.write_text(old.replace("private-a", "private-z"), encoding="utf-8")

    with pytest.raises(ValueError, match="no longer matches"):
        views.report()


def _write_public_dictionary(root: Path) -> None:
    data = root / "docs/data"
    data.mkdir(parents=True, exist_ok=True)
    fields = ["codebook_order,csv_column,codebook_name,codebook_part,survey_wave_ranges,survey_question_refs,codebook_condition,wave_variant_flags,quarter,pdf_page,printed_page,field_family,timing_class,predictor_use,sas_length,sas_format,sas_label"]
    for index in range(587):
        family = "survey_response" if index == 0 else "metadata"
        fields.append(f"{index+1},field_{index},Field {index},A,,,,,,,,{family},unknown,REVIEW,8,FMT,Label {index}")
    (data / "nsmo-v70-field-dictionary.csv").write_text("\n".join(fields) + "\n", encoding="utf-8")
    (data / "nsmo-v70-value-labels.csv").write_text(
        "format_name,format_value,format_label\nFMT,1,One\n", encoding="utf-8")
    (data / "nsmo-v70-wave-coverage.csv").write_text(
        "csv_column,observed_response_waves,entirely_not_asked_waves,partially_not_asked_waves,not_applicable_waves\n"
        "field_0,1-46,,-,\n", encoding="utf-8")


def _write_domain_receipts(root: Path, source_sha: str) -> None:
    from credit_atlas.workspace import sha256

    dictionary = root / "docs/data/nsmo-v70-field-dictionary.csv"
    source_docs = root / "data/private/mortgage/nsmo-2026-05-27/source_docs"
    source_docs.mkdir(parents=True, exist_ok=True)
    labels_path = source_docs / "nsmo_v70_labels.sas"
    formats_path = source_docs / "nsmo_v70_formats.sas"
    labels_path.write_text("labels", encoding="utf-8")
    formats_path.write_text("formats", encoding="utf-8")
    state_path = root / "artifacts/private/nsmo-performance-state-audit-20261015/receipt.json"
    domain_path = root / "artifacts/private/nsmo-domain-aggregate-audit-20261015/receipt.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    domain_path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "status": "PASS", "sources": {"puf_csv": {"sha256": source_sha}},
        "schema": {"rows": 2}, "termination": {
            "code_labels_from_official_sas_formats": {"1": "Open", "2": "Terminated"},
            "close_status_counts": {"1": 1, "2": 1},
            "close_date_consistency": {"valid": 2},
            "final_2025q3_performance_by_close_status": [],
            "codebook_note_issue": "stale field reference",
        },
        "quarterly_state_matrix": [
            {"quarter_end": f"Q{i}", "paired_transition_to_next_quarter": (
                None if i == 50 else {
                    "next_quarter_end": f"Q{i+1}",
                    "observation_classes": {"observed_to_observed": 1, "observed_to_nonobservation": 1},
                    "observed_state_transitions": [{"from": "C", "to": "1", "n": 1,
                                                     "weight_sum_descriptive_only": 10.0}],
                })}
            for i in range(51)
        ],
        "limitations": ["No target."],
    }
    domain = {
        "status": "PASS", "sources": {"puf_csv": {"sha256": source_sha},
                                             "field_dictionary_sha256": sha256(dictionary),
                                             "sas_labels_sha256": sha256(labels_path),
                                             "sas_formats_sha256": sha256(formats_path)},
        "schema": {"row_count": 2},
        "origination_attributes": [{"field": f"attribute_{i}"} for i in range(30)],
        "origination_scores": [{"field": f"score_{i}"} for i in range(5)],
        "quarterly_respondent_scores": [{"quarter": f"Q{i}"} for i in range(51)],
        "quarterly_forbearance": [{"quarter": f"Q{i}"} for i in range(23)],
        "limitations": ["Weighted values descriptive only."],
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    domain_path.write_text(json.dumps(domain), encoding="utf-8")


def _write_target_feasibility_receipt(root: Path, source_sha: str) -> None:
    target = root / "artifacts/private/nsmo-target-anchor-vintage-20261016/receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    outcomes = {"observed_90plus_event": 1, "four_quarters_observed_no_event": 1}
    target.write_text(json.dumps({
        "status": "PASS", "target_created": False,
        "source": {"sha256": source_sha},
        "schema": {"rows": 2, "columns": 587, "quarterly_status_columns": 51},
        "candidate_definition_for_feasibility_only": {"horizon": "four quarterly snapshots"},
        "baseline_quarter_state_aggregates": [{
            "baseline_quarter": "2013-03-31", "baseline_state": "C",
            "full_12m_snapshot_horizon_available": True,
            "outcomes_unweighted": {"eligible_snapshot": 2, **outcomes},
        }],
        "origination_vintage_baseline_aggregates": [{
            "origination_year": "2013", "baseline_state": "C",
            "full_horizon_baseline_snapshots_unweighted": outcomes,
            "unique_mortgages_with_at_least_one_full_horizon_baseline": 2,
            "unique_mortgages_by_snapshot_outcome_class_nonexclusive": outcomes,
        }],
        "one_landmark_per_mortgage_support": {
            "selection_rule": "earliest eligible C",
            "outcomes_by_origination_vintage": [{
                "origination_year": "2013", "unique_mortgage_count": 2,
                "first_eligible_c_landmark_outcomes_unweighted": outcomes,
            }],
            "outcomes_by_landmark_quarter_and_vintage": [{
                "landmark_quarter": "2013-03-31", "origination_year": "2013",
                "unique_mortgage_count": 2, "outcomes_unweighted": outcomes,
            }],
        },
    }), encoding="utf-8")


def _write_origination_feasibility_receipt(root: Path, source_sha: str) -> None:
    target = root / "artifacts/private/nsmo-origination-feasibility-20261016/receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    outcomes = {"observed_90plus": 1, "all_in_window_snapshots_observed_no_90plus": 1}
    target.write_text(json.dumps({
        "status": "PASS", "target_created": False,
        "source": {"sha256": source_sha},
        "schema": {"rows": 2, "columns": 587, "quarterly_status_columns": 51},
        "reconciliation": {"reconciles": True, "classified_rows": 2, "origination_vintage_rows": 2},
        "candidate_definition_for_feasibility_only": {"anchor": "open_year/open_month"},
        "outcomes_unweighted": outcomes,
        "outcomes_by_origination_year_unweighted": {"2013": outcomes},
        "available_snapshot_count_by_origination_year_unweighted": {
            "2013": {"source_quarters_within_month_window_3": 2},
        },
    }), encoding="utf-8")


def test_nsmo_dictionary_has_full_field_crosswalk_and_value_labels(tmp_path):
    _write_public_dictionary(tmp_path)
    result = NsmoViews(tmp_path).dictionary()

    assert result["field_count"] == 587
    assert result["value_label_count"] == 1
    assert result["wave_coverage_count"] == 1
    assert result["fields"][0]["csv_column"] == "field_0"
    assert result["value_labels"][0]["format_label"] == "One"
    assert result["wave_coverage"][0]["observed_response_waves"] == "1-46"


def test_nsmo_dictionary_rejects_incomplete_crosswalk(tmp_path):
    data = tmp_path / "docs/data"
    data.mkdir(parents=True)
    (data / "nsmo-v70-field-dictionary.csv").write_text(
        "csv_column,codebook_name\na,A\n", encoding="utf-8")
    (data / "nsmo-v70-value-labels.csv").write_text(
        "format_name,format_value,format_label\n", encoding="utf-8")

    with pytest.raises(ValueError, match="schema check"):
        NsmoViews(tmp_path).dictionary()


def test_nsmo_domain_profile_is_hash_bound_and_aggregates_only(tmp_path):
    csv = _workspace(tmp_path)
    _write_public_dictionary(tmp_path)
    _write_domain_receipts(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())

    result = NsmoViews(tmp_path).domains()

    assert result["schema_version"] == "nsmo-domain-profile-v1"
    assert result["termination"]["status_counts"] == {"1": 1, "2": 1}
    assert len(result["quarterly_respondent_scores"]) == 51
    assert len(result["quarterly_forbearance"]) == 23
    assert result["observed_state_transitions"][0]["transitions"][0]["share_of_observed_from_state"] == 1.0
    assert "private-a" not in json.dumps(result)


def test_nsmo_domain_profile_rejects_audit_for_another_source(tmp_path):
    csv = _workspace(tmp_path)
    _write_public_dictionary(tmp_path)
    _write_domain_receipts(tmp_path, "0" * 64)

    with pytest.raises(ValueError, match="stale or does not match"):
        NsmoViews(tmp_path).domains()


def test_nsmo_target_feasibility_is_hash_bound_and_reconciles_anchors(tmp_path):
    csv = _workspace(tmp_path)
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    _write_target_feasibility_receipt(tmp_path, digest)

    result = NsmoViews(tmp_path).target_feasibility()

    assert result["schema_version"] == "nsmo-target-feasibility-v1"
    assert result["repeated_landmarks"]["c_state_summary"]["unique_mortgages_with_at_least_one_full_horizon_baseline"] == 2
    assert result["one_landmark_per_mortgage"]["summary"]["outcomes_unweighted"]["observed_90plus_event"] == 1
    assert "private-a" not in json.dumps(result)


def test_nsmo_target_feasibility_rejects_a_receipt_for_another_puf(tmp_path):
    _workspace(tmp_path)
    _write_target_feasibility_receipt(tmp_path, "0" * 64)

    with pytest.raises(ValueError, match="stale or does not match"):
        NsmoViews(tmp_path).target_feasibility()


def test_nsmo_origination_feasibility_is_hash_bound_and_aggregates_only(tmp_path):
    csv = _workspace(tmp_path)
    _write_origination_feasibility_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())

    result = NsmoViews(tmp_path).origination_feasibility()

    assert result["schema_version"] == "nsmo-origination-feasibility-v1"
    assert result["outcomes_unweighted"]["observed_90plus"] == 1
    assert result["outcomes_by_origination_year"][0]["origination_year"] == "2013"
    assert "private-a" not in json.dumps(result)


def test_nsmo_origination_feasibility_rejects_a_receipt_for_another_puf(tmp_path):
    _workspace(tmp_path)
    _write_origination_feasibility_receipt(tmp_path, "0" * 64)

    with pytest.raises(ValueError, match="stale or does not match"):
        NsmoViews(tmp_path).origination_feasibility()


def test_nsmo_origination_feasibility_rejects_nonreconciling_vintage_totals(tmp_path):
    csv = _workspace(tmp_path)
    _write_origination_feasibility_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    path = tmp_path / "artifacts/private/nsmo-origination-feasibility-20261016/receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["outcomes_by_origination_year_unweighted"]["2013"]["observed_90plus"] = 2
    path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ValueError, match="vintage snapshot support does not reconcile"):
        NsmoViews(tmp_path).origination_feasibility()


def test_nsmo_profile_http_and_standalone_page(tmp_path):
    _workspace(tmp_path)
    _write_public_dictionary(tmp_path)
    csv = tmp_path / "data/private/mortgage/nsmo-2026-05-27/puf/nsmo_v70_1324_puf.csv"
    _write_domain_receipts(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    _write_target_feasibility_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    _write_origination_feasibility_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    source_web = Path(__file__).parents[1] / "apps" / "web"
    target_web = tmp_path / "apps" / "web"
    target_web.mkdir(parents=True)
    for name in ("nsmo.html", "nsmo.css", "nsmo.js"):
        shutil.copyfile(source_web / name, target_web / name)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=tmp_path)))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/nsmo", timeout=5) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert "D02 · SEPARATE NSMO CASE" in html
            assert "Endpoint support, landmark và censoring" in html
        with urlopen(base + "/api/nsmo-profile", timeout=5) as response:
            payload = json.loads(response.read())
            assert response.status == 200
            assert payload["status"] == "AVAILABLE"
            assert "private-a" not in json.dumps(payload)
        with urlopen(base + "/api/nsmo-dictionary", timeout=5) as response:
            dictionary = json.loads(response.read())
            assert response.status == 200
            assert dictionary["field_count"] == 587
            assert dictionary["value_label_count"] == 1
        with urlopen(base + "/api/nsmo-domains", timeout=5) as response:
            domains = json.loads(response.read())
            assert response.status == 200
            assert len(domains["observed_state_transitions"]) == 50
        with urlopen(base + "/api/nsmo-target-feasibility", timeout=5) as response:
            feasibility = json.loads(response.read())
            assert response.status == 200
            assert feasibility["status"] == "AVAILABLE"
            assert "private-a" not in json.dumps(feasibility)
        with urlopen(base + "/api/nsmo-origination-feasibility", timeout=5) as response:
            feasibility = json.loads(response.read())
            assert response.status == 200
            assert feasibility["outcomes_unweighted"]["observed_90plus"] == 1
            assert "private-a" not in json.dumps(feasibility)
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-profile?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-target-feasibility?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-origination-feasibility?run=unexpected", timeout=5)
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
