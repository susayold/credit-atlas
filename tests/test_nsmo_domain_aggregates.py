from collections import Counter

from scripts.audit_nsmo_domain_aggregates import _bucket_for_value, _compile_formats, _field_summary


def test_score_values_are_grouped_to_publisher_bins_and_special_codes_stay_distinct():
    formats = [{
        "format_value": "300-619", "format_label": "Low score"},
        {"format_value": "620-850", "format_label": "Higher score"},
        {"format_value": "-2", "format_label": "Not applicable"},
    ]
    rules = _compile_formats({"pscorefm": formats})["pscorefm"]

    assert _bucket_for_value("599", rules, formats) == "300-619"
    assert _bucket_for_value("700", rules, formats) == "620-850"
    assert _bucket_for_value("-2", rules, formats) == "-2"


def test_forbearance_summary_uses_reported_response_denominator_and_weighted_sum():
    formats = [
        {"format_value": "1", "format_label": "In forbearance"},
        {"format_value": "2", "format_label": "Not in forbearance"},
        {"format_value": "-2", "format_label": "Not applicable"},
        {"format_value": "-4", "format_label": "Missing"},
    ]
    result = _field_summary(
        {"csv_column": "forb0320", "sas_label": "Forbearance", "sas_format": "PFORB", "quarter": "2020-Q1"},
        Counter({"1": 2, "2": 6, "-2": 1, "-4": 1}),
        Counter({"1": 20.0, "2": 60.0, "-2": 10.0, "-4": 10.0}),
        formats,
        10,
        known_codes={"1", "2"}, affirmative_code="1",
    )

    assert result["available_n"] == 8
    assert result["available_share_of_full_sample"] == 0.8
    assert result["affirmative_n"] == 2
    assert result["affirmative_share_of_known_responses"] == 0.25
    assert result["affirmative_weighted_share_of_known_responses_descriptive_only"] == 0.25


def test_score_availability_excludes_not_applicable_and_missing_codes():
    formats = [
        {"format_value": "300-619", "format_label": "Low score"},
        {"format_value": "-2", "format_label": "Not applicable"},
        {"format_value": "-4", "format_label": "Missing"},
    ]
    result = _field_summary(
        {"csv_column": "score_orig_r", "sas_label": "Score", "sas_format": "PSCOREFM", "quarter": ""},
        Counter({"300-619": 7, "-2": 2, "-4": 1}),
        Counter({"300-619": 70.0, "-2": 20.0, "-4": 10.0}),
        formats,
        10,
    )

    assert result["available_n"] == 7
    assert result["available_share_of_full_sample"] == 0.7
    assert result["categories"][1]["code"] == "-2"
    assert result["categories"][1]["n"] == 2
