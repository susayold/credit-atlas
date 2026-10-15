"""P5 native-frequency rate/spread facts, alignment and inspectable source evidence."""
from __future__ import annotations

import csv
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .public_sources import catalog
from .public_suite import verify_acquisition
from .workspace import contained, read_json, sha256, timestamp, write_new

SERIES = ('DGS2', 'DGS10', 'DGS30', 'BAMLC0A0CM', 'MORTGAGE30US')
MISSING = ('', '.')
SCHEMA = pa.schema([('series', pa.string()), ('observation_date', pa.date32()),
                    ('source_value_percent', pa.decimal128(18, 6)),
                    ('value_percent', pa.decimal128(18, 6)), ('source_value', pa.string()),
                    ('documented_discontinuation_conflict', pa.bool_())])
METHODS = ('market_data', 'public_sources', 'public_suite', 'workspace')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in METHODS}


def native_rows(path, series):
    if series not in SERIES:
        raise ValueError('Unsupported market series')
    result, previous = [], None
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['observation_date', series]:
            raise ValueError('Market series header mismatch')
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('Malformed market CSV')
            observed = date.fromisoformat(row['observation_date'])
            if previous is not None and observed <= previous:
                raise ValueError('Duplicate/unordered native observation dates')
            previous = observed
            raw = row[series]
            value = None
            if raw not in MISSING:
                try:
                    value = Decimal(raw)
                except InvalidOperation as error:
                    raise ValueError('Invalid market percentage') from error
                if (not value.is_finite() or abs(value) >= 10**12
                        or value != value.quantize(Decimal('.000001'))):
                    raise ValueError('Market percentage precision/nonfinite value')
            conflict = (series == 'DGS30' and date(2002, 2, 18) <= observed < date(2006, 2, 9)
                        and value is not None)
            result.append({'series': series, 'observation_date': observed,
                           'source_value_percent': value, 'value_percent': None if conflict else value,
                           'source_value': raw, 'documented_discontinuation_conflict': conflict})
    if not result:
        raise ValueError('Empty market series')
    return result


