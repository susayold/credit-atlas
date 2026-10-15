from scripts.audit_nsmo_performance_states import _compile_formats, _value_in_format


def test_sas_format_validator_accepts_characters_and_numeric_ranges():
    compiled = _compile_formats({
        "$pstatfm": [
            {"format_value": "'C'", "format_label": "Current"},
            {"format_value": "'A'", "format_label": "History ended"},
        ],
        "pscorefm": [
            {"format_value": "300-619", "format_label": "Low"},
            {"format_value": "620-850", "format_label": "Higher"},
            {"format_value": "-2", "format_label": "Not applicable"},
        ],
    })

    assert _value_in_format("C", compiled["$pstatfm"])
    assert not _value_in_format("c", compiled["$pstatfm"])
    assert _value_in_format("300", compiled["pscorefm"])
    assert _value_in_format("640", compiled["pscorefm"])
    assert _value_in_format("-2", compiled["pscorefm"])
    assert not _value_in_format("851", compiled["pscorefm"])
