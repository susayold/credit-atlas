from datetime import date
from decimal import Decimal

import pytest

from scripts.acquire_treasury_par_yields import (
    AcquisitionError,
    annual_url,
    compare_series,
    parse_treasury_csv,
)


def test_archive_and_current_csv_headers_normalize_to_native_tenors():
    archive = (
        b'date,1 mo,2 mo,3 mo,4 mo,6 mo,1 yr,2 yr,3 yr,5 yr,7 yr,10 yr,20 yr,30 yr\n'
        b'01/02/1990,,,,,,7.81,7.87,7.90,7.87,7.98,7.94,,8.00\n'
    )
    current = (
        b'Date,"1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr",'
        b'"2 Yr","3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"\n'
        b'10/16/2026,4.12,4.14,4.17,4.26,4.32,4.34,4.46,4.74,4.82,4.89,4.98,5.09,5.47,5.43\n'
    )
    old_rows = parse_treasury_csv(archive, "1990-2023")
    new_rows = parse_treasury_csv(current, "2026")
    assert old_rows == [{
        "observation_date": date(1990, 1, 2), "2YR": Decimal("7.87"),
        "10YR": Decimal("7.94"), "30YR": Decimal("8.00"),
    }]
    assert new_rows[0]["observation_date"] == date(2026, 10, 16)
    assert new_rows[0]["2YR"] == Decimal("4.74")
    assert new_rows[0]["10YR"] == Decimal("5.09")
    assert new_rows[0]["30YR"] == Decimal("5.43")


def test_official_missing_cells_remain_null_and_not_zero():
    body = b'Date,"2 Yr","10 Yr","30 Yr"\n02/19/2002,5.10,5.20,N/A\n'
    rows = parse_treasury_csv(body, "2002")
    assert rows[0]["2YR"] == Decimal("5.10")
    assert rows[0]["10YR"] == Decimal("5.20")
    assert rows[0]["30YR"] is None


@pytest.mark.parametrize("body,period", [
    (b'Date,"2 Yr","10 Yr","30 Yr"\n01/02/2025,1,2,3\n', "2024"),
    (b'Date,"2 Yr","10 Yr","30 Yr"\n01/02/2025,1,2,3\n01/02/2025,1,2,3\n', "2025"),
    (b'Date,"2 Yr","10 Yr","30 Yr"\n01/02/2025,1.12345,2,3\n', "2025"),
    (b'Date,"2 Yr","10 Yr","30 Yr"\n01/02/2025,NaN,2,3\n', "2025"),
])
def test_invalid_treasury_csv_is_rejected(body, period):
    with pytest.raises(AcquisitionError):
        parse_treasury_csv(body, period)


def test_fred_comparison_separates_exact_overlap_from_the_30y_gap_and_newer_dates():
    direct = [
        {"observation_date": date(2002, 2, 19), "2YR": Decimal("5.10"), "10YR": Decimal("5.20"), "30YR": None},
        {"observation_date": date(2026, 10, 16), "2YR": Decimal("4.74"), "10YR": Decimal("5.09"), "30YR": Decimal("5.43")},
    ]
    fred = {
        date(1989, 12, 29): Decimal("7.90"),
        date(2002, 2, 19): Decimal("4.91"),
    }
    result = compare_series(direct, fred, "30YR")
    assert result["same_calendar_dates"] == 1
    assert result["both_known_date_comparisons"] == 0
    assert result["common_date_treasury_missing_fred_known"] == 1
    assert result["treasury_known_dates_without_fred_calendar_row"] == 1
    assert result["fred_known_dates_without_treasury_calendar_row"] == 1
    assert result["common_date_treasury_missing_examples"] == ["2002-02-19"]
    assert result["common_date_both_missing_examples"] == []


def test_annual_url_is_constrained_to_the_official_treasury_csv_host():
    url = annual_url(2026)
    assert url.startswith("https://home.treasury.gov/")
    assert "/daily-treasury-rates.csv/2026/all?" in url
    assert "field_tdr_date_value=2026" in url
