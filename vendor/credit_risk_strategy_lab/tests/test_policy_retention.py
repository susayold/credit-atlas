from decimal import Decimal

import pytest

from crsl.policy.retention import fixed_retention


def rows():
    return [dict(loan_id='a', principal=70, risk_score='.01'),
            dict(loan_id='b', principal=10, risk_score='.02'),
            dict(loan_id='c', principal=10, risk_score='.02'),
            dict(loan_id='d', principal=10, risk_score='.03')]


def select(data=None, target='.5', basis='count'):
    return fixed_retention(rows() if data is None else data, target=target,
                           basis=basis, evidence_class='synthetic_demo')


def test_boundary_tie_included_whole_and_overshoot_exposed():
    result = select()
    assert result['selected_count'] == 3
    assert Decimal(result['target_overshoot_fraction']) == Decimal('.25')
    assert result['boundary_group_count'] == 2


def test_principal_and_count_retention_are_not_interchangeable():
    assert select(basis='principal')['selected_count'] == 1
    assert select(basis='principal')['principal_retention'] == '0.7'


@pytest.mark.parametrize('target,expected', [('0', 0), ('1', 4), ('.25', 1)])
def test_endpoints_and_exact_boundary(target, expected):
    assert select(target=target)['selected_count'] == expected


def test_order_and_future_outcomes_do_not_change_ranking():
    assert select(list(reversed(rows()))) == select()
    assert select([{**r, 'actual_loss': -999, 'target': 1} for r in rows()]) == select()


@pytest.mark.parametrize('change', [dict(risk_score=None), dict(risk_score=True),
    dict(risk_score='NaN'), dict(risk_score='1.1'), dict(principal=0)])
def test_unscored_or_invalid_rows_cannot_disappear(change):
    data = rows()
    data[0].update(change)
    with pytest.raises(ValueError):
        select(data)


def test_duplicate_and_empty_cohort_rejected():
    with pytest.raises(ValueError):
        select(rows() * 2)
    with pytest.raises(ValueError):
        select([])
