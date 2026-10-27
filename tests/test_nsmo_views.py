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
        "csv_column,puf_nonmissing_value_waves,entirely_not_asked_waves,partially_not_asked_waves,not_applicable_waves\n"
        "field_0,1-46,,-,\n", encoding="utf-8")
    (data / "nsmo-v70-wave-item-comparability.csv").write_text(
        "field,assessment\nfield_0,WORDING_VERSION_BREAK: separate wave groups\n",
        encoding="utf-8")
    gate_rows = ["codebook_order,csv_column,codebook_name,field_family,timing_class,publisher_predictor_gate,eligibility_bucket,intended_scope,decision_status,required_review,sas_label"]
    for index in range(587):
        family = "survey_response" if index == 0 else "metadata"
        gate_rows.append(f"{index+1},field_{index},Field {index},{family},unknown,REVIEW,POST_ORIGINATION_RESPONSE_EXCLUDE,Descriptive only,AUXILIARY_ONLY_OR_EXCLUDED_FROM_FEATURES,Review timing,Label {index}")
    (data / "nsmo-v70-predictor-gates.csv").write_text("\n".join(gate_rows) + "\n", encoding="utf-8")


def _copy_public_dictionary(root: Path) -> None:
    source_data = Path(__file__).parents[1] / "docs" / "data"
    target_data = root / "docs" / "data"
    target_data.mkdir(parents=True, exist_ok=True)
    for name in (
        "nsmo-v70-field-dictionary.csv",
        "nsmo-v70-value-labels.csv",
        "nsmo-v70-wave-coverage.csv",
        "nsmo-v70-wave-item-comparability.csv",
        "nsmo-v70-predictor-gates.csv",
    ):
        shutil.copyfile(source_data / name, target_data / name)


