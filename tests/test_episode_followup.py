from datetime import date

import pytest

from credit_atlas.episode_followup import audit_followup


def row(month, state="CURRENT", terminal=None):
    return date(2020, month, 1), state, terminal


def test_followup_starts_after_confirmation_and_requires_full_horizon():
    months = [row(m) for m in range(1, 8)]
    assert audit_followup(date(2020, 1, 1), months, 6) == ("complete_nonterminal_followup", 6)
    assert audit_followup(date(2020, 3, 1), months, 6) == ("end_of_source", 4)


def test_gap_unknown_and_terminal_cannot_become_complete_followup():
    anchor = date(2020, 1, 1)
    assert audit_followup(anchor, [row(1), row(3)], 6) == ("interrupted_gap", 0)
    assert audit_followup(anchor, [row(1), row(2), row(3, "UNKNOWN"), row(4)], 6) == ("interrupted_unknown", 1)
    assert audit_followup(anchor, [row(1), row(2), row(3, terminal="PREPAID_OR_MATURED")], 6) == ("terminal_exit", 1)
    assert audit_followup(anchor, [row(1, "D3PLUS", "CREDIT_TERMINATION"), row(2)], 6) == ("terminal_at_confirmation", 0)


def test_duplicate_and_missing_confirmation_cannot_enter_support_counts():
    with pytest.raises(ValueError):
        audit_followup(date(2020, 1, 1), [row(1), row(1)], 6)
    with pytest.raises(ValueError):
        audit_followup(date(2020, 2, 1), [row(1), row(3)], 6)
