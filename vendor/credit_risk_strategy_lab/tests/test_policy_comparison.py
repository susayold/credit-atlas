import pytest
from crsl.policy.comparison import common_cohort


def fixture():
    labels = [dict(loan_id=str(i), landmark='2012-01-01', original_upb=100,
        eligibility_reason='eligible' if i < 3 else 'ineligible',
        target=[1, 0, None, None][i], label_known_month='2013-01-01') for i in range(4)]
    decisions = [dict(record_id=str(i), as_of='2012-01-01', original_upb='100',
        base_eligible=i < 3, decision='selected' if i < 3 else 'data_ineligible') for i in range(4)]
    return labels, decisions, [dict(r) for r in decisions]


def test_attrition_preserves_common_base_and_missing_policy_data():
    labels, base, candidate = fixture()
    candidate[1]['decision'] = 'data_ineligible'
    rows, audit = common_cohort(labels, base, candidate, evaluation_cutoff='2014-01-01')
    assert len(rows) == 2 and not rows[1]['candidate_selected']
    assert audit['exclusions'] == {'endpoint_unavailable': 1, 'entry_ineligible': 1}


def test_cutoff_equality_excluded():
    rows, audit = common_cohort(*fixture(), evaluation_cutoff='2013-01-01')
    assert rows == [] and audit['exclusions']['not_known_before_cutoff'] == 2


@pytest.mark.parametrize('field,value', [('as_of', '2012-02-01'), ('original_upb', '101'),
                                      ('base_eligible', False), ('decision', 'approved')])
def test_mismatched_decisions_fail(field, value):
    labels, base, candidate = fixture()
    candidate[0][field] = value
    with pytest.raises(ValueError):
        common_cohort(labels, base, candidate, evaluation_cutoff='2014-01-01')


def test_missing_loan_never_inner_joined_away():
    labels, base, candidate = fixture()
    with pytest.raises(ValueError, match='universe'):
        common_cohort(labels, base, candidate[:-1], evaluation_cutoff='2014-01-01')
