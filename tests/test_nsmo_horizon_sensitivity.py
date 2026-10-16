from scripts.audit_nsmo_horizon_sensitivity import (
    _classify, _first_eligible_c_landmark,
)
from scripts.audit_nsmo_target_feasibility import _quarter_ordinal


def test_horizon_sensitivity_uses_horizon_specific_no_event_label():
    statuses = ["C", "C", "C", "3", "A", "A", "A", "A", "A"]
    assert _classify(statuses, None, 0, 2) == "observed_no_90plus_within_2_quarters"
    assert _classify(statuses, None, 0, 4) == "observed_90plus_event"
    assert _classify(statuses, None, 0, 8) == "observed_90plus_event"


def test_horizon_sensitivity_preserves_incomplete_followup_as_censored():
    assert _classify(["C", "C", "C"], None, 0, 4) == "administratively_short_followup"


def test_one_landmark_sensitivity_uses_one_earliest_complete_c_anchor():
    assert _first_eligible_c_landmark(["C", "1", "3", "A"], None, 2012, 12, 2) == "observed_90plus_event"
    assert _first_eligible_c_landmark(["C", "C"], None, 2012, 12, 2) is None
    assert _first_eligible_c_landmark(
        ["C", "C", "C"], _quarter_ordinal(0), 2012, 12, 2
    ) is None


def test_horizon_landmark_excludes_origination_quarter_snapshot():
    states = ["C", "C", "C", "3", "A"]
    # April origination belongs to Q2; the first eligible anchor is Q3.
    assert _first_eligible_c_landmark(states, None, 2013, 4, 2) == "observed_90plus_event"