def prepare_market(root, suite_id):
    root = root.resolve()
    source, acquisition = verify_acquisition(root, suite_id)
    source_digest, frozen_methods = sha256(source / 'acquisition-complete.json'), methods()
    source_by_id = {item['source_id']: item for item in acquisition['sources']}
    selected = []
    facts, profiles = [], []
    for series in SERIES:
        item = source_by_id['fred-' + series.lower()]
        if item['status'] != 'DOWNLOADED_AND_PROFILED':
            raise ValueError('Required market source unavailable')
        rows = native_rows(source / item['file'], series)
        if len(rows) != item['profile']['rows']:
            raise ValueError('Market source count mismatch')
        selected.append(item)
        facts.extend(rows)
        known = [row for row in rows if row['value_percent'] is not None]
        if not known:
            raise ValueError('Market series has no known observations')
        profiles.append({'series': series, 'rows': len(rows), 'known': len(known),
            'missing': len(rows) - len(known), 'first_native_date': rows[0]['observation_date'].isoformat(),
            'source_known': sum(row['source_value_percent'] is not None for row in rows),
            'source_missing': sum(row['source_value_percent'] is None for row in rows),
            'quarantined': sum(row['documented_discontinuation_conflict'] for row in rows),
            'last_native_date': rows[-1]['observation_date'].isoformat(),
            'last_known_date': known[-1]['observation_date'].isoformat(),
            'last_known_percent': str(known[-1]['value_percent']),
            'unit': 'percent', 'frequency': 'weekly_source_native_dates' if series == 'MORTGAGE30US' else 'daily_source_native_dates',
            'source_id': item['source_id'], 'source_sha256': item['sha256'],
            'source_url': item['metadata_url'], 'retrieved_at': item['retrieved_at'],
            'rights': item['rights']})
    identifier = 'market-case-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    write_new(output / 'run-start.json', {'started_at': timestamp(), 'suite_id': suite_id,
              'source_receipt_sha256': source_digest, 'methods': frozen_methods})
    table = pa.Table.from_pylist(facts, schema=SCHEMA)
    pq.write_table(table, output / 'native-observations.parquet', compression='zstd')
    with duckdb.connect() as con:
        con.read_parquet(str(output / 'native-observations.parquet')).create_view('facts')
        con.register('typed', table)
        roundtrip = con.execute('''SELECT count(*) FROM ((SELECT * FROM typed EXCEPT ALL SELECT * FROM facts)
            UNION ALL (SELECT * FROM facts EXCEPT ALL SELECT * FROM typed))''').fetchone()[0]
        reconciliations = []
        for item, series in zip(selected, SERIES):
            con.sql("SELECT * FROM read_csv(?, header=true, all_varchar=true, "
                    "nullstr='__MARKET_NO_NATIVE_NULL__', sample_size=-1)",
                    params=[str(source / item['file'])]).create_view('raw', replace=True)
            differing = con.execute(f'''WITH native AS (SELECT ?::VARCHAR AS series,
                observation_date::DATE AS observation_date,
                CASE WHEN "{series}" IN ('', '.') THEN NULL
                    ELSE CAST("{series}" AS DECIMAL(18,6)) END AS source_value_percent,
                "{series}"::VARCHAR AS source_value FROM raw), expected AS (
                SELECT series, observation_date, source_value_percent,
                    CASE WHEN series='DGS30' AND observation_date>=DATE '2002-02-18'
                       AND observation_date<DATE '2006-02-09' THEN NULL ELSE source_value_percent END AS value_percent,
                    source_value, (series='DGS30' AND observation_date>=DATE '2002-02-18'
                       AND observation_date<DATE '2006-02-09' AND source_value_percent IS NOT NULL)
                       AS documented_discontinuation_conflict FROM native), saved AS (
                SELECT * FROM facts WHERE series=?) SELECT count(*) FROM (
                (SELECT * FROM expected EXCEPT ALL SELECT * FROM saved) UNION ALL
                (SELECT * FROM saved EXCEPT ALL SELECT * FROM expected))''', [series, series]).fetchone()[0]
            reconciliations.append({'series': series, 'differing_rows': differing})
        if roundtrip or any(row['differing_rows'] for row in reconciliations):
            raise ValueError('Independent market CSV/Parquet reconciliation failed')
        projected = []
        for series in SERIES[:4]:
            key = series.lower()
            projected.extend([f"max(value_percent) FILTER(WHERE series='{series}') AS {key}_percent",
                              f"max(source_value_percent) FILTER(WHERE series='{series}') AS {key}_source_value_percent",
                              f"coalesce(bool_or(documented_discontinuation_conflict) FILTER(WHERE series='{series}'), false) AS {key}_quarantined",
                              f"count(*) FILTER(WHERE series='{series}')>0 AS {key}_native_present"])
        con.execute('CREATE VIEW daily AS SELECT observation_date, ' + ','.join(projected)
                    + " FROM facts WHERE series<>'MORTGAGE30US' GROUP BY observation_date")
        aligned = con.execute('''SELECT *, (dgs10_percent-dgs2_percent)*100 AS slope_10y_2y_bps,
            (dgs30_percent-dgs10_percent)*100 AS slope_30y_10y_bps,
            bamlc0a0cm_percent*100 AS corporate_index_oas_bps,
            (dgs2_percent IS NOT NULL AND dgs10_percent IS NOT NULL AND dgs30_percent IS NOT NULL)
                AS treasury_three_tenors_known FROM daily ORDER BY observation_date''').to_arrow_table()
        pq.write_table(aligned, output / 'aligned-daily-context.parquet', compression='zstd')
        monthly = con.execute('''SELECT series, date_trunc('month', observation_date)::DATE AS month,
            count(*) AS native_rows, count(value_percent) AS known_rows,
            count(*)-count(value_percent) AS missing_rows,
            count(*) FILTER(WHERE documented_discontinuation_conflict) AS quarantined_rows,
            count(*) FILTER(WHERE source_value_percent IS NULL) AS source_missing_rows,
            min(value_percent) AS min_percent, max(value_percent) AS max_percent,
            avg(value_percent) AS mean_percent,
            max(observation_date) FILTER(WHERE value_percent IS NOT NULL) AS last_known_date,
            arg_max(value_percent, observation_date) AS last_known_percent
            FROM facts GROUP BY series, month ORDER BY series, month''').to_arrow_table()
        pq.write_table(monthly, output / 'monthly-context.parquet', compression='zstd')
        coverage = con.execute('''SELECT count(*) AS aligned_dates,
            count(*) FILTER(WHERE dgs2_percent IS NOT NULL AND dgs10_percent IS NOT NULL AND dgs30_percent IS NOT NULL) AS three_tenor_known_dates,
            count(*) FILTER(WHERE dgs2_percent IS NOT NULL AND dgs10_percent IS NOT NULL AND dgs30_percent IS NOT NULL AND bamlc0a0cm_percent IS NOT NULL) AS three_tenor_plus_oas_known_dates,
            min(observation_date)::VARCHAR AS first_date, max(observation_date)::VARCHAR AS last_date
            FROM daily''').to_arrow_table().to_pylist()[0]
    contract = {'units': 'Percent for five source series; 1 percentage point = 100 basis points.',
        'alignment': 'Exact native-date outer join of four daily series; no fill/interpolation.',
        'native_present': 'Native-present flags distinguish absent rows; source-value and quarantine flags distinguish raw missing from reviewed excluded usable values.',
        'weekly': 'MORTGAGE30US kept native weekly dates, never promoted to daily observations.',
        'treasury': 'Constant-maturity par-yield context; not bootstrapped zero/discount curve or security quote.',
        'slope': '(10Y-2Y) and (30Y-10Y) in basis points, only if both same-date values known.',
        'oas': 'Investment-grade corporate index option-adjusted spread; not issuer/CDS/deal-specific quote.',
        'dgs30_break': 'FRED documents discontinuation 2002-02-18 to 2006-02-09. Payload values in that interval are preserved as source values but quarantined from usable rates pending provenance resolution.',
        'oas_coverage': 'FRED notes: only three years since April 2026; month-end weekend rows can occur.',
        'mortgage_break': 'PMMS methodology changed 2022-11-17; historical native dates retained.',
        'monthly': 'Summaries of available native observations, not complete calendar-month assertions.',
        'availability': 'Latest-revised retrieval; historical publication/availability times unknown.',
        'rights': 'ICE data/derived summaries internal use only; all outputs private, no external publication approval.',
        'source_links': [profile['source_url'] for profile in profiles] + [
            'https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology']}
    write_new(output / 'contract.json', contract)
    # Recheck only this case's source bytes after derivation; full batch was verified at intake.
    for item in selected:
        if sha256(source / item['file']) != item['sha256']:
            raise ValueError('Market source changed during preparation')
    if source_digest != sha256(source / 'acquisition-complete.json') or frozen_methods != methods():
        raise ValueError('Market acquisition/implementation changed during preparation')
    receipt = {'case_id': identifier, 'status': 'MARKET_CONTEXT_COMPLETE', 'completed_at': timestamp(),
        'suite_id': suite_id, 'source_receipt_sha256': source_digest,
        'sources': selected, 'profiles': profiles, 'native_records': len(facts),
        'coverage': coverage, 'monthly_records': monthly.num_rows,
        'independent_reconciliations': reconciliations, 'roundtrip_differing_rows': roundtrip,
        'quarantined_records': sum(profile['quarantined'] for profile in profiles),
        'historical_treasury_semantics_qualified': not any(profile['quarantined'] for profile in profiles),
        'methods': frozen_methods, 'visibility': 'private', 'public_release_approved': False,
        'security_price_qualified': False, 'cds_curve_qualified': False,
        'files': [{'file': path.name, 'sha256': sha256(path), 'bytes': path.stat().st_size}
                  for path in sorted(output.iterdir()) if path.is_file()]}
    write_new(output / 'market-complete.json', receipt)
    return receipt