def _write_domain_receipts(root: Path, source_sha: str) -> None:
    from credit_atlas.nsmo_views import _FIELD_DICTIONARY_RECEIPT_SHA256
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
                                             "field_dictionary_sha256": _FIELD_DICTIONARY_RECEIPT_SHA256,
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
    repeated_outcomes = {**outcomes, "termination_same_month_ambiguous": 2}
    target.write_text(json.dumps({
        "status": "PASS", "target_created": False,
        "source": {"sha256": source_sha},
        "schema": {"rows": 2, "columns": 587, "quarterly_status_columns": 51},
        "candidate_definition_for_feasibility_only": {"horizon": "four quarterly snapshots"},
        "baseline_quarter_state_aggregates": [{
            "baseline_quarter": "2013-03-31", "baseline_state": "C",
            "full_12m_snapshot_horizon_available": True,
            "outcomes_unweighted": {"eligible_snapshot": 4, **repeated_outcomes},
        }],
        "origination_vintage_baseline_aggregates": [{
            "origination_year": "2013", "baseline_state": "C",
            "full_horizon_baseline_snapshots_unweighted": repeated_outcomes,
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
        "same_month_ambiguous_snapshot_status_counts_by_baseline_state": {"C": {"A": 2}, "1": {}, "2": {}},
        "same_month_ambiguous_snapshot_status_counts_by_vintage_and_baseline_state": [{
            "origination_year": "2013", "baseline_state": "C", "snapshot_status_counts_unweighted": {"A": 2},
        }],
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


def _write_first_observed_transition_receipt(root: Path, source_sha: str) -> None:
    target = root / "artifacts/private/nsmo-first-observed-transition-support-20261016/receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "status": "PASS",
        "source": {"sha256": source_sha},
        "schema": {"rows": 2, "columns": 587, "quarterly_status_columns": 51},
        "checks": {"unique_mortgage_ids": 2, "width_errors": 0,
                   "empty_mortgage_ids": 0, "duplicate_mortgage_ids": 0},
        "definition": {"target_or_label_created": False, "risk_set_or_event_incidence": False},
        "all_vintages": {
            "repeated_90plus_transition_count_by_source_state": {"C": 2},
            "unique_mortgages_with_any_90plus_transition_by_source_state": {"C": 1},
            "first_observed_90plus_event_count": 2,
            "first_observed_90plus_event_with_baseline_source_state": 1,
            "first_observed_90plus_event_without_observed_prior": 1,
            "first_observed_90plus_event_after_other_adverse_state": 0,
            "first_observed_90plus_event_by_prior_baseline_state": {"C": 1},
            "first_event_partition_reconciles": True,
        },
        "by_origination_vintage_and_source_state": [{
            "origination_year": "2013", "source_state": "C",
            "repeated_90plus_transition_count": 2,
            "unique_mortgages_with_any_90plus_transition": 1,
            "first_observed_90plus_event_count": 1,
        }],
        "limitations": ["Aggregate-only; no target."],
    }), encoding="utf-8")


def _write_first_entry_risk_set_receipt(root: Path, source_sha: str) -> None:
    target = root / "artifacts/private/nsmo-first-entry-risk-set-20261016/receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "status": "PASS", "source": {"sha256": source_sha},
        "schema": {"rows": 2, "columns": 587, "quarterly_status_columns": 51},
        "checks": {"row_width_errors": 0, "empty_ids": 0, "duplicate_ids": 0, "partitioned_rows": 2},
        "definition": {"target_created": False, "risk_set_is_model_ready": False, "rates_or_weights_used": False},
        "population_partition_unweighted": {"entered_risk_set": 2},
        "risk_set_entry_by_state_unweighted": {"C": 2},
        "first_exit_after_entry_unweighted": {"observed_90plus": 1, "administrative_end": 1},
        "at_risk_quarter_intervals_by_start_state_unweighted": {"C": 3},
        "population_and_entry_by_origination_vintage_unweighted": [{
            "origination_year": "2013", "puf_mortgages": 2, "entered_risk_set": 2,
            "pre_entry_exclusions": {},
            "first_exit_after_entry": {"observed_90plus": 1, "administrative_end": 1},
        }],
        "by_origination_vintage_and_entry_state_unweighted": [{
            "origination_year": "2013", "entry_state": "C", "mortgages_entered": 2,
            "at_risk_quarter_intervals": 3, "intervals_by_class": {"C": 3},
            "first_exit_by_class": {"observed_90plus": 1, "administrative_end": 1},
        }],
        "limitations": ["Aggregate-only; no risk target."],
    }), encoding="utf-8")


def _write_horizon_sensitivity_receipt(root: Path, source_sha: str) -> None:
    target = root / "artifacts/private/nsmo-horizon-sensitivity-20261016/receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for quarters in (2, 4, 8):
        results.append({
            "horizon_quarters": quarters, "approx_months": quarters * 3,
            "c_baseline_snapshots_with_full_horizon_unweighted": 2,
            "unique_mortgages_with_at_least_one_c_baseline": 2,
            "snapshot_outcomes_unweighted": {
                "observed_90plus_event": 1,
                f"observed_no_90plus_within_{quarters}_quarters": 1,
            },
            "unique_mortgages_by_outcome_nonexclusive": {
                "observed_90plus_event": 1,
                f"observed_no_90plus_within_{quarters}_quarters": 1,
            },
            "by_origination_year": [{
                "origination_year": "2013",
                "c_baseline_snapshots_with_full_horizon_unweighted": 2,
                "unique_mortgages_with_at_least_one_c_baseline": 2,
                "snapshot_outcomes_unweighted": {
                    "observed_90plus_event": 1,
                    f"observed_no_90plus_within_{quarters}_quarters": 1,
                },
                "unique_mortgages_by_outcome_nonexclusive": {
                    "observed_90plus_event": 1,
                    f"observed_no_90plus_within_{quarters}_quarters": 1,
                },
            }],
            "one_landmark_per_mortgage": {
                "selection_rule": "earliest eligible C",
                "mortgages_with_eligible_landmark": 2,
                "outcomes_unweighted": {
                    "observed_90plus_event": 1,
                    f"observed_no_90plus_within_{quarters}_quarters": 1,
                },
                "unique_mortgages_by_outcome": {
                    "observed_90plus_event": 1,
                    f"observed_no_90plus_within_{quarters}_quarters": 1,
                },
                "by_origination_year": [{
                    "origination_year": "2013",
                    "mortgages_with_eligible_landmark": 2,
                    "outcomes_unweighted": {
                        "observed_90plus_event": 1,
                        f"observed_no_90plus_within_{quarters}_quarters": 1,
                    },
                    "unique_mortgages_by_outcome": {
                        "observed_90plus_event": 1,
                        f"observed_no_90plus_within_{quarters}_quarters": 1,
                    },
                }],
            },
        })
    target.write_text(json.dumps({
        "status": "PASS", "target_created": False,
        "source": {"sha256": source_sha},
        "schema": {"rows": 2, "columns": 587, "quarterly_status_columns": 51},
        "integrity": {"width_errors": 0, "missing_ids": 0, "duplicate_ids": 0},
        "candidate_definition_for_feasibility_only": {"baseline_state": "C"},
        "horizon_results": results,
        "limitations": ["Aggregate-only; no target."],
    }), encoding="utf-8")


