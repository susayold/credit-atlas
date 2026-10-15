"""Synthetic API-shaped fixtures only. No observed macro values are claimed."""
import copy
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from crsl.macro import (FredClient, MacroIndex, MacroUnavailable, fetch_run,
                        fetch_series, join_records, join_run, load_index, normalize, parse_date, validate_forecast_inputs,
                        validate_metadata)

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'configs/macro.json').read_text())
SPEC = CONFIG['series']['UNRATE']


def observation(period='2012-01-01', start='2012-02-03', end='9999-12-31', value='12.0'):
    return dict(date=period, realtime_start=start, realtime_end=end, value=value)


def index(rows):
    return MacroIndex(normalize(rows, 'UNRATE', SPEC), {'UNRATE': SPEC})


def test_old_reference_released_after_landmark_not_joined_t17():
    macro = index([observation()])
    assert macro.select('UNRATE', '2012-02-01')['value'] is None
    assert macro.select('UNRATE', '2012-02-03')['value'] is None  # date-only conservative rule
    assert macro.select('UNRATE', '2012-02-04')['value'] == '12.0'


def test_revision_after_scoring_never_used_in_past():
    macro = index([observation(end='2012-03-01'), observation(start='2012-03-02', value='13.0')])
    assert macro.select('UNRATE', '2012-03-02')['value'] == '12.0'
    assert macro.select('UNRATE', '2012-03-03')['value'] == '13.0'
    comparison = macro.compare_revision('UNRATE', '2012-01-01', '2012-02-04', '2012-03-03')
    assert comparison['revision_delta'] == '1.0'
    assert comparison['use'] == 'retrospective_revision_comparison_not_predictive_feature'


def test_latest_reference_does_not_mean_latest_revision():
    macro = index([observation(end='2012-03-01'), observation(start='2012-03-02', value='13.0'),
                   observation('2012-02-01', '2012-03-09', value='15.0')])
    assert macro.select('UNRATE', '2012-03-05')['reference_period'] == '2012-01-01'
    assert macro.select('UNRATE', '2012-03-10')['reference_period'] == '2012-02-01'


def test_stale_value_unavailable_not_unlimited_forward_fill():
    result = index([observation()]).select('UNRATE', '2012-06-01')
    assert result['status'] == 'stale' and result['value'] is None


def test_withdrawn_revision_does_not_resurrect_old_value():
    result = index([observation(end='2012-03-01'), observation(start='2012-03-02', value='.')]).select('UNRATE', '2012-03-03')
    assert result['status'] == 'source_missing' and result['value'] is None


def test_gap_in_revision_coverage_is_unavailable():
    result = index([observation(end='2012-03-01')]).select('UNRATE', '2012-03-03')
    assert result['status'] == 'unavailable_revision_window'


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity', '', 'not-a-number'])
def test_nonfinite_and_invalid_source_numbers_fail(value):
    with pytest.raises(ValueError):
        normalize([observation(value=value)], 'UNRATE', SPEC)


def test_zero_is_not_missing():
    assert index([observation(value='0')]).select('UNRATE', '2012-02-04')['value'] == '0'


def test_overlap_and_duplicate_intervals_fail():
    with pytest.raises(ValueError, match='Overlapping'):
        index([observation(), observation()])


def test_invalid_reference_calendar_fails():
    with pytest.raises(ValueError, match='first of month'):
        index([observation(period='2012-01-15')])
    with pytest.raises(ValueError, match='quarter'):
        normalize([observation(period='2012-02-01')], 'USSTHPI', CONFIG['series']['USSTHPI'])


def test_forecast_future_actual_macro_rejected_t31():
    row = dict(evidence_class='observed_vintage', available_at='2012-03-10', reference_end='2012-02-29')
    with pytest.raises(ValueError, match='released after'):
        validate_forecast_inputs([row], '2012-03-01')
    with pytest.raises(ValueError, match='Future actual'):
        validate_forecast_inputs([{**row, 'available_at': '2012-02-01'}], '2012-02-01')


def test_explicit_scenario_and_oracle_labels_required():
    with pytest.raises(ValueError, match='masquerade'):
        validate_forecast_inputs([{'evidence_class': 'observed_vintage'}], '2012-01-01', 'scenario')
    validate_forecast_inputs([{'evidence_class': 'scenario'}], '2012-01-01', 'scenario')
    validate_forecast_inputs([{'evidence_class': 'oracle_sensitivity'}], '2012-01-01', 'oracle_sensitivity')


def test_metadata_unit_frequency_and_adjustment_checked():
    for key in ('units', 'frequency', 'seasonal_adjustment'):
        with pytest.raises(ValueError, match='mismatch'):
            validate_metadata({'seriess': [{'id': 'UNRATE', **SPEC, key: 'WRONG'}]}, 'UNRATE', SPEC)


def test_missing_key_never_fetches_latest(monkeypatch):
    monkeypatch.delenv('FRED_API_KEY', raising=False)
    with pytest.raises(MacroUnavailable, match='no latest-data fallback'):
        FredClient()


def test_mutating_feature_result_does_not_poison_cached_history():
    macro = index([observation()])
    first = macro.select('UNRATE', '2012-02-04')
    first['value'] = 'future-value'
    assert macro.select('UNRATE', '2012-02-04')['value'] == '12.0'


def test_datetime_cannot_silently_become_date_only():
    with pytest.raises(ValueError, match='date-only'):
        parse_date(datetime(2012, 1, 1, 8, 30))


