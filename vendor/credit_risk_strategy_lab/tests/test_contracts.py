import pytest
from crsl.contracts import validate_row, fields_for

def test_widths():
    assert len(fields_for("origination")) == 31
    assert len(fields_for("performance")) == 35

@pytest.mark.parametrize("table", ["origination", "performance"])
def test_valid_record(make_record, table):
    assert validate_row(make_record(table), table) == []

@pytest.mark.parametrize("table", ["origination", "performance"])
def test_wrong_width(make_record, table):
    assert validate_row(make_record(table)[:-1], table)[0].startswith("field_count")

@pytest.mark.parametrize("status", ["XX", "RA", "00", "03", "99"])
def test_documented_status(make_record, status):
    assert validate_row(make_record("performance", delinquency=status), "performance") == []

@pytest.mark.parametrize("status", ["", "0", "100", "AAA"])
def test_unknown_status(make_record, status):
    assert "delinquency_unknown" in validate_row(
        make_record("performance", delinquency=status), "performance")

@pytest.mark.parametrize("month", ["202613", "20261", "000000", "bad"])
def test_invalid_month(make_record, month):
    assert "period_invalid_month" in validate_row(
        make_record("performance", period=month), "performance")

def test_required_period(make_record):
    assert "period_required" in validate_row(make_record("performance", period=""), "performance")

@pytest.mark.parametrize("value", ["NaN", "Infinity", "bad"])
def test_nonfinite_numeric(make_record, value):
    assert "current_upb_invalid_numeric" in validate_row(
        make_record("performance", current_upb=value), "performance")

@pytest.mark.parametrize("value", ["299", "851", "720.5"])
def test_score_domain(make_record, value):
    assert "classic_fico_invalid_domain" in validate_row(
        make_record("origination", classic_fico=value), "origination")

def test_score_sentinel_not_normalized(make_record):
    row = make_record("origination", classic_fico="9999")
    assert validate_row(row, "origination") == []
    assert row[0] == "9999"

@pytest.mark.parametrize("quarter", ["5", "6"])
def test_example_quarter_never_passes_annual(make_record, quarter):
    row = make_record("origination", loan_id=f"F26Q{quarter}0000001")
    assert "loan_id_format" in validate_row(row, "origination")
    assert validate_row(row, "origination", format_example=True) == []

def test_example_does_not_allow_arbitrary_quarter(make_record):
    row = make_record("origination", loan_id="F26Q70000001")
    assert "loan_id_format" in validate_row(row, "origination", format_example=True)

def test_negative_recoveries_preserved(make_record):
    row = make_record("performance", mi_recoveries="-123.50")
    assert validate_row(row, "performance") == []
    assert row[13] == "-123.50"