def test_nsmo_dictionary_has_full_field_crosswalk_and_value_labels(tmp_path):
    _write_public_dictionary(tmp_path)
    result = NsmoViews(tmp_path).dictionary()

    assert result["field_count"] == 587
    assert result["value_label_count"] == 1
    assert result["wave_coverage_count"] == 1
    assert result["item_comparability_count"] == 1
    assert result["item_comparability"][0] == {
        "field": "field_0", "assessment": "WORDING_VERSION_BREAK: separate wave groups"}
    assert result["predictor_gate_count"] == 587
    assert result["approved_feature_count"] == 0
    assert result["predictor_gates"][0]["eligibility_bucket"] == "POST_ORIGINATION_RESPONSE_EXCLUDE"
    assert result["fields"][0]["csv_column"] == "field_0"
    assert result["value_labels"][0]["format_label"] == "One"
    assert result["wave_coverage"][0]["puf_nonmissing_value_waves"] == "1-46"


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
    _copy_public_dictionary(tmp_path)
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
    assert result["same_month_ambiguity"]["snapshot_status_counts_by_baseline_state"] == {"C": {"A": 2}, "1": {}, "2": {}}
    assert result["same_month_ambiguity"]["snapshot_status_counts_by_vintage_and_baseline_state"][0]["snapshot_status_counts_unweighted"] == {"A": 2}
    assert "private-a" not in json.dumps(result)


def test_nsmo_target_feasibility_rejects_nonreconciling_same_month_status(tmp_path):
    csv = _workspace(tmp_path)
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    _write_target_feasibility_receipt(tmp_path, digest)
    receipt_path = tmp_path / "artifacts/private/nsmo-target-anchor-vintage-20261016/receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["same_month_ambiguous_snapshot_status_counts_by_baseline_state"]["C"]["A"] = 1
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ValueError, match="same-month state totals do not reconcile"):
        NsmoViews(tmp_path).target_feasibility()


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


def test_nsmo_first_observed_transition_support_is_hash_bound_and_aggregate_only(tmp_path):
    csv = _workspace(tmp_path)
    _write_first_observed_transition_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    result = NsmoViews(tmp_path).first_observed_transition_support()
    assert result["schema_version"] == "nsmo-first-observed-transition-support-v1"
    assert result["all_vintages"]["repeated_90plus_transition_count_by_source_state"] == {"C": 2}
    assert result["all_vintages"]["unique_mortgages_with_any_90plus_transition_by_source_state"] == {"C": 1}
    assert "private-a" not in json.dumps(result)


def test_nsmo_first_observed_transition_support_rejects_stale_puf(tmp_path):
    _workspace(tmp_path)
    _write_first_observed_transition_receipt(tmp_path, "0" * 64)
    with pytest.raises(ValueError, match="stale or does not match"):
        NsmoViews(tmp_path).first_observed_transition_support()


