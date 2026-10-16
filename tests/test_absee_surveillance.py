"""Contract-level checks for the public aggregate ABS surveillance release."""
from pathlib import Path

import pytest

from credit_atlas.absee_surveillance import report


ROOT = Path(__file__).resolve().parents[1]


def test_contract_aware_release_keeps_recovery_comparators_separate():
    result = report(ROOT)
    assert result["status"] == "PASS"
    assert result["period_count"] == 103
    assert result["deal_count"] == 3
    assert result["exception_period_count"] == 86
    assert result["recovery_exception_period_count"] == 83
    assert result["cross_deal_recovery_residual_total"] is None
    assert "differ by contract" in result["cross_deal_residual_note"]
    assert result["loan_level_rows_published"] is False
    assert result["forecast_or_imputation_used"] is False

    summaries = {item["deal_id"]: item for item in result["deal_summaries"]}
    assert summaries["TOYOTA-2022-B"]["recovery_comparator_id"] == "aggregate_net_liquidation_proceeds"
    assert summaries["TOYOTA-2022-B"]["recovery_tie_periods"] == 2
    assert summaries["TOYOTA-2022-B"]["recovery_exception_periods"] == 49
    assert summaries["TOYOTA-2024-B"]["recovery_tie_periods"] == 1
    assert summaries["TOYOTA-2024-B"]["recovery_exception_periods"] == 28
    assert summaries["NISSAN-2024-B"]["recovery_comparator_id"] == "recoveries_of_defaulted_receivables"
    assert summaries["NISSAN-2024-B"]["recovery_tie_periods"] == 17
    assert summaries["NISSAN-2024-B"]["recovery_exception_periods"] == 6


def test_july_chargeoff_and_june_dpd_exceptions_remain_source_linked():
    result = report(ROOT)
    rows = {row["deal_id"] + "/" + row["report_date"]: row for row in result["exceptions"]}
    july = rows["NISSAN-2024-B/2025-07-31"]
    assert july["asset_positive_chargeoff_event_count"] == "36"
    assert july["asset_chargeoff_amount_source_signed_usd"] == "655185.56000000"
    assert july["certificate_chargeoff_amount_source_signed_usd"] == "-59000.49"
    assert july["recovery_tie_status"] == "TIED"
    assert july["root_cause_resolved"] == "No"
    assert july["abs_ee_source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
    assert july["certificate_source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")

    june = rows["NISSAN-2024-B/2025-06-30"]
    assert june["dpd_literal_exact_fields"] == "2"
    assert june["dpd_total_field_checks"] == "8"
    assert "literal_dpd_bucket" in june["exception_categories"]


def test_release_has_no_filter_contract_yet():
    with pytest.raises(ValueError, match="accepts no filters"):
        report(ROOT, {"deal_id": "NISSAN-2024-B"})
