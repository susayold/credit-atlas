import datetime as dt

from crsl.behavioral import assert_no_future_leakage, build_landmark_features
from crsl.models.behavioral import BehavioralLogistic, current_state_baseline


def panel():
    rows = []
    for age in range(1, 17):
        state = 'CURRENT'
        if age == 6:
            state = 'D3PLUS'
        if age == 9:
            state = 'UNKNOWN'
        month = age - 1
        rows.append({'loan_id': 'L1', 'period': dt.date(2020 + month // 12, month % 12 + 1, 1),
                     'delinquency_state': state, 'current_upb': 100000 - age * 100})
    for age in range(1, 17):
        month = age - 1
        rows.append({'loan_id': 'L2', 'period': dt.date(2020 + month // 12, month % 12 + 1, 1),
                     'delinquency_state': 'CURRENT', 'current_upb': 90000 - age * 100})
    return rows


def test_landmark_features_are_history_only_and_exclude_event_landmarks():
    rows = panel()
    features = build_landmark_features(rows, horizon=3)
    assert_no_future_leakage(features, rows)
    assert all(r['current_state'] != 'D3PLUS' for r in features)
    row = next(r for r in features if r['loan_id'] == 'L1' and r['landmark'] == '2020-05-01')
    assert row['trailing_3_d3plus_count'] == 0
    assert row['target'] == 1
    changed = [dict(r, current_upb=999999) if r['loan_id'] == 'L1' and r['period'] > dt.date(2020, 5, 1) else r for r in rows]
    changed_row = next(r for r in build_landmark_features(changed, horizon=3) if r['loan_id'] == 'L1' and r['landmark'] == '2020-05-01')
    assert changed_row['trailing_3_d3plus_count'] == row['trailing_3_d3plus_count']


def test_unknown_or_gap_future_is_unavailable_not_zero():
    rows = [r for r in panel() if not (r['loan_id'] == 'L1' and r['period'] == dt.date(2020, 9, 1))]
    row = next(r for r in build_landmark_features(rows, horizon=3) if r['loan_id'] == 'L1' and r['landmark'] == '2020-08-01')
    assert row['target'] is None and row['target_reason'] == 'gap_before_horizon'


def test_baseline_and_logistic_keep_unavailable_out_of_rate():
    names = (
        'current_upb', 'current_upb_missing', 'history_months_available', 'history_has_gap',
        'months_since_last_d3plus', 'consecutive_current_months', 'trailing_3_d3plus_count',
        'trailing_3_unknown_count', 'trailing_3_state_usable_share', 'trailing_6_d3plus_count',
        'trailing_6_unknown_count', 'trailing_6_state_usable_share', 'trailing_12_d3plus_count',
        'trailing_12_unknown_count', 'trailing_12_state_usable_share', 'upb_change_from_prior_observed')
    base = {name: 0 for name in names}
    rows = []
    for i, target in enumerate([0, 1, None, 0]):
        rows.append({'loan_id': f'L{i}', 'landmark': '2020-01-01', 'current_state': 'CURRENT',
                     'target': target, 'partition': 'train', **base})
    summary = current_state_baseline(rows, minimum_support=1)
    assert summary['loans'] == 3 and summary['events'] == 1
    model = BehavioralLogistic().fit([r for r in rows if r['target'] is not None], fit_cutoff='2020-02-01')
    assert len(model.predict(rows)) == 4
