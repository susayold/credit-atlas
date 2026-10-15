import pytest

from credit_atlas.nsmo_codebook import (
    classify_nsmo_field,
    parse_sas_formats,
    parse_sas_labels,
    reconcile_headers,
)


def test_survey_responses_are_not_approved_as_origination_features():
    result = classify_nsmo_field("X05A", 4, "A")
    assert result == {
        "field_family": "survey_response",
        "timing_class": "post_origination_survey_response",
        "predictor_use": "NOT_ORIGINATION_TIME_SAFE",
    }


@pytest.mark.parametrize(
    "name,ordinal,family,timing,use",
    [
        ("Score_Orig_R", 352, "origination_credit_score", "at_origination", "CANDIDATE_AFTER_ROLE_AND_MISSINGNESS_REVIEW; VANTAGESCORE_NOT_FICO"),
        ("Score_0925_R", 406, "quarterly_credit_score", "quarterly_as_of", "DYNAMIC_ONLY_AT_OR_BEFORE_INDEX_DATE; NO_FUTURE_VALUES"),
        ("Perf_Status_0925", 509, "quarterly_performance_status", "quarterly_outcome_history", "OUTCOME_HISTORY; NOT_SAME_PERIOD_OR_FUTURE_FEATURE"),
        ("Close_Status_0925", 512, "mortgage_termination", "termination_through_2025Q3", "COMPETING_EVENT_OR_CENSORING_ONLY"),
        ("Forb0925", 536, "quarterly_forbearance", "quarterly_as_of", "DYNAMIC_ONLY_AT_OR_BEFORE_INDEX_DATE; NOT_ORIGINATION_FEATURE"),
        ("Mtmltv0925", 587, "quarterly_mark_to_market_ltv", "quarterly_as_of", "DYNAMIC_ONLY_AT_OR_BEFORE_INDEX_DATE; REVIEW_LOOKAHEAD"),
    ],
)
def test_supplemental_temporal_field_gates(name, ordinal, family, timing, use):
    result = classify_nsmo_field(name, ordinal, "B")
    assert result == {"field_family": family, "timing_class": timing, "predictor_use": use}


def test_codebook_header_reconciliation_is_case_insensitive():
    records = [
        {"csv_column": "nsmoid"},
        {"csv_column": "perf_status_0925"},
    ]
    reconcile_headers(records, ["NSMOID", "PERF_STATUS_0925"])


def test_codebook_header_reconciliation_rejects_missing_and_extra_fields():
    records = [{"csv_column": "nsmoid"}]
    with pytest.raises(ValueError, match="(?i)header/codebook mismatch"):
        reconcile_headers(records, ["NSMOID", "new_field"])


def test_codebook_header_reconciliation_rejects_case_insensitive_duplicates():
    records = [{"csv_column": "nsmoid"}]
    with pytest.raises(ValueError, match="case-insensitive duplicate"):
        reconcile_headers(records, ["NSMOID", "nsmoid"])


def test_sas_label_parser_maps_column_format_and_label(tmp_path):
    path = tmp_path / "labels.sas"
    path.write_text(
        'attrib\nnsmoid length = 8. format = PIDFM. label = "NSMO Identification Number"\n',
        encoding="utf-8",
    )
    assert parse_sas_labels(path) == {
        "nsmoid": {
            "sas_length": "8",
            "sas_format": "PIDFM",
            "sas_label": "NSMO Identification Number",
        }
    }


def test_sas_format_parser_preserves_string_and_numeric_domain_labels(tmp_path):
    path = tmp_path / "formats.sas"
    path.write_text(
        "value $pstatfm\n"
        "  'C' = 'C: Current'\n"
        ";\n\n"
        'value pforb\n'
        ' 1 = "1: In forbearance"\n'
        ' -4 = "-4: Missing"\n'
        ';\n',
        encoding="utf-8",
    )
    result = parse_sas_formats(path)
    assert result["$pstatfm"][0] == {
        "format_name": "$pstatfm",
        "format_value": "'C'",
        "format_label": "C: Current",
    }
    assert result["pforb"][0]["format_value"] == "1"
    assert result["pforb"][1]["format_label"] == "-4: Missing"
