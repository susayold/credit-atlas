import csv

from scripts.audit_nsmo_first_entry_risk_set import classify_first_entry_path, audit


def test_first_entry_and_adjacent_risk_intervals_stop_at_first_observed_event():
    quarters = [2013 * 12 + month for month in (3, 6, 9, 12)]
    result = classify_first_entry_path(["Q", "C", "C", "3"], quarters, 2013, 1, None)
    assert result["entry"] is True
    assert result["entry_state"] == "C"
    assert result["exit"] == "observed_90plus"
    assert result["intervals"] == {"C": 2}


def test_pre_entry_event_does_not_enter_incident_risk_set():
    quarters = [2013 * 12 + month for month in (3, 6, 9)]
    result = classify_first_entry_path(["Q", "4", "C"], quarters, 2013, 1, None)
    assert result == {"entry": False, "reason": "pre_entry_observed_90plus"}


def test_other_adverse_status_competes_after_entry():
    quarters = [2013 * 12 + month for month in (3, 6, 9)]
    result = classify_first_entry_path(["Q", "1", "8"], quarters, 2013, 1, None)
    assert result["entry_state"] == "1"
    assert result["exit"] == "competing_adverse_8"
    assert result["intervals"] == {"1": 1}


def test_same_month_and_earlier_termination_end_risk_interval_before_status():
    quarters = [2013 * 12 + month for month in (3, 6, 9)]
    ambiguous = classify_first_entry_path(["Q", "C", "A"], quarters, 2013, 1, quarters[2])
    earlier = classify_first_entry_path(["Q", "C", "A"], quarters, 2013, 1, quarters[1] + 1)
    assert ambiguous["exit"] == "termination_same_month_ambiguous"
    assert earlier["exit"] == "termination_competing"


def test_nonobservation_censors_instead_of_becoming_negative():
    quarters = [2013 * 12 + month for month in (3, 6, 9)]
    result = classify_first_entry_path(["Q", "C", "M"], quarters, 2013, 1, None)
    assert result["exit"] == "observation_censor_M"


def test_close_before_first_eligible_baseline_excludes_entry():
    quarters = [2013 * 12 + month for month in (3, 6, 9)]
    result = classify_first_entry_path(["Q", "A", "C"], quarters, 2013, 1, quarters[1] - 1)
    assert result == {"entry": False, "reason": "termination_before_entry"}
