from datetime import date

from scripts.audit_bondora_n14_readiness import add_twelve_calendar_months, label_class


def test_bondora_target_remains_three_valued():
    assert label_class(True) == "true"
    assert label_class(False) == "false"
    assert label_class(None) == "null"
    assert label_class(1) == "true"
    assert label_class(0) == "false"
    assert label_class("unknown") == "other"


def test_twelve_month_proxy_uses_calendar_anniversary_and_leap_day_clamp():
    issued = date(2025, 8, 10)
    maturity = add_twelve_calendar_months(issued)
    assert maturity == date(2026, 8, 10)
    assert not maturity <= date(2026, 8, 9)
    assert maturity <= date(2026, 8, 10)
    assert add_twelve_calendar_months(date(2024, 2, 29)) == date(2025, 2, 28)