def test_nsmo_first_observed_transition_support_rejects_nonreconciling_vintage(tmp_path):
    csv = _workspace(tmp_path)
    _write_first_observed_transition_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    target = tmp_path / "artifacts/private/nsmo-first-observed-transition-support-20261016/receipt.json"
    receipt = json.loads(target.read_text(encoding="utf-8"))
    receipt["by_origination_vintage_and_source_state"][0]["repeated_90plus_transition_count"] = 3
    target.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="totals do not reconcile"):
        NsmoViews(tmp_path).first_observed_transition_support()


def test_nsmo_first_entry_risk_set_is_hash_bound_and_aggregate_only(tmp_path):
    csv = _workspace(tmp_path)
    _write_first_entry_risk_set_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    result = NsmoViews(tmp_path).first_entry_risk_set_feasibility()
    assert result["schema_version"] == "nsmo-first-entry-risk-set-feasibility-v1"
    assert result["risk_set_entry_by_state_unweighted"] == {"C": 2}
    assert result["first_exit_after_entry_unweighted"]["observed_90plus"] == 1
    assert result["population_and_entry_by_origination_vintage_unweighted"][0]["puf_mortgages"] == 2
    assert "private-a" not in json.dumps(result)


def test_nsmo_first_entry_risk_set_rejects_stale_puf(tmp_path):
    _workspace(tmp_path)
    _write_first_entry_risk_set_receipt(tmp_path, "0" * 64)
    with pytest.raises(ValueError, match="stale or does not match"):
        NsmoViews(tmp_path).first_entry_risk_set_feasibility()


def test_nsmo_first_entry_risk_set_rejects_nonreconciling_vintage(tmp_path):
    csv = _workspace(tmp_path)
    _write_first_entry_risk_set_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    target = tmp_path / "artifacts/private/nsmo-first-entry-risk-set-20261016/receipt.json"
    receipt = json.loads(target.read_text(encoding="utf-8"))
    receipt["by_origination_vintage_and_entry_state_unweighted"][0]["mortgages_entered"] = 3
    target.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="vintage groups do not reconcile"):
        NsmoViews(tmp_path).first_entry_risk_set_feasibility()


def test_nsmo_first_entry_risk_set_rejects_nonreconciling_population_vintage(tmp_path):
    csv = _workspace(tmp_path)
    _write_first_entry_risk_set_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    target = tmp_path / "artifacts/private/nsmo-first-entry-risk-set-20261016/receipt.json"
    receipt = json.loads(target.read_text(encoding="utf-8"))
    receipt["population_and_entry_by_origination_vintage_unweighted"][0]["puf_mortgages"] = 3
    target.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="vintage population counts do not reconcile"):
        NsmoViews(tmp_path).first_entry_risk_set_feasibility()


def test_nsmo_horizon_sensitivity_is_hash_bound_and_aggregate_only(tmp_path):
    csv = _workspace(tmp_path)
    _write_horizon_sensitivity_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    result = NsmoViews(tmp_path).horizon_sensitivity()
    assert result["schema_version"] == "nsmo-horizon-sensitivity-v1"
    assert [row["approx_months"] for row in result["horizon_results"]] == [6, 12, 24]
    assert result["horizon_results"][1]["snapshot_outcomes_unweighted"]["observed_90plus_event"] == 1
    assert result["horizon_results"][1]["by_origination_year"][0]["origination_year"] == "2013"
    assert result["horizon_results"][1]["one_landmark_per_mortgage"]["outcomes_unweighted"]["observed_90plus_event"] == 1
    assert "private-a" not in json.dumps(result)


def test_nsmo_horizon_sensitivity_rejects_stale_and_nonreconciling_receipts(tmp_path):
    csv = _workspace(tmp_path)
    _write_horizon_sensitivity_receipt(tmp_path, "0" * 64)
    with pytest.raises(ValueError, match="stale or does not match"):
        NsmoViews(tmp_path).horizon_sensitivity()

    _write_horizon_sensitivity_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    target = tmp_path / "artifacts/private/nsmo-horizon-sensitivity-20261016/receipt.json"
    receipt = json.loads(target.read_text(encoding="utf-8"))
    receipt["horizon_results"][1]["snapshot_outcomes_unweighted"]["observed_90plus_event"] = 2
    target.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="outcomes do not reconcile"):
        NsmoViews(tmp_path).horizon_sensitivity()


