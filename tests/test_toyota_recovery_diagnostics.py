from decimal import Decimal
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_toyota_recovery_components_ledger import summarize_reconciliation  # noqa: E402


def _period(deal, month, asset, certificate):
    delta = Decimal(asset) - Decimal(certificate)
    return {
        "deal": deal,
        "report_month": month,
        "asset_recovered_amount_signed": asset,
        "certificate_aggregate_net_liquidation_proceeds": certificate,
        "asset_minus_certificate_recovery_delta": str(delta),
        "recovery_reconciliation_status": "TIED" if delta == 0 else "UNRESOLVED",
    }


def test_reconciliation_diagnostics_use_exact_amounts_and_type7_quantiles():
    rows = [
        _period("2022-B", "2025-01", "100.00", "90.00"),
        _period("2022-B", "2025-02", "100.00", "80.00"),
        _period("2024-B", "2025-03", "300.00", "270.00"),
        _period("2024-B", "2025-04", "0.00", "0.00"),
        _period("2024-B", "2025-05", "0.00", "0.00"),
    ]

    result = summarize_reconciliation(rows)
    overall = result["overall"]

    assert result["quantile_method"].startswith("Hyndman-Fan Type 7")
    assert overall["periods"] == 5
    assert overall["ties"] == 2
    assert overall["periods_with_zero_abs_ee_recovered_amount"] == 2
    assert overall["unresolved_periods"] == 3
    assert overall["unresolved_residual_usd"] == "60.00"
    assert overall["residual_share_of_abs_ee_recovered_amount_percent"] == "12.00"
    assert overall["unresolved_residual_quantiles_usd"] == {
        "minimum": "10.00",
        "p25": "15.00",
        "median": "20.00",
        "p75": "25.00",
        "maximum": "30.00",
    }
    assert overall["top_five_unresolved_share_of_unresolved_residual_percent"] == "100.00"
    assert overall["per_period_unresolved_residual_share_of_abs_ee_amount_percent"] == {
        "eligible_periods": 3,
        "median": "10.00",
        "p75": "15.00",
    }
    assert result["by_report_year_combined_deals"][0]["report_year"] == "2025"


def test_top_five_concentration_is_suppressed_for_mixed_sign_residuals():
    rows = [
        _period("2022-B", "2025-01", "100.00", "90.00"),
        _period("2022-B", "2025-02", "100.00", "105.00"),
    ]

    result = summarize_reconciliation(rows)

    assert result["overall"]["negative_unresolved_periods"] == 1
    assert result["overall"]["top_five_unresolved_share_of_unresolved_residual_percent"] is None
