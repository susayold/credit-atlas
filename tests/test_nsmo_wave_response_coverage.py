from scripts.audit_nsmo_wave_response_coverage import compress_waves, lookup_label


def test_lookup_label_matches_publisher_numeric_range_formats():
    assert lookup_label("50", {"45-54": "45-54 years old"}) == "45-54 years old"


def test_lookup_label_preserves_exact_special_codes():
    assert lookup_label("-3", {"-3": "not asked in wave"}) == "not asked in wave"


def test_compress_waves_collapses_only_consecutive_wave_numbers():
    assert compress_waves([1, 2, 3, 6, 8, 9]) == "1-3;6;8-9"
