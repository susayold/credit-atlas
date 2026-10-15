"""Date-vintage macro adapter. Never substitute latest data into predictive history."""
import argparse
import bisect
import calendar
import json
import os
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .evidence_checks import require, require_hash
from .source import sha256, utc_now, write_json_new


class MacroUnavailable(RuntimeError):
    """Missing optional access is not authorization to use latest observations."""


def parse_date(value):
    if type(value) is date:
        return value
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Expected date-only YYYY-MM-DD')
    return date.fromisoformat(value)


def period_end(period, frequency):
    if frequency == 'Monthly':
        require(period.day == 1, 'Monthly reference must be first of month')
        return period.replace(day=calendar.monthrange(period.year, period.month)[1])
    if frequency == 'Quarterly':
        require(period.day == 1 and period.month in (1, 4, 7, 10), 'Invalid quarter reference')
        month = period.month + 2
        return date(period.year, month, calendar.monthrange(period.year, month)[1])
    if frequency == 'Weekly, Ending Thursday':
        # The source frequency is checked independently. Do not shift old dates.
        return period
    raise ValueError('Unsupported source frequency; no automatic resampling')


def validate_metadata(payload, series_id, spec):
    versions = payload.get('seriess', [])
    require(bool(versions), 'Missing series metadata')
    for item in versions:
        require(item['id'] == series_id, 'Series identifier mismatch')
        for key in ('units', 'frequency', 'seasonal_adjustment'):
            require(item[key] == spec[key], f'Macro {key} mismatch')


@dataclass(frozen=True)
class Revision:
    series_id: str
    reference_period: date
    reference_end: date
    realtime_start: date
    realtime_end: date
    value: Decimal | None
    units: str
    frequency: str
    revision_id: str

    @property
    def available_at(self):
        # Date-level source cannot establish an intraday release timestamp.
        return self.realtime_start + timedelta(days=1)


def normalize(observations, series_id, spec):
    result = []
    intervals = defaultdict(list)
    for row in observations:
        period = parse_date(row['date'])
        start, end = parse_date(row['realtime_start']), parse_date(row['realtime_end'])
        require(start <= end and start < date.max, 'Invalid real-time interval')
        reference_end = period_end(period, spec['frequency'])
        raw = row['value']
        require(isinstance(raw, str), 'Source value must be an unmodified API string')
        try:
            value = None if raw == '.' else Decimal(raw)
        except InvalidOperation:
            raise ValueError('Invalid macro numeric value') from None
        require(value is None or value.is_finite(), 'Non-finite macro value')
        revision = Revision(series_id, period, reference_end, start, end, value,
                            spec['units'], spec['frequency'], f'{series_id}:{period}:{start}')
        intervals[period].append(revision)
        result.append(revision)
    require(bool(result), 'Empty macro vintage history')
    for versions in intervals.values():
        versions.sort(key=lambda r: r.realtime_start)
        for left, right in zip(versions, versions[1:]):
            require(left.realtime_end < right.realtime_start, 'Overlapping or duplicate revision intervals')
    return sorted(result, key=lambda r: (r.reference_period, r.realtime_start))