class FixtureClient:
    def __init__(self, bad=None):
        self.bad = bad

    def get(self, endpoint, params):
        if endpoint == 'series':
            return {'seriess': [{'id': 'UNRATE', **SPEC}]}
        rows = [observation(end='2012-03-01'), observation(start='2012-03-02', end=CONFIG['realtime_end'], value='13.0')]
        offset = params['offset']
        payload = {'units': 'lin', 'output_type': 1, 'realtime_start': CONFIG['realtime_start'],
                   'realtime_end': CONFIG['realtime_end'], 'offset': offset, 'count': 2,
                   'observations': rows[offset:offset + params['limit']]}
        if self.bad == 'count_change' and offset:
            payload['count'] = 3
        if self.bad == 'wrong_units':
            payload['units'] = 'pc1'
        if self.bad == 'empty':
            payload['observations'] = []
        return payload


def test_pagination_retains_all_revisions():
    _, pages, rows = fetch_series(FixtureClient(), 'UNRATE', SPEC, CONFIG, page_size=1)
    assert len(pages) == 2 and len(rows) == 2


@pytest.mark.parametrize('bad', ['count_change', 'wrong_units', 'empty'])
def test_invalid_api_response_rejected(bad):
    with pytest.raises(ValueError):
        fetch_series(FixtureClient(bad), 'UNRATE', SPEC, CONFIG, page_size=1)


def test_missing_optional_macro_records_unavailable_without_core_failure(tmp_path, monkeypatch):
    monkeypatch.delenv('FRED_API_KEY', raising=False)
    run = fetch_run(tmp_path, CONFIG)
    result = json.loads((run / 'unavailable.json').read_text())
    assert result['status'] == 'MACRO_UNAVAILABLE'
    assert not result['core_pipeline_affected'] and not result['predictive_fallback_used']
    assert not (run / 'run-complete.json').exists()


def test_source_receipts_and_normalized_output(tmp_path):
    config = copy.deepcopy(CONFIG)
    config['series'] = {'UNRATE': SPEC}
    run = fetch_run(tmp_path, config, FixtureClient())
    assert (run / 'UNRATE-source.json').is_file()
    result = json.loads((run / 'run-complete.json').read_text())
    assert result['rows'] == 2 and not result['research_ready']
    assert load_index(run).select('UNRATE', '2012-02-04')['value'] == '12.0'


def test_landmark_join_preserves_unavailable_rows():
    macro = index([observation()])
    rows = list(join_records([('synthetic-a', '2012-02-01'), ('synthetic-b', '2012-02-04')], macro))
    assert len(rows) == 2 and rows[0]['value'] is None and rows[1]['value'] == '12.0'


def test_duplicate_landmark_fails():
    with pytest.raises(ValueError, match='Duplicate'):
        list(join_records([('synthetic', '2012-02-04')] * 2, index([observation()])))


def test_join_parquet_roundtrip(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from crsl.source import sha256
    config = copy.deepcopy(CONFIG)
    config['series'] = {'UNRATE': SPEC}
    macro_run = fetch_run(tmp_path, config, FixtureClient())
    labels = tmp_path / 'synthetic-labels'
    labels.mkdir()
    pq.write_table(pa.Table.from_pylist([{'loan_id': 'synthetic-a', 'landmark': date(2012, 2, 1)},
                                       {'loan_id': 'synthetic-b', 'landmark': date(2012, 2, 4)}]), labels / 'labels.parquet')
    (labels / 'run-complete.json').write_text(json.dumps({'status': 'LABELS_DEVELOPMENT_COMPLETE',
        'outputs_sha256': {'labels.parquet': sha256(labels / 'labels.parquet')}}))
    result = join_run(tmp_path, labels, macro_run)
    rows = pq.read_table(result / 'macro_features.parquet').to_pylist()
    assert len(rows) == 2 and rows[0]['value'] is None and rows[1]['value'] == 12.0
    assert rows[1]['value_raw_string'] == '12.0'


def test_tampered_cached_macro_fails_load(tmp_path):
    config = copy.deepcopy(CONFIG)
    config['series'] = {'UNRATE': SPEC}
    macro_run = fetch_run(tmp_path, config, FixtureClient())
    (macro_run / 'vintages.json').write_text('{"rows":[]}')
    with pytest.raises(ValueError, match='hash mismatch'):
        load_index(macro_run)


def test_api_error_never_echoes_credential(monkeypatch):
    from urllib.error import HTTPError
    key = 'x' * 32  # synthetic credential; no network call
    def fail(request, timeout):
        raise HTTPError(request.full_url, 403, 'forbidden ' + key, {}, None)
    monkeypatch.setattr('crsl.macro.urlopen', fail)
    with pytest.raises(MacroUnavailable) as error:
        FredClient(key).get('series', {'series_id': 'UNRATE'})
    assert key not in str(error.value)
    assert str(error.value) == 'FRED HTTP 403; no fallback'


def test_config_drift_invalidates_cached_macro(tmp_path):
    config = copy.deepcopy(CONFIG)
    config['series'] = {'UNRATE': SPEC}
    macro_run = fetch_run(tmp_path, config, FixtureClient())
    (macro_run / 'run-start.json').write_text('{"config":{}}')
    with pytest.raises(ValueError, match='hash mismatch'):
        load_index(macro_run)
