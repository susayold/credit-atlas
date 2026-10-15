from scripts.audit_nsmo_origination_feasibility import (
    _expected_followup_quarters,
    _month_ordinal,
    _quarter_months_after_open,
    classify_origination_followup,
)


def test_opening_quarter_is_excluded_and_only_post_open_quarters_are_used():
    dates = [(2023, 3), (2023, 6), (2023, 9), (2023, 12),
             (2024, 3), (2024, 6), (2024, 9), (2024, 12)]
    quarters = [(_month_ordinal(y, m), i) for i, (y, m) in enumerate(dates)]
    open_quarter, indices = _quarter_months_after_open(2023, 10, quarters)
    assert open_quarter == _month_ordinal(2023, 12)
    assert indices == [4, 5, 6]


def test_month_precision_window_contains_three_or_four_quarter_ends():
    quarters = [(_month_ordinal(y, m), i) for i, (y, m) in enumerate(
        ([(2023, 3), (2023, 6), (2023, 9), (2023, 12)]
         + [(2024, 3), (2024, 6), (2024, 9), (2024, 12)])
    )]
    opening, indices = _quarter_months_after_open(2023, 1, quarters)
    expected = _expected_followup_quarters(opening, _month_ordinal(2023, 1) + 12)
    assert len(indices) == len(expected) == 3
    assert [quarters[i][0] for i in indices] == expected


def test_december_ordinal_rolls_into_next_calendar_year_correctly():
    opening = _month_ordinal(2023, 12)
    expected = _expected_followup_quarters(opening, opening + 12)
    assert expected == [_month_ordinal(2024, m) for m in (3, 6, 9, 12)]


def test_observed_90plus_is_separate_from_other_adverse_states():
    opening = _month_ordinal(2023, 3)
    expected = [_month_ordinal(2023, m) for m in (6, 9, 12)]
    observations = list(zip(expected, ["1", "3", "A"]))
    assert classify_origination_followup(observations, expected, set(expected), None) == "observed_90plus"
    other = list(zip(expected, ["1", "8", "A"]))
    assert classify_origination_followup(other, expected, set(expected), None) == "observed_other_adverse_state_8"


def test_nonobservation_never_becomes_no_event():
    expected = [_month_ordinal(2023, m) for m in (6, 9, 12)]
    observations = list(zip(expected, ["C", "K", "C"]))
    assert classify_origination_followup(observations, expected, set(expected), None) == "observation_censor_K"


def test_same_month_termination_is_ambiguous_and_earlier_termination_censors():
    expected = [_month_ordinal(2023, m) for m in (6, 9, 12)]
    observations = list(zip(expected, ["C", "3", "C"]))
    assert classify_origination_followup(observations, expected, set(expected), expected[1]) == "termination_same_month_ambiguous"
    assert classify_origination_followup(observations, expected, set(expected), expected[1] - 1) == "termination_competing_censor"


def test_missing_end_of_horizon_is_administrative_censor_not_negative():
    expected = [_month_ordinal(2024, m) for m in (3, 6, 9, 12)]
    observations = list(zip(expected[:-1], ["C", "C", "C"]))
    assert classify_origination_followup(observations, expected, set(expected[:-1]), None) == "administratively_short_followup"


def test_complete_observed_snapshots_support_only_no_observed_event_language():
    expected = [_month_ordinal(2023, m) for m in (6, 9, 12)]
    observations = list(zip(expected, ["C", "1", "2"]))
    assert classify_origination_followup(observations, expected, set(expected), None) == "all_in_window_snapshots_observed_no_90plus"