def verify_market(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'market-case-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid market case identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'market-complete.json')
    if (receipt['case_id'] != identifier or receipt['status'] != 'MARKET_CONTEXT_COMPLETE'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private'
            or any(receipt[key] is not False for key in ('public_release_approved', 'security_price_qualified', 'cds_curve_qualified'))):
        raise ValueError('Market case implementation/qualification changed')
    if not re.fullmatch(r'suite-[0-9a-f]{12}', receipt['suite_id']):
        raise ValueError('Invalid market source suite')
    source = contained(root, 'data/private/public-suite/' + receipt['suite_id'])
    start = read_json(folder / 'run-start.json')
    if (start['suite_id'] != receipt['suite_id'] or start['methods'] != receipt['methods']
            or start['source_receipt_sha256'] != receipt['source_receipt_sha256']):
        raise ValueError('Market start/completion lineage changed')
    if sha256(source / 'acquisition-complete.json') != receipt['source_receipt_sha256']:
        raise ValueError('Market acquisition receipt changed')
    batch = read_json(source / 'acquisition-complete.json')
    expected = {item['source_id']: item for item in catalog()}
    if [item['source_id'] for item in receipt['sources']] != ['fred-' + series.lower() for series in SERIES]:
        raise ValueError('Market source population changed')
    for item in receipt['sources']:
        spec = expected[item['source_id']]
        if (any(item.get(key) != value for key, value in spec.items())
                or item['status'] != 'DOWNLOADED_AND_PROFILED'
                or item['model_qualified'] is not False or item['public_release_approved'] is not False
                or item not in batch['sources']
                or read_json(source / (item['source_id'] + '-receipt.json')) != item):
            raise ValueError('Market per-source contract changed')
        path = contained(source, item['file'])
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Market source bytes changed')
    expected_files = {'run-start.json', 'contract.json', 'native-observations.parquet',
                      'aligned-daily-context.parquet', 'monthly-context.parquet'}
    if (len(receipt['files']) != len(expected_files) or {item['file'] for item in receipt['files']} != expected_files
            or receipt['native_records'] != sum(item['rows'] for item in receipt['profiles'])
            or any(item['differing_rows'] != 0 for item in receipt['independent_reconciliations'])
            or receipt['roundtrip_differing_rows'] != 0):
        raise ValueError('Market output/coverage contract changed')
    if ([item['series'] for item in receipt['profiles']] != list(SERIES)
            or any(profile['rows'] != item['profile']['rows']
                or profile['known'] + profile['missing'] != profile['rows']
                or profile['source_known'] + profile['source_missing'] != profile['rows']
                or profile['known'] + profile['quarantined'] != profile['source_known']
                or profile['source_sha256'] != item['sha256']
                for profile, item in zip(receipt['profiles'], receipt['sources']))):
        raise ValueError('Market profile/source counts changed')
    if (receipt['quarantined_records'] != sum(profile['quarantined'] for profile in receipt['profiles'])
            or receipt['historical_treasury_semantics_qualified'] != (receipt['quarantined_records'] == 0)):
        raise ValueError('Market semantic quarantine status changed')
    for item in receipt['files']:
        path = contained(folder, item['file'])
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Market output bytes changed')
    if pq.read_metadata(folder / 'native-observations.parquet').num_rows != receipt['native_records']:
        raise ValueError('Market native record count changed')
    if (pq.read_metadata(folder / 'aligned-daily-context.parquet').num_rows != receipt['coverage']['aligned_dates']
            or pq.read_metadata(folder / 'monthly-context.parquet').num_rows != receipt['monthly_records']):
        raise ValueError('Market aligned/monthly counts changed')
    return folder, receipt