class MacroIndex:
    def __init__(self, revisions, specs):
        self.specs = {key: dict(value) for key, value in specs.items()}
        grouped = defaultdict(list)
        for revision in revisions:
            require(revision.series_id in specs, 'Unconfigured macro series')
            spec = specs[revision.series_id]
            require(revision.units == spec['units'] and revision.frequency == spec['frequency'], 'Macro unit/frequency mismatch')
            require(revision.reference_end == period_end(revision.reference_period, revision.frequency), 'Reference calendar mismatch')
            require(revision.realtime_start <= revision.realtime_end and revision.realtime_start < date.max, 'Invalid revision interval')
            require(revision.value is None or revision.value.is_finite(), 'Invalid revision value')
            grouped[(revision.series_id, revision.reference_period)].append(revision)
        self.groups = {}
        self.starts = {}
        self.periods = defaultdict(list)
        for key, versions in grouped.items():
            versions.sort(key=lambda r: r.realtime_start)
            for left, right in zip(versions, versions[1:]):
                require(left.realtime_end < right.realtime_start, 'Overlapping revision intervals')
            self.groups[key] = tuple(versions)
            self.starts[key] = tuple(r.realtime_start for r in versions)
            self.periods[key[0]].append(key[1])
        for periods in self.periods.values():
            periods.sort(reverse=True)
        for spec in self.specs.values():
            require(type(spec['max_reference_age_days']) is int and spec['max_reference_age_days'] > 0,
                    'Positive finite staleness limit required')

    def select(self, series_id, information_cutoff):
        return dict(self._select(series_id, parse_date(information_cutoff)))

    @lru_cache(maxsize=8192)
    def _select(self, series_id, information_cutoff):
        """Latest reference known at the start of cutoff day, with an explicit status."""
        cutoff = parse_date(information_cutoff)
        require(cutoff > date.min, 'Invalid earliest information cutoff')
        require(series_id in self.specs, 'Unconfigured macro series')
        knowledge_date = cutoff - timedelta(days=1)
        for period in self.periods.get(series_id, ()):
            key = (series_id, period)
            position = bisect.bisect_right(self.starts[key], knowledge_date) - 1
            if position < 0:
                continue
            revision = self.groups[key][position]
            if revision.reference_end > knowledge_date:
                continue
            if revision.realtime_end < knowledge_date:
                return self._result('unavailable_revision_window', cutoff, revision)
            if (knowledge_date - revision.reference_end).days > self.specs[series_id]['max_reference_age_days']:
                return self._result('stale', cutoff, revision)
            if revision.value is None:
                return self._result('source_missing', cutoff, revision)
            return self._result('available', cutoff, revision)
        return {'series_id': series_id, 'information_cutoff': cutoff.isoformat(),
                'status': 'no_released_observation', 'value': None}

    def compare_revision(self, series_id, reference_period, information_cutoff, later_cutoff):
        """Same reference period at two information dates; later value is retrospective only."""
        period = parse_date(reference_period)
        cutoff, later = parse_date(information_cutoff), parse_date(later_cutoff)
        require(cutoff <= later and cutoff > date.min, 'Invalid revision comparison dates')
        require(series_id in self.specs, 'Unconfigured macro series')
        key = (series_id, period)
        def at(day):
            knowledge_date = day - timedelta(days=1)
            versions = self.groups.get(key, ())
            pos = bisect.bisect_right(self.starts.get(key, ()), knowledge_date) - 1
            if pos < 0 or versions[pos].realtime_end < knowledge_date or versions[pos].reference_end > knowledge_date:
                return None
            return versions[pos].value
        old, revised = at(cutoff), at(later)
        return {'series_id': series_id, 'reference_period': period.isoformat(),
                'information_cutoff': cutoff.isoformat(), 'later_cutoff': later.isoformat(),
                'asof_value': None if old is None else str(old),
                'revised_value': None if revised is None else str(revised),
                'revision_delta': None if old is None or revised is None else str(revised - old),
                'use': 'retrospective_revision_comparison_not_predictive_feature'}

    @staticmethod
    def _result(status, cutoff, revision):
        return {'series_id': revision.series_id, 'information_cutoff': cutoff.isoformat(),
                'status': status, 'reference_period': revision.reference_period.isoformat(),
                'reference_end': revision.reference_end.isoformat(),
                'available_at': revision.available_at.isoformat(),
                'revision_id': revision.revision_id, 'units': revision.units,
                'frequency': revision.frequency,
                'value': str(revision.value) if status == 'available' else None}


def validate_forecast_inputs(rows, origin, mode='predictive'):
    require(mode in ('predictive', 'scenario', 'oracle_sensitivity'), 'Unknown forecast input mode')
    origin = parse_date(origin)
    for row in rows:
        if mode == 'scenario':
            require(row.get('evidence_class') == 'scenario', 'Actual data cannot masquerade as a scenario')
        elif mode == 'oracle_sensitivity':
            require(row.get('evidence_class') == 'oracle_sensitivity', 'Oracle inputs require explicit labeling')
        else:
            require(row.get('evidence_class') == 'observed_vintage', 'Predictive path needs vintage observations')
            require(parse_date(row['available_at']) <= origin, 'Macro released after forecast origin')
            require(parse_date(row['reference_end']) < origin, 'Future actual macro path prohibited')


class FredClient:
    BASE = 'https://api.stlouisfed.org/fred/'

    def __init__(self, api_key=None):
        self._api_key = api_key if api_key is not None else os.environ.get('FRED_API_KEY', '')
        if not self._api_key:
            raise MacroUnavailable('FRED_API_KEY is not configured; no latest-data fallback')
        require(bool(re.fullmatch('[a-z0-9]{32}', self._api_key)), 'Invalid FRED API key format')

    def get(self, endpoint, params):
        require(endpoint in ('series', 'series/observations'), 'Unapproved FRED endpoint')
        url = self.BASE + endpoint + '?' + urlencode({**params, 'file_type': 'json', 'api_key': self._api_key})
        try:
            with urlopen(Request(url, headers={'User-Agent': 'CreditRiskStrategyLab/0.1'}), timeout=30) as response:
                raw = response.read(32 * 1024 * 1024 + 1)
            require(len(raw) <= 32 * 1024 * 1024, 'FRED response exceeds bounded request size')
            require(self._api_key.encode() not in raw, 'FRED response unexpectedly includes a credential')
            payload = json.loads(raw)
        except HTTPError as error:
            raise MacroUnavailable(f'FRED HTTP {error.code}; no fallback') from None
        except (URLError, TimeoutError):
            raise MacroUnavailable('FRED network unavailable; no fallback') from None
        return payload


