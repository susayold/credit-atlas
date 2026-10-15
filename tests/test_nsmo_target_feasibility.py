from collections import Counter, defaultdict

from scripts.audit_nsmo_target_feasibility import (
    _commit_unique_vintage_support,
    classify_followup,
    first_eligible_c_landmark,
)


def test_candidate_event_is_first_observed_90_plus_state():
    states = ["C", "1", "3", "A", "A"]
    assert classify_followup(states, None, 0) == "observed_90plus_event"


def test_adverse_non_90plus_state_is_separate():
    assert classify_followup(["C", "7", "A", "A", "A"], None, 0) == "observed_other_adverse_state_7"


def test_nonobservation_censors_before_later_event():
    assert classify_followup(["C", "M", "3", "3", "3"], None, 0) == "observation_censor_M"


def test_close_before_quarter_snapshot_is_competing_censor():
    # Baseline index 0 = 2013-03; index 1 = 2013-06 (ordinal 2013*12+6).
    assert classify_followup(["C", "A", "A", "A", "A"], 2013 * 12 + 5, 0) == "termination_competing_censor"


def test_close_in_snapshot_month_is_ambiguous():
    assert classify_followup(["C", "3", "A", "A", "A"], 2013 * 12 + 6, 0) == "termination_same_month_ambiguous"


def test_close_after_event_snapshot_does_not_erase_observed_event():
    assert classify_followup(["C", "3", "A", "A", "A"], 2013 * 12 + 7, 0) == "observed_90plus_event"


def test_incomplete_quarterly_horizon_is_not_negative():
    assert classify_followup(["C", "C", "C", "C", "C"], None, 47) == "administratively_short_followup"


def test_repeated_quarter_snapshots_do_not_inflate_unique_loan_support():
    group = ("2018", "C")
    unique_baselines = Counter()
    unique_outcomes = defaultdict(Counter)
    snapshot_count = Counter()

    # Two quarterly baselines of one mortgage count as two snapshots but one
    # unique loan for that outcome class.
    row_outcomes = set()
    for _ in range(2):
        snapshot_count[(group, "observed_90plus_event")] += 1
        row_outcomes.add((group, "observed_90plus_event"))
    _commit_unique_vintage_support(row_outcomes, unique_baselines, unique_outcomes)
    assert snapshot_count[(group, "observed_90plus_event")] == 2
    assert unique_baselines[group] == 1
    assert unique_outcomes[group]["observed_90plus_event"] == 1


def test_one_landmark_rule_selects_earliest_fully_followed_current_snapshot():
    states = ["C", "C", "1", "3", "A", "A"]
    assert first_eligible_c_landmark(states, None) == (0, "observed_90plus_event")


def test_one_landmark_rule_skips_baseline_known_closed_before_snapshot():
    # Index 0 is 2013-03. Closed in February means it was closed before that
    # quarter's endpoint; the later current-state snapshot cannot form a risk set.
    states = ["C", "C", "C", "C", "C"]
    assert first_eligible_c_landmark(states, 2013 * 12 + 2) is None
