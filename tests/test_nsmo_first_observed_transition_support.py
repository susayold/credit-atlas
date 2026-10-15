from scripts.audit_nsmo_first_observed_transition_support import mortgage_transition_summary


def test_repeated_transitions_and_unique_source_support_are_separate():
    summary = mortgage_transition_summary(["C", "3", "3", "C", "4"])
    assert summary["repeated_transitions"] == {"C": 2}
    assert summary["first_event_from"] == "C"


def test_first_observed_event_uses_immediately_prior_quarter_only():
    summary = mortgage_transition_summary(["C", "M", "2", "3", "3"])
    assert summary["repeated_transitions"] == {"2": 1}
    assert summary["first_event_from"] == "2"


def test_first_event_without_prior_baseline_is_not_backfilled():
    summary = mortgage_transition_summary(["3", "3", "C", "4"])
    assert summary["repeated_transitions"] == {"C": 1}
    assert summary["first_event_from"] is None
    assert summary["first_event_has_observed_prior"] is False


def test_competing_7_to_9_states_are_not_primary_events():
    summary = mortgage_transition_summary(["C", "7", "C", "9"])
    assert summary["repeated_transitions"] == {}
    assert summary["first_event_observed"] is False
