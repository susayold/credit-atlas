import pytest

from crsl.losses import component_residual, first_terminal_records, summarize


def row(**changes):
    base = dict(loan_id='L1', period='2020-01-01', zero_balance_code='02', zero_balance_date='2020-01-01',
                actual_loss=-100, removal_upb=-1000, net_sales_proceeds=800,
                delinquent_accrued_interest=0, total_expenses=50, mi_recoveries=25, non_mi_recoveries=25,
                legal_costs=20, maintenance_costs=10, taxes_insurance=10, misc_expenses=10)
    base.update(changes)
    return base


def test_signed_components_reconcile_without_clipping():
    assert component_residual(row()) == 0
    summary = summarize([row()])
    assert summary['reported_loss_sum_usd'] == -100
    assert summary['severity_mean_uncapped'] == pytest.approx(0.1)


def test_repeated_terminal_rows_are_selected_once():
    rows = [row(), row(period='2020-02-01', zero_balance_date='2020-01-01', actual_loss=-999)]
    selected = first_terminal_records(rows)
    assert len(selected) == 1 and selected[0]['actual_loss'] == -100
    assert summarize(rows)['duplicate_terminal_rows_removed'] == 1


def test_missing_or_zero_denominator_stays_unavailable():
    summary = summarize([row(removal_upb=0), row(loan_id='L2', actual_loss=-50, removal_upb=None)])
    assert summary['severity_observation_loans'] == 0
    assert summary['severity_mean_uncapped'] is None
    assert summary['zero_or_missing_denominator_loans'] == 2


def test_partial_component_does_not_become_zero():
    summary = summarize([row(total_expenses=None)])
    assert summary['component_bridge'] is None
    assert summary['partial_component_rows'] == 1
