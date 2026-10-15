from scripts.audit_nsmo_horizon_sensitivity import _classify


def test_horizon_sensitivity_uses_horizon_specific_no_event_label():
    statuses = ["C", "C", "C", "3", "A", "A", "A", "A", "A"]
    assert _classify(statuses, None, 0, 2) == "observed_no_90plus_within_2_quarters"
    assert _classify(statuses, None, 0, 4) == "observed_90plus_event"
    assert _classify(statuses, None, 0, 8) == "observed_90plus_event"


def test_horizon_sensitivity_preserves_incomplete_followup_as_censored():
    assert _classify(["C", "C", "C"], None, 0, 4) == "administratively_short_followup"