def test_nsmo_horizon_sensitivity_rejects_nonreconciling_vintage_totals(tmp_path):
    csv = _workspace(tmp_path)
    _write_horizon_sensitivity_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    target = tmp_path / "artifacts/private/nsmo-horizon-sensitivity-20261016/receipt.json"
    receipt = json.loads(target.read_text(encoding="utf-8"))
    receipt["horizon_results"][1]["by_origination_year"][0]["snapshot_outcomes_unweighted"]["observed_90plus_event"] = 2
    target.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="vintage outcomes do not reconcile"):
        NsmoViews(tmp_path).horizon_sensitivity()


def test_nsmo_profile_http_and_standalone_page(tmp_path):
    csv = _workspace(tmp_path)
    _copy_public_dictionary(tmp_path)
    _write_first_observed_transition_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    _write_first_entry_risk_set_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    _write_horizon_sensitivity_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    _write_domain_receipts(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    _write_target_feasibility_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    _write_origination_feasibility_receipt(tmp_path, hashlib.sha256(csv.read_bytes()).hexdigest())
    source_web = Path(__file__).parents[1] / "apps" / "web"
    target_web = tmp_path / "apps" / "web"
    target_web.mkdir(parents=True)
    for name in ("nsmo.html", "nsmo.css", "nsmo.js"):
        shutil.copyfile(source_web / name, target_web / name)
    source_workbook = Path(__file__).parents[1] / "apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx"
    target_workbook = tmp_path / "apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx"
    target_workbook.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_workbook, target_workbook)
    source_hud_workbook = Path(__file__).parents[1] / "apps/excel/templates/CreditAtlas-HUD-FHA-Performance.xlsx"
    shutil.copyfile(source_hud_workbook, target_workbook.parent / source_hud_workbook.name)
    source_nmdb_workbook = Path(__file__).parents[1] / "apps/excel/templates/CreditAtlas-NMDB-Performance.xlsx"
    shutil.copyfile(source_nmdb_workbook, target_workbook.parent / source_nmdb_workbook.name)
    source_d02_workbook = Path(__file__).parents[1] / "apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx"
    shutil.copyfile(source_d02_workbook, target_workbook.parent / source_d02_workbook.name)
    target_data = tmp_path / "docs/data"
    target_data.mkdir(parents=True, exist_ok=True)
    for name in (
        "hud-fha-performance-2026-08.csv", "hud-fha-performance-2026-08-subgroups.csv",
        "hud-fha-new-90plus-reasons-2026-08.csv", "hud-fha-foreclosure-statistics-2026-08.csv",
        "hud-fha-reo-recovery-2026-08.csv", "hud-fha-reo-loss-components-2026-08.csv",
        "hud-fha-production-transitions-2026-08.csv",
    ):
        shutil.copyfile(Path(__file__).parents[1] / "docs/data" / name, target_data / name)
    for name in ("nmdb-performance-national-quarterly-2026q2.csv",
                 "nmdb-performance-national-quarterly-2026q2-receipt.json"):
        shutil.copyfile(Path(__file__).parents[1] / "docs/data" / name, target_data / name)
    for name in ("nmdb-performance-state-quarterly-2026q2.csv",
                 "nmdb-performance-state-quarterly-2026q2-receipt.json"):
        shutil.copyfile(Path(__file__).parents[1] / "docs/data" / name, target_data / name)
    shutil.copyfile(Path(__file__).parents[1] / "docs/data/nsmo-v70-survey-returns.csv",
                    target_data / "nsmo-v70-survey-returns.csv")
    shutil.copyfile(Path(__file__).parents[1] / "docs/data/nsmo-v70-usable-responses.csv",
                    target_data / "nsmo-v70-usable-responses.csv")
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
            assert "Độ dài cửa sổ và support quan sát được" in html
            assert "horizon-sensitivity-vintage-table" in html
            assert "Chuyển trạng thái kề quý vào 90+" in html
            assert "Kênh phản hồi thay đổi theo wave" in html
            assert "usable-responses-table" in html
            assert "/downloads/nsmo-reference.xlsx" in html
            assert "/downloads/hud-fha-performance.xlsx" in html
            assert "/downloads/nmdb-performance.xlsx" in html
            assert "/downloads/d02-data-reference.xlsx" in html
            assert "FHA portfolio performance context" in html
            assert "Serious-delinquency inventory transitions" in html
            assert "hud-transitions-state" in html
            assert "Residential mortgage performance, 2002Q1–2026Q2" in html
        with urlopen(base + "/downloads/nsmo-reference.xlsx", timeout=5) as response:
            workbook_bytes = response.read()
            assert response.status == 200
            assert response.headers.get_content_type() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "CreditAtlas-NSMO-Reference.xlsx" in response.headers["Content-Disposition"]
            assert workbook_bytes[:2] == b"PK"
        with urlopen(base + "/downloads/d02-data-reference.xlsx", timeout=5) as response:
            workbook_bytes = response.read()
            assert response.status == 200
            assert response.headers.get_content_type() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "CreditAtlas-D02-Data-Reference.xlsx" in response.headers["Content-Disposition"]
            assert workbook_bytes[:2] == b"PK"
        with urlopen(base + "/downloads/hud-fha-performance.xlsx", timeout=5) as response:
            workbook_bytes = response.read()
            assert response.status == 200
            assert response.headers.get_content_type() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "CreditAtlas-HUD-FHA-Performance.xlsx" in response.headers["Content-Disposition"]
            assert workbook_bytes[:2] == b"PK"
        with urlopen(base + "/api/hud-fha-performance", timeout=5) as response:
            hud = json.loads(response.read())
            assert response.status == 200
            assert len(hud["monthly"]) == 26
            assert len(hud["subgroups"]) == 60
            assert len(hud["new_90plus_reasons"]) == 22
            assert len(hud["foreclosure_statistics"]) == 37
            assert len(hud["reo_recovery"]) == 50
            assert len(hud["reo_loss_components"]) == 13
            assert hud["latest"]["NSA"]["serious_delinquency_pct"] == 6.42
            assert hud["latest"]["SA"]["serious_delinquency_pct"] == 6.63
        with urlopen(base + "/api/hud-fha-production-transitions", timeout=5) as response:
            transitions = json.loads(response.read())
            assert response.status == 200
            assert len(transitions["monthly"]) == 13
            assert transitions["latest"]["period"] == "2026-08"
            assert transitions["latest"]["ending_serious_delinquency_inventory"] == 540410
            assert transitions["latest"]["flow_identity_difference"] == 0
        with urlopen(base + "/downloads/nmdb-performance.xlsx", timeout=5) as response:
            workbook_bytes = response.read()
            assert response.status == 200
            assert response.headers.get_content_type() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "CreditAtlas-NMDB-Performance.xlsx" in response.headers["Content-Disposition"]
            assert workbook_bytes[:2] == b"PK"
        with urlopen(base + "/api/nmdb-performance", timeout=5) as response:
            nmdb = json.loads(response.read())
            assert response.status == 200
            assert len(nmdb["observations"]) == 1568
            latest = {(row["market"], row["series_id"]): row["value_pct"] for row in nmdb["latest"]}
            assert latest[("All Mortgages", "P90DL")] == 1.0
            assert nmdb["series"]["PFORB"]["first_nonblank_quarter"] == "2019Q4"
        with urlopen(base + "/api/nmdb-state-performance?state=ca", timeout=10) as response:
            nmdb_state = json.loads(response.read())
            assert response.status == 200
            assert nmdb_state["selected_state"] == "CA"
            assert len(nmdb_state["observations"]) == 1568
            assert len(nmdb_state["latest"]) == 16
        with pytest.raises(HTTPError) as invalid_state:
            urlopen(base + "/api/nmdb-state-performance?state=ZZ", timeout=10)
        assert invalid_state.value.code == 400
        with urlopen(base + "/api/nsmo-profile", timeout=5) as response:
            payload = json.loads(response.read())
            assert response.status == 200
            assert payload["status"] == "AVAILABLE"
            assert "private-a" not in json.dumps(payload)
        with urlopen(base + "/api/nsmo-dictionary", timeout=5) as response:
            dictionary = json.loads(response.read())
            assert response.status == 200
            assert dictionary["field_count"] == 587
            assert dictionary["value_label_count"] == 377
        with urlopen(base + "/api/nsmo-survey-returns", timeout=5) as response:
            returns = json.loads(response.read())
            assert response.status == 200
            assert len(returns["waves"]) == 48
            assert returns["puf_v70"]["surveys_completed_total"] == 74193
            assert returns["puf_v70"]["online_share_pct_of_completed"] == 45.55
            assert returns["usability"]["usable_responses_table4"] == 63151
            assert returns["usability"]["puf_v70_rows_and_tables5_6_2013_2024"] == 62359
            assert returns["usability"]["usable_table4_minus_puf_scope"] == 792
            assert returns["usability"]["wave_7_remote_rural_scope_gap"] == 295
            assert returns["usability"]["wave_45_46_origination_scope_gap"] == 497
            assert returns["mode_shift"]["change_percentage_points"] == 41.06
            assert returns["waves"][45]["included_in_nsmo_v70_puf"] is True
            assert returns["waves"][46]["included_in_nsmo_v70_puf"] is False
            assert "no respondent-level response-mode field" in " ".join(returns["limitations"])
        with urlopen(base + "/api/nsmo-domains", timeout=5) as response:
            domains = json.loads(response.read())
            assert response.status == 200
            assert len(domains["observed_state_transitions"]) == 50
        with urlopen(base + "/api/nsmo-target-feasibility", timeout=5) as response:
            feasibility = json.loads(response.read())
            assert response.status == 200
            assert feasibility["status"] == "AVAILABLE"
            assert feasibility["same_month_ambiguity"]["snapshot_status_counts_by_baseline_state"] == {"C": {"A": 2}, "1": {}, "2": {}}
            assert "private-a" not in json.dumps(feasibility)
        with urlopen(base + "/api/nsmo-origination-feasibility", timeout=5) as response:
            feasibility = json.loads(response.read())
            assert response.status == 200
            assert feasibility["outcomes_unweighted"]["observed_90plus"] == 1
            assert "private-a" not in json.dumps(feasibility)
        with urlopen(base + "/api/nsmo-first-observed-transition-support", timeout=5) as response:
            transition = json.loads(response.read())
            assert response.status == 200
            assert transition["all_vintages"]["first_observed_90plus_event_count"] == 2
            assert "private-a" not in json.dumps(transition)
        with urlopen(base + "/api/nsmo-first-entry-risk-set-feasibility", timeout=5) as response:
            risk_set = json.loads(response.read())
            assert response.status == 200
            assert risk_set["risk_set_entry_by_state_unweighted"] == {"C": 2}
            assert risk_set["population_and_entry_by_origination_vintage_unweighted"][0]["entered_risk_set"] == 2
            assert "private-a" not in json.dumps(risk_set)
        with urlopen(base + "/api/nsmo-horizon-sensitivity", timeout=5) as response:
            sensitivity = json.loads(response.read())
            assert response.status == 200
            assert [row["approx_months"] for row in sensitivity["horizon_results"]] == [6, 12, 24]
            assert sensitivity["horizon_results"][0]["one_landmark_per_mortgage"]["mortgages_with_eligible_landmark"] == 2
            assert sensitivity["horizon_results"][0]["by_origination_year"][0]["origination_year"] == "2013"
            assert "private-a" not in json.dumps(sensitivity)
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-profile?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/hud-fha-performance?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-target-feasibility?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-origination-feasibility?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-first-observed-transition-support?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-first-entry-risk-set-feasibility?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-horizon-sensitivity?run=unexpected", timeout=5)
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nsmo-survey-returns?run=unexpected", timeout=5)
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
