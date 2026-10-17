"""P5 native-frequency rate/spread facts, alignment and inspectable source evidence."""
from __future__ import annotations

import csv
import hashlib
import re
import uuid
from collections import Counter
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
TREASURY_SERIES = ('DGS2', 'DGS10', 'DGS30')
TREASURY_RUN = re.compile(r'treasury-par-yield-\d{8}T\d{6}Z-[0-9a-f]{8}\Z')
TREASURY_START = date(1990, 1, 2)
TREASURY_COLUMNS = {'DGS2': 'TREASURY2Y', 'DGS10': 'TREASURY10Y', 'DGS30': 'TREASURY30Y'}
MISSING = ('', '.')
SCHEMA = pa.schema([('series', pa.string()), ('observation_date', pa.date32()),
                    ('source_value_percent', pa.decimal128(18, 6)),
                    ('value_percent', pa.decimal128(18, 6)), ('source_value', pa.string()),
                    ('documented_discontinuation_conflict', pa.bool_()),
                    ('source_id', pa.string()), ('source_sha256', pa.string())])
METHODS = ('market_data', 'public_sources', 'public_suite', 'workspace')


def methods():
    result = {name: sha256(Path(__file__).with_name(name + '.py')) for name in METHODS}
    result['acquire_treasury_par_yields'] = sha256(
        Path(__file__).resolve().parents[2] / 'scripts' / 'acquire_treasury_par_yields.py')
    return result


def _treasury_normalized_rows(root, run_id):
    if not isinstance(run_id, str) or not TREASURY_RUN.fullmatch(run_id):
        raise ValueError('Invalid Treasury par-yield run identifier')
    folder = contained(root, 'data/private/market-context/treasury-par-yields/' + run_id)
    receipt_path = contained(folder, 'acquisition-audit.json')
    receipt = read_json(receipt_path)
    if (receipt.get('run_id') != run_id or receipt.get('status') != 'DOWNLOADED_AND_AUDITED'
            or receipt.get('visibility') != 'private' or receipt.get('public_release_approved') is not False
            or receipt.get('model_qualified') is not False
            or receipt.get('acquisition_method_sha256') != methods()['acquire_treasury_par_yields']):
        raise ValueError('Treasury direct source receipt/scope is invalid')
    manifest = {item.get('file'): item for item in receipt.get('files', [])}
    source_files = receipt.get('source_files', [])
    normalized = receipt.get('normalized_file', {})
    if (not source_files or len(source_files) < 2 or normalized.get('file') != 'normalized-treasury-par-yields.csv'
            or normalized.get('file') not in manifest):
        raise ValueError('Treasury direct source manifest is incomplete')
    for item in source_files:
        url = item.get('source_object_url', '')
        if (item.get('file') not in manifest or not url.startswith('https://home.treasury.gov/')
                or manifest[item['file']].get('sha256') != item.get('sha256')
                or manifest[item['file']].get('bytes') != item.get('bytes')):
            raise ValueError('Treasury source partition manifest is invalid')
    for filename, item in manifest.items():
        path = contained(folder, filename)
        if not path.is_file() or sha256(path) != item.get('sha256') or path.stat().st_size != item.get('bytes'):
            raise ValueError('Treasury source payload hash/size mismatch')
    normalized_path = contained(folder, normalized['file'])
    if sha256(normalized_path) != normalized.get('sha256') or normalized_path.stat().st_size != normalized.get('bytes'):
        raise ValueError('Treasury normalized payload hash/size mismatch')
    rows, previous = [], None
    with normalized_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['observation_date', 'TREASURY2Y', 'TREASURY10Y', 'TREASURY30Y']:
            raise ValueError('Treasury normalized data header changed')
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('Treasury normalized row is malformed')
            observed = date.fromisoformat(row['observation_date'])
            if observed < TREASURY_START or (previous is not None and observed <= previous):
                raise ValueError('Treasury normalized dates are outside range or unordered')
            previous = observed
            values = {}
            for series, column in TREASURY_COLUMNS.items():
                raw = row[column].strip()
                if raw in MISSING:
                    values[series] = None
                    continue
                try:
                    value = Decimal(raw)
                except InvalidOperation as error:
                    raise ValueError('Treasury normalized yield is not numeric') from error
                if (not value.is_finite() or value < 0 or value >= 100
                        or value != value.quantize(Decimal('.000001'))):
                    raise ValueError('Treasury normalized yield is out of contract')
                values[series] = value
            rows.append({'observation_date': observed, **values})
    if (len(rows) != receipt.get('native_rows') or not rows
            or rows[0]['observation_date'].isoformat() != receipt.get('first_date')
            or rows[-1]['observation_date'].isoformat() != receipt.get('last_date')):
        raise ValueError('Treasury normalized coverage does not match receipt')
    return folder, receipt, rows