def fetch_series(client, series_id, spec, config, page_size=100000):
    require(type(page_size) is int and 1 <= page_size <= 100000, 'Invalid FRED page size')
    params = {'series_id': series_id, 'realtime_start': config['realtime_start'], 'realtime_end': config['realtime_end']}
    metadata = client.get('series', params)
    validate_metadata(metadata, series_id, spec)
    pages, observations = [], []
    offset, expected_count = 0, None
    while True:
        request = {**params, 'observation_start': config['observation_start'], 'observation_end': config['observation_end'],
                   'units': 'lin', 'output_type': 1, 'sort_order': 'asc', 'limit': page_size, 'offset': offset}
        page = client.get('series/observations', request)
        require(page['units'] == 'lin' and page['output_type'] == 1, 'Transformed or non-interval macro response')
        require(page['realtime_start'] == params['realtime_start'] and page['realtime_end'] == params['realtime_end'],
                'Real-time request bounds not honored')
        require(page['offset'] == offset and type(page['count']) is int and 0 <= page['count'] <= 1000000,
                'Invalid or oversized pagination')
        if expected_count is None:
            expected_count = page['count']
        require(page['count'] == expected_count, 'Source count changed during pagination')
        batch = page['observations']
        require(bool(batch), 'Empty macro response or truncated pagination')
        require(len(batch) == min(page_size, expected_count - offset), 'Truncated macro page')
        pages.append({'request': request, 'response': page})
        observations.extend(batch)
        offset += len(batch)
        require(offset <= expected_count, 'Macro pagination exceeds source total')
        if offset == expected_count:
            break
    revisions = normalize(observations, series_id, spec)
    lower, upper = parse_date(config['observation_start']), parse_date(config['observation_end'])
    require(all(lower <= r.reference_period <= upper for r in revisions), 'Observation outside requested coverage')
    first, last = parse_date(config['realtime_start']), parse_date(config['realtime_end'])
    require(all(first <= r.realtime_start <= r.realtime_end <= last for r in revisions), 'Revision outside requested real-time window')
    return metadata, pages, revisions


def fetch_run(root, config, client=None):
    output = root / 'artifacts/private' / ('macro-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_json_new(output / 'run-start.json', {'started_at': utc_now(), 'config': config,
                   'visibility': 'private', 'public_release_approved': False, 'research_ready': False})
    try:
        client = FredClient() if client is None else client
        require(config['realtime_start'] == '1776-07-04', 'Full real-time history required; avoid clipped release dates')
        require(config['transformation'] == 'lin', 'Only source levels are supported')
        all_revisions = []
        for series_id, spec in config['series'].items():
            metadata, pages, revisions = fetch_series(client, series_id, spec, config)
            write_json_new(output / f'{series_id}-source.json', {'metadata': metadata, 'pages': pages})
            all_revisions.extend(revisions)
        # Constructing the index rechecks cross-file consistency.
        MacroIndex(all_revisions, config['series'])
        records = [{**r.__dict__, 'available_at': r.available_at} for r in all_revisions]
        records = [{key: (str(value) if isinstance(value, (date, Decimal)) else value)
                    for key, value in r.items()} for r in records]
        write_json_new(output / 'vintages.json', {'evidence_class': 'observed_vintage', 'rows': records})
        write_json_new(output / 'run-complete.json', {'status': 'MACRO_VINTAGES_FETCHED', 'completed_at': utc_now(),
                       'run_start_sha256': sha256(output / 'run-start.json'),
                       'series': list(config['series']), 'rows': len(records), 'visibility': 'private',
                       'public_release_approved': False, 'research_ready': False,
                       'outputs_sha256': {p.name: sha256(p) for p in output.glob('*-source.json')} |
                                         {'vintages.json': sha256(output / 'vintages.json')}})
    except MacroUnavailable as error:
        write_json_new(output / 'unavailable.json', {'status': 'MACRO_UNAVAILABLE', 'reason': str(error),
                       'core_pipeline_affected': False, 'predictive_fallback_used': False})
    except Exception as error:
        write_json_new(output / 'run-failed.json', {'status': 'MACRO_VALIDATION_FAILED', 'exception_type': type(error).__name__,
                       'core_pipeline_affected': False, 'predictive_fallback_used': False})
        raise
    return output