def _row_with_source(row, source_id, source_sha256):
    return {**row, 'source_id': source_id, 'source_sha256': source_sha256}


def _legs_digest(legs):
    basis = '\n'.join(f"{leg['source_id']}|{leg['sha256']}|{leg['role']}" for leg in legs)
    return hashlib.sha256(basis.encode('utf-8')).hexdigest()


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


def prepare_market(root, suite_id, treasury_run_id=None):
    root = root.resolve()
    source, acquisition = verify_acquisition(root, suite_id)
    source_digest, frozen_methods = sha256(source / 'acquisition-complete.json'), methods()
    source_by_id = {item['source_id']: item for item in acquisition['sources']}
    treasury_folder, treasury_receipt, treasury_rows = (None, None, [])
    treasury_receipt_digest = None
    if treasury_run_id is not None:
        treasury_folder, treasury_receipt, treasury_rows = _treasury_normalized_rows(root, treasury_run_id)
        treasury_receipt_digest = sha256(treasury_folder / 'acquisition-audit.json')
    treasury_by_date = {row['observation_date']: row for row in treasury_rows}
    treasury_source_hash = treasury_receipt['normalized_file']['sha256'] if treasury_receipt else None
    selected = []
    facts, profiles, selected_rows = [], [], {}
    for series in SERIES:
        item = source_by_id['fred-' + series.lower()]
        if item['status'] != 'DOWNLOADED_AND_PROFILED':
            raise ValueError('Required market source unavailable')
        fred_rows = native_rows(source / item['file'], series)
        if len(fred_rows) != item['profile']['rows']:
            raise ValueError('Market source count mismatch')
        selected.append(item)
        legs = []
        if treasury_receipt is not None and series in TREASURY_SERIES:
            historical = [_row_with_source(row, item['source_id'], item['sha256'])
                          for row in fred_rows if row['observation_date'] < TREASURY_START]
            direct = []
            for observed in sorted(treasury_by_date):
                source_row = treasury_by_date[observed]
                if observed < TREASURY_START:
                    raise ValueError('Treasury direct series unexpectedly predates its registered coverage')
                value = source_row[series]
                conflict = series == 'DGS30' and date(2002, 2, 18) <= observed < date(2006, 2, 9) and value is not None
                direct.append(_row_with_source({
                    'series': series, 'observation_date': observed,
                    'source_value_percent': value,
                    'value_percent': None if conflict else value,
                    'source_value': '' if value is None else str(value),
                    'documented_discontinuation_conflict': conflict,
                }, 'treasury-daily-par-yield', treasury_source_hash))
            rows = sorted([*historical, *direct], key=lambda row: row['observation_date'])
            legs = [
                {'source_id': item['source_id'], 'sha256': item['sha256'],
                 'source_url': item['metadata_url'], 'role': 'historical_extension_before_1990-01-02',
                 'first_date': min((row['observation_date'] for row in historical), default=None).isoformat()
                    if historical else None,
                 'last_date': max((row['observation_date'] for row in historical), default=None).isoformat()
                    if historical else None},
                {'source_id': 'treasury-daily-par-yield', 'sha256': treasury_source_hash,
                 'source_url': treasury_receipt['source_files'][0]['source_page_url'],
                 'role': 'direct_publisher_from_1990-01-02',
                 'first_date': min(treasury_by_date).isoformat(), 'last_date': max(treasury_by_date).isoformat()},
            ]
        else:
            rows = [_row_with_source(row, item['source_id'], item['sha256']) for row in fred_rows]
            legs = [{'source_id': item['source_id'], 'sha256': item['sha256'],
                     'source_url': item['metadata_url'], 'role': 'native_source_snapshot',
                     'first_date': rows[0]['observation_date'].isoformat(),
                     'last_date': rows[-1]['observation_date'].isoformat()}]
        selected_rows[series] = rows
        facts.extend(rows)
        known = [row for row in rows if row['value_percent'] is not None]
        if not known:
            raise ValueError('Market series has no known observations')
        direct_mode = treasury_receipt is not None and series in TREASURY_SERIES
        profiles.append({'series': series, 'rows': len(rows), 'known': len(known),
            'missing': len(rows) - len(known), 'first_native_date': rows[0]['observation_date'].isoformat(),
            'source_known': sum(row['source_value_percent'] is not None for row in rows),
            'source_missing': sum(row['source_value_percent'] is None for row in rows),
            'quarantined': sum(row['documented_discontinuation_conflict'] for row in rows),
            'last_native_date': rows[-1]['observation_date'].isoformat(),
            'last_known_date': known[-1]['observation_date'].isoformat(),
            'last_known_percent': str(known[-1]['value_percent']),
            'unit': 'percent', 'frequency': 'weekly_source_native_dates' if series == 'MORTGAGE30US' else 'daily_source_native_dates',
            'source_id': ('treasury-daily-par-yield + ' + item['source_id'] + ' (pre-1990 only)') if direct_mode else item['source_id'],
            'source_sha256': _legs_digest(legs), 'source_legs': legs,
            'source_url': [leg['source_url'] for leg in legs],
            'retrieved_at': treasury_receipt['retrieved_at_utc'] if direct_mode else item['retrieved_at'],
            'rights': ('Treasury direct observations from 1990; FRED snapshot used only before 1990. Raw market data stay private; public redistribution and model use are not approved.'
                       if direct_mode else item['rights'])})
    identifier = 'market-case-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    write_new(output / 'run-start.json', {'started_at': timestamp(), 'suite_id': suite_id,
              'source_receipt_sha256': source_digest, 'methods': frozen_methods,
              'treasury_run_id': treasury_run_id, 'treasury_receipt_sha256': treasury_receipt_digest})
    table = pa.Table.from_pylist(facts, schema=SCHEMA)
    pq.write_table(table, output / 'native-observations.parquet', compression='zstd')
    with duckdb.connect() as con:
        con.read_parquet(str(output / 'native-observations.parquet')).create_view('facts')
        con.register('typed', table)
        roundtrip = con.execute('''SELECT count(*) FROM ((SELECT * FROM typed EXCEPT ALL SELECT * FROM facts)
            UNION ALL (SELECT * FROM facts EXCEPT ALL SELECT * FROM typed))''').fetchone()[0]
        reconciliations = []
        for item, series in zip(selected, SERIES):
            direct_mode = treasury_receipt is not None and series in TREASURY_SERIES
            if direct_mode:
                columns = [field.name for field in SCHEMA]
                expected = [tuple(row[column] for column in columns) for row in selected_rows[series]]
                saved_rows = con.execute('SELECT * FROM facts WHERE series=? ORDER BY observation_date', [series]).fetchall()
                differing = sum((Counter(expected) - Counter(saved_rows)).values()) + sum(
                    (Counter(saved_rows) - Counter(expected)).values())
                audit = treasury_receipt['fred_overlap_comparisons'].get(
                    {'DGS2': '2YR', 'DGS10': '10YR', 'DGS30': '30YR'}[series])
                if (not audit or audit.get('exact_value_mismatches') != 0
                        or audit.get('exact_match_rate_when_both_known') != 1.0):
                    raise ValueError('Treasury direct-source overlap audit is not exact')
                reconciliations.append({'series': series, 'differing_rows': differing,
                    'mode': 'receipt-bound Treasury from 1990 plus FRED pre-1990 extension; direct/FRED overlap exact'})
                continue
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
                SELECT series, observation_date, source_value_percent, value_percent, source_value,
                    documented_discontinuation_conflict FROM facts WHERE series=?) SELECT count(*) FROM (
                (SELECT * FROM expected EXCEPT ALL SELECT * FROM saved) UNION ALL
                (SELECT * FROM saved EXCEPT ALL SELECT * FROM expected))''', [series, series]).fetchone()[0]
            reconciliations.append({'series': series, 'differing_rows': differing, 'mode': 'independent FRED CSV-to-Parquet'})
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
        'dgs30_break': ('Treasury reports that the 30-year CMT was discontinued from 2002-02-18 to 2006-02-08; the downloaded direct series has 994 native dates in that interval and all are missing, not filled from 20-year rates. A separate common missing date is 2010-10-11 across the three tenors. In FRED-only legacy mode, published values in the 30-year interval are preserved but quarantined.'),
        'treasury_source_route': ('Direct Treasury daily par-yield curve is primary from 1990-01-02 when a receipt-bound run is selected. FRED DGS2/DGS10/DGS30 are then used only as the pre-1990 historical extension and as a whole-snapshot comparator. Direct Treasury/FRED exact overlap is checked independently in the acquisition receipt. Without a Treasury run, legacy FRED-only behavior is retained.'),
        'oas_coverage': 'FRED notes: only three years since April 2026; month-end weekend rows can occur.',
        'mortgage_break': 'PMMS methodology changed 2022-11-17; historical native dates retained.',
        'monthly': 'Summaries of available native observations, not complete calendar-month assertions.',
        'availability': 'Latest-revised retrieval; historical publication/availability times unknown.',
        'rights': 'ICE data/derived summaries internal use only; all outputs private, no external publication approval.',
        'source_links': [url for profile in profiles for url in
                         (profile['source_url'] if isinstance(profile['source_url'], list) else [profile['source_url']]) if url] + [
            'https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology']}
    write_new(output / 'contract.json', contract)
    # Recheck only this case's source bytes after derivation; full batch was verified at intake.
    for item in selected:
        if sha256(source / item['file']) != item['sha256']:
            raise ValueError('Market source changed during preparation')
    if treasury_run_id is not None:
        rechecked_folder, _, _ = _treasury_normalized_rows(root, treasury_run_id)
        if sha256(rechecked_folder / 'acquisition-audit.json') != treasury_receipt_digest:
            raise ValueError('Treasury source receipt changed during preparation')
    if source_digest != sha256(source / 'acquisition-complete.json') or frozen_methods != methods():
        raise ValueError('Market acquisition/implementation changed during preparation')
    receipt = {'case_id': identifier, 'status': 'MARKET_CONTEXT_COMPLETE', 'completed_at': timestamp(),
        'suite_id': suite_id, 'source_receipt_sha256': source_digest,
        'treasury_run_id': treasury_run_id, 'treasury_receipt_sha256': treasury_receipt_digest,
        'treasury_direct_source': ({'run_id': treasury_run_id, 'receipt_sha256': treasury_receipt_digest,
            'normalized_sha256': treasury_source_hash, 'native_rows': treasury_receipt['native_rows'],
            'first_date': treasury_receipt['first_date'], 'last_date': treasury_receipt['last_date'],
            'source_file_ids': [item['source_id'] for item in treasury_receipt['source_files']]}
            if treasury_receipt else None),
        'sources': selected, 'profiles': profiles, 'native_records': len(facts),
        'coverage': coverage, 'monthly_records': monthly.num_rows,
        'independent_reconciliations': reconciliations, 'roundtrip_differing_rows': roundtrip,
        'quarantined_records': sum(profile['quarantined'] for profile in profiles),
        'historical_treasury_semantics_qualified': (not any(profile['quarantined'] for profile in profiles)
            and treasury_receipt is None),
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
            or start['source_receipt_sha256'] != receipt['source_receipt_sha256']
            or start.get('treasury_run_id') != receipt.get('treasury_run_id')
            or start.get('treasury_receipt_sha256') != receipt.get('treasury_receipt_sha256')):
        raise ValueError('Market start/completion lineage changed')
    if sha256(source / 'acquisition-complete.json') != receipt['source_receipt_sha256']:
        raise ValueError('Market acquisition receipt changed')
    batch = read_json(source / 'acquisition-complete.json')
    direct_ref = receipt.get('treasury_direct_source')
    direct_treasury = None
    if direct_ref is None:
        if receipt.get('treasury_run_id') is not None or receipt.get('treasury_receipt_sha256') is not None:
            raise ValueError('Market Treasury source reference is incomplete')
    else:
        if direct_ref.get('run_id') != receipt.get('treasury_run_id'):
            raise ValueError('Market Treasury source run ID changed')
        direct_folder, direct_receipt, direct_rows = _treasury_normalized_rows(root, direct_ref['run_id'])
        direct_sha = sha256(direct_folder / 'acquisition-audit.json')
        if (direct_sha != receipt.get('treasury_receipt_sha256') or direct_sha != direct_ref.get('receipt_sha256')
                or direct_receipt['normalized_file']['sha256'] != direct_ref.get('normalized_sha256')
                or direct_receipt['native_rows'] != direct_ref.get('native_rows')
                or direct_receipt['first_date'] != direct_ref.get('first_date')
                or direct_receipt['last_date'] != direct_ref.get('last_date')
                or [item['source_id'] for item in direct_receipt['source_files']] != direct_ref.get('source_file_ids')):
            raise ValueError('Market Treasury source receipt changed')
        direct_treasury = (direct_receipt, direct_rows)
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
    if [item['series'] for item in receipt['profiles']] != list(SERIES):
        raise ValueError('Market profile/source counts changed')
    for profile, item in zip(receipt['profiles'], receipt['sources']):
        if (profile['known'] + profile['missing'] != profile['rows']
                or profile['source_known'] + profile['source_missing'] != profile['rows']
                or profile['known'] + profile['quarantined'] != profile['source_known']):
            raise ValueError('Market source coverage/profile counts changed')
        legs = profile.get('source_legs')
        if not isinstance(legs, list) or not legs or profile.get('source_sha256') != _legs_digest(legs):
            raise ValueError('Market source leg lineage digest changed')
        if direct_treasury is not None and profile['series'] in TREASURY_SERIES:
            expected_ids = [item['source_id'], 'treasury-daily-par-yield']
            expected_hashes = [item['sha256'], direct_ref['normalized_sha256']]
            if ([leg.get('source_id') for leg in legs] != expected_ids
                    or [leg.get('sha256') for leg in legs] != expected_hashes
                    or legs[0].get('role') != 'historical_extension_before_1990-01-02'
                    or legs[1].get('role') != 'direct_publisher_from_1990-01-02'):
                raise ValueError('Market hybrid Treasury/FRED source legs changed')
        else:
            if (len(legs) != 1 or legs[0].get('source_id') != item['source_id']
                    or legs[0].get('sha256') != item['sha256']
                    or legs[0].get('role') != 'native_source_snapshot'):
                raise ValueError('Market native source leg changed')
    if (receipt['quarantined_records'] != sum(profile['quarantined'] for profile in receipt['profiles'])
            or receipt['historical_treasury_semantics_qualified'] !=
                (receipt['quarantined_records'] == 0 and direct_treasury is None)):
        raise ValueError('Market semantic quarantine status changed')
    for item in receipt['files']:
        path = contained(folder, item['file'])
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Market output bytes changed')
    if pq.read_metadata(folder / 'native-observations.parquet').num_rows != receipt['native_records']:
        raise ValueError('Market native record count changed')
    source_rows = pq.read_table(folder / 'native-observations.parquet', columns=[
        'series', 'observation_date', 'source_id', 'source_sha256']).to_pylist()
    source_by_id = {item['source_id']: item for item in receipt['sources']}
    for row in source_rows:
        series, observed = row['series'], row['observation_date']
        if direct_treasury is not None and series in TREASURY_SERIES and observed >= TREASURY_START:
            expected_id, expected_sha = 'treasury-daily-par-yield', direct_ref['normalized_sha256']
        else:
            expected_id = 'fred-' + series.lower()
            expected_sha = source_by_id[expected_id]['sha256']
        if row['source_id'] != expected_id or row['source_sha256'] != expected_sha:
            raise ValueError('Market row-level source provenance changed')
    if (pq.read_metadata(folder / 'aligned-daily-context.parquet').num_rows != receipt['coverage']['aligned_dates']
            or pq.read_metadata(folder / 'monthly-context.parquet').num_rows != receipt['monthly_records']):
        raise ValueError('Market aligned/monthly counts changed')
    return folder, receipt