def load_index(macro_run):
    if not (macro_run / 'run-complete.json').exists():
        raise MacroUnavailable('No completed vintage acquisition; no predictive fallback')
    manifest = json.loads((macro_run / 'run-complete.json').read_text())
    require(manifest['status'] == 'MACRO_VINTAGES_FETCHED', 'Wrong macro artifact type')
    require_hash(macro_run / 'run-start.json', manifest['run_start_sha256'])
    for name, digest in manifest['outputs_sha256'].items():
        require(Path(name).name == name, 'Invalid macro artifact filename')
        require_hash(macro_run / name, digest)
    config = json.loads((macro_run / 'run-start.json').read_text())['config']
    payload = json.loads((macro_run / 'vintages.json').read_text())
    require(payload['evidence_class'] == 'observed_vintage', 'Latest-only input is not vintage evidence')
    revisions = []
    for row in payload['rows']:
        values = {key: value for key, value in row.items() if key != 'available_at'}
        for key in ('reference_period', 'reference_end', 'realtime_start', 'realtime_end'):
            values[key] = parse_date(values[key])
        values['value'] = None if values['value'] is None else Decimal(values['value'])
        revision = Revision(**values)
        require(revision.available_at == parse_date(row['available_at']), 'Availability date mismatch')
        revisions.append(revision)
    require(len(revisions) == manifest['rows'], 'Macro row count mismatch')
    return MacroIndex(revisions, config['series'])


def join_records(records, macro_index):
    """Preserve one row per loan landmark and configured series, including unavailable."""
    seen = set()
    for loan_id, landmark in records:
        landmark = parse_date(landmark)
        key = (loan_id, landmark)
        require(key not in seen, 'Duplicate loan landmark in macro join')
        seen.add(key)
        for series_id in macro_index.specs:
            yield {'loan_id': loan_id, **macro_index.select(series_id, landmark)}


def join_run(root, label_run, macro_run):
    import math
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq

    source = json.loads((label_run / 'run-complete.json').read_text())
    require(source['status'] == 'LABELS_DEVELOPMENT_COMPLETE', 'Completed label input required')
    label_file = label_run / 'labels.parquet'
    require_hash(label_file, source['outputs_sha256']['labels.parquet'])
    index = load_index(macro_run)
    output = root / 'artifacts/private' / ('macro-join-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    manifest = {'started_at': utc_now(), 'label_run': label_run.name, 'macro_run': macro_run.name,
                'label_sha256': sha256(label_file), 'macro_manifest_sha256': sha256(macro_run / 'run-complete.json'),
                'visibility': 'private', 'public_release_approved': False, 'research_ready': False,
                'claim': 'macro_date_vintage_safe_mortgage_latest_release_retrospective'}
    write_json_new(output / 'run-start.json', manifest)
    fields = ['loan_id', 'series_id', 'information_cutoff', 'status', 'reference_period', 'reference_end',
              'available_at', 'revision_id', 'units', 'frequency', 'value_raw_string']
    schema = pa.schema([(f, pa.string()) for f in fields] + [('value', pa.float64())])
    counts = defaultdict(int)
    total = 0
    try:
        with duckdb.connect() as db, pq.ParquetWriter(output / 'macro_features.parquet', schema, compression='zstd') as writer:
            query = db.read_parquet(str(label_file)).project('loan_id, landmark')
            expected = len(query) * len(index.specs)
            cursor = query.execute()
            def records():
                while batch := cursor.fetchmany(10000):
                    yield from batch
            buffer = []
            for row in join_records(records(), index):
                raw_value = row.pop('value')
                numeric = None if raw_value is None else float(raw_value)
                require(numeric is None or math.isfinite(numeric), 'Macro value cannot be represented numerically')
                buffer.append({**row, 'value_raw_string': raw_value, 'value': numeric})
                counts[(row['series_id'], row['status'])] += 1
                total += 1
                if len(buffer) == 10000:
                    writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
                    buffer = []
            if buffer:
                writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
            require(total == expected, 'Macro join changed cardinality')
        write_json_new(output / 'summary.json', {'rows': total,
                       'status_counts': [{'series_id': key[0], 'status': key[1], 'rows': n} for key, n in sorted(counts.items())]})
        manifest.update(status='MACRO_JOIN_COMPLETE', completed_at=utc_now(), rows=total,
                        outputs_sha256={'macro_features.parquet': sha256(output / 'macro_features.parquet')})
        write_json_new(output / 'run-complete.json', manifest)
    except Exception as error:
        write_json_new(output / 'run-failed.json', {'status': 'MACRO_JOIN_FAILED', 'exception_type': type(error).__name__})
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['fetch', 'join'])
    parser.add_argument('--label-run', type=Path)
    parser.add_argument('--macro-run', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / 'configs/macro.json').read_text())
    if args.command == 'fetch':
        print(fetch_run(root, config))
    else:
        if args.label_run is None or args.macro_run is None:
            parser.error('join requires --label-run and --macro-run')
        print(join_run(root, args.label_run.resolve(), args.macro_run.resolve()))
