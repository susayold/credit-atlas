"""FDIC historical bank reports: immutable HTTP acquisition and descriptive panel.

No borrower outcomes, point-in-time availability or regulatory capital inferred.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pyarrow as pa
import pyarrow.parquet as pq

from .workspace import contained, read_json, sha256, timestamp, write_new

FIELDS = ('CERT', 'REPDTE', 'NAME', 'ASSET', 'DEP', 'EQ', 'ROA', 'CERTCONS')
DEFINITIONS = 'https://api.fdic.gov/banks/docs/risview_properties.yaml'
UNITS = 'https://api.fdic.gov/banks/docs/swagger.yaml'
SCHEMA = pa.schema([
    ('cert', pa.int64()), ('report_date', pa.date32()), ('name', pa.string()),
    ('assets_usd_thousands', pa.int64()), ('deposits_usd_thousands', pa.int64()),
    ('equity_usd_thousands', pa.int64()), ('roa_annualized_percent', pa.float64()),
    ('consolidating_parent_cert', pa.int64()), ('asset_peer', pa.string()),
    ('equity_assets_percent', pa.float64()), ('deposits_assets_percent', pa.float64()),
])


def quarter_dates(start_year=2016, end_year=2026, end_quarter=2):
    if not (1992 <= start_year <= end_year <= 2100 and 1 <= end_quarter <= 4):
        raise ValueError('Invalid quarterly coverage')
    return [f'{year}{month:02d}{day:02d}'
            for year in range(start_year, end_year + 1)
            for q, (month, day) in enumerate(((3, 31), (6, 30), (9, 30), (12, 31)), 1)
            if year < end_year or q <= end_quarter]


def _download(url, destination):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in
            {'api.fdic.gov', 'banks.data.fdic.gov'} or parsed.username or parsed.password
            or parsed.port is not None):
        raise ValueError('Official credential-free FDIC URL required')
    if destination.exists():
        raise ValueError('Immutable output already exists')
    partial = destination.with_suffix(destination.suffix + '.partial')
    response = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error',
        '--proto', '=https', '--connect-timeout', '20', '--max-time', '120',
        '--max-filesize', str(32 * 1024**2), '--output', str(partial),
        '--write-out', '%{http_code}', url], capture_output=True, timeout=125)
    if response.returncode or response.stdout != b'200':
        raise RuntimeError(f'FDIC HTTP failed: curl={response.returncode}, HTTP={response.stdout[:3]!r}')
    if not partial.is_file() or not 0 < partial.stat().st_size <= 32 * 1024**2:
        raise ValueError('Invalid FDIC response size')
    partial.rename(destination)
    return {'url': url, 'file': destination.name, 'sha256': sha256(destination),
            'bytes': destination.stat().st_size, 'retrieved_at': timestamp()}


def definition_blocks(text):
    """Extract exact reviewed YAML blocks, retaining raw YAML as authority."""
    result = {}
    for field in FIELDS:
        match = re.search(r'(?m)^      ' + field + r':\s*\n', text)
        if not match:
            raise ValueError('Missing official field definition: ' + field)
        next_field = re.search(r'(?m)^      [A-Z0-9_]+:\s*\n', text[match.end():])
        stop = match.end() + next_field.start() if next_field else len(text)
        result[field] = text[match.start():stop]
    if not ('NETINCA' in result['ROA'] and 'ASSET5' in result['ROA']
            and 'annualized' in result['ROA']):
        raise ValueError('ROA definition requires renewed review')
    if 'consolidated' not in result['CERTCONS']:
        raise ValueError('Consolidation definition requires renewed review')
    return result


def _integer(value, required=False):
    if value is None or value == '':
        if required:
            raise ValueError('Required integer missing')
        return None
    if isinstance(value, bool):
        raise ValueError('Boolean is not a financial integer')
    number = Decimal(str(value))
    if not number.is_finite() or number != number.to_integral_value() or abs(number) > 2**63 - 1:
        raise ValueError('Invalid exact int64 financial value')
    return int(number)


def asset_peer(assets):
    if assets is None or assets <= 0:
        return 'unknown_or_nonpositive'
    for threshold, label in [(100_000, 'under_100m'), (1_000_000, '100m_to_1bn'),
                             (10_000_000, '1bn_to_10bn'), (100_000_000, '10bn_to_100bn')]:
        if assets < threshold:
            return label
    return '100bn_plus'


def normalize(payload, expected_date):
    rows = payload.get('data')
    total = payload.get('meta', {}).get('total')
    if (not isinstance(rows, list) or not rows or isinstance(total, bool)
            or not isinstance(total, int) or len(rows) != total or total >= 10000):
        raise ValueError('Incomplete/empty FDIC response; pagination must be reviewed')
    observed = date(int(expected_date[:4]), int(expected_date[4:6]), int(expected_date[6:]))
    if expected_date[4:] not in ('0331', '0630', '0930', '1231'):
        raise ValueError('Quarter-end required')
    result, keys = [], set()
    for wrapper in rows:
        row = wrapper['data']
        if any(field not in row for field in FIELDS) or str(row['REPDTE']) != expected_date:
            raise ValueError('Financial field/date mismatch')
        cert = _integer(row['CERT'], required=True)
        if cert <= 0 or cert in keys:
            raise ValueError('Duplicate/invalid bank-quarter identifier')
        keys.add(cert)
        if not isinstance(row['NAME'], str) or not row['NAME'].strip():
            raise ValueError('Institution name missing')
        assets, deposits, equity = [_integer(row[field]) for field in ('ASSET', 'DEP', 'EQ')]
        roa = None if row['ROA'] is None or row['ROA'] == '' else float(row['ROA'])
        if isinstance(row['ROA'], bool) or (roa is not None and not math.isfinite(roa)):
            raise ValueError('Nonfinite/boolean ROA')
        parent = _integer(row['CERTCONS'])
        if parent is not None and parent < 0:
            raise ValueError('Invalid consolidating parent')
        ratio = lambda v: float(Decimal(v) / Decimal(assets) * 100) if v is not None and assets is not None and assets > 0 else None
        result.append(dict(zip(SCHEMA.names, (cert, observed, row['NAME'], assets, deposits,
            equity, roa, parent, asset_peer(assets), ratio(equity), ratio(deposits)))))
    return sorted(result, key=lambda row: row['cert'])


def acquire_bank_history(root: Path):
    root = root.resolve()
    if root.drive.upper() != 'D:':
        raise ValueError('D: workspace required')
    identifier = 'fdic-history-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'data/private/bank-history/' + identifier)
    folder.mkdir(parents=True)
    dates = quarter_dates()
    write_new(folder / 'acquisition-start.json', {'started_at': timestamp(), 'dates': dates,
              'fields': list(FIELDS), 'methods': {'bank_panel.py': sha256(Path(__file__))}})
    references, results = [], []
    try:
        for url, filename in [(DEFINITIONS, 'financial-definitions.yaml'), (UNITS, 'openapi.yaml')]:
            reference = _download(url, folder / filename)
            references.append(reference)
            write_new(folder / (filename + '-receipt.json'), reference)
        definition_blocks((folder / 'financial-definitions.yaml').read_text(encoding='utf-8'))
        units_text = (folder / 'openapi.yaml').read_text(encoding='utf-8')
        if '50000 thousands of dollars' not in units_text or 'DEP:[50000 TO *]' not in units_text:
            raise ValueError('Official deposit unit evidence requires renewed review')
        def fetch(report_date):
            query = urlencode({'filters': 'REPDTE:' + report_date, 'fields': ','.join(FIELDS),
                'limit': 10000, 'offset': 0, 'sort_by': 'CERT', 'sort_order': 'ASC', 'format': 'json'})
            try:
                receipt = _download('https://api.fdic.gov/banks/financials?' + query,
                                    folder / ('financials-' + report_date + '.json'))
                payload = json.loads((folder / receipt['file']).read_text(encoding='utf-8'), parse_float=Decimal)
                typed = normalize(payload, report_date)
                receipt.update(report_date=report_date, status='COMPLETE', rows=len(typed),
                               source_total=payload['meta']['total'])
            except Exception as error:
                receipt = {'report_date': report_date, 'status': 'FAILED',
                           'error_type': type(error).__name__, 'error': str(error)[:240]}
            write_new(folder / ('financials-' + report_date + '-receipt.json'), receipt)
            return receipt
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(fetch, dates))
        if any(item['status'] != 'COMPLETE' for item in results):
            raise ValueError('One or more FDIC quarters failed; retained receipts identify gaps')
        complete = {'acquisition_id': identifier, 'status': 'COMPLETE', 'completed_at': timestamp(),
            'dates': dates, 'fields': list(FIELDS), 'references': references, 'quarters': results,
            'rows': sum(item['rows'] for item in results),
            'bytes': sum(item['bytes'] for item in results + references),
            'availability': 'latest_revised_retrieval_not_historical_asof',
            'model_qualified': False, 'public_release_approved': False}
        write_new(folder / 'acquisition-complete.json', complete)
        return complete
    except Exception as error:
        write_new(folder / 'acquisition-failed.json', {'acquisition_id': identifier,
            'failed_at': timestamp(), 'error_type': type(error).__name__, 'error': str(error)[:240]})
        raise


def verify_acquisition(root, identifier):
    if not re.fullmatch(r'fdic-history-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid acquisition identifier')
    folder = contained(root, 'data/private/bank-history/' + identifier)
    receipt = read_json(folder / 'acquisition-complete.json')
    start = read_json(folder / 'acquisition-start.json')
    if (receipt['acquisition_id'] != identifier or receipt['status'] != 'COMPLETE'
            or receipt['dates'] != quarter_dates() or start['dates'] != receipt['dates']
            or receipt['fields'] != list(FIELDS) or start['fields'] != list(FIELDS)
            or len(receipt['quarters']) != len(receipt['dates'])
            or [item['report_date'] for item in receipt['quarters']] != receipt['dates']):
        raise ValueError('Acquisition coverage contract changed')
    if [(item['url'], item['file']) for item in receipt['references']] != [
            (DEFINITIONS, 'financial-definitions.yaml'), (UNITS, 'openapi.yaml')]:
        raise ValueError('Official references changed')
    if (receipt['rows'] != sum(item['rows'] for item in receipt['quarters'])
            or receipt['bytes'] != sum(item['bytes'] for item in receipt['references'] + receipt['quarters'])):
        raise ValueError('Acquisition totals changed')
    for item in receipt['quarters']:
        query = urlencode({'filters': 'REPDTE:' + item['report_date'], 'fields': ','.join(FIELDS),
            'limit': 10000, 'offset': 0, 'sort_by': 'CERT', 'sort_order': 'ASC', 'format': 'json'})
        if (item['status'] != 'COMPLETE' or item['rows'] != item['source_total']
                or not 0 < item['rows'] < 10000
                or item['file'] != 'financials-' + item['report_date'] + '.json'
                or item['url'] != 'https://api.fdic.gov/banks/financials?' + query):
            raise ValueError('Quarter source contract changed')
    for item in receipt['references'] + receipt['quarters']:
        path = contained(folder, item['file'])
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('FDIC source bytes changed')
        receipt_file = item['file'] + '-receipt.json' if 'report_date' not in item else 'financials-' + item['report_date'] + '-receipt.json'
        if read_json(folder / receipt_file) != item:
            raise ValueError('Per-source receipt changed')
    return folder, receipt


def prepare_bank_panel(root, acquisition_id):
    import duckdb
    source, acquisition = verify_acquisition(root, acquisition_id)
    identifier = 'bank-panel-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    definitions = definition_blocks((source / 'financial-definitions.yaml').read_text(encoding='utf-8'))
    write_new(output / 'field-contract.json', {'definitions': definitions,
        'monetary_units': 'USD thousands', 'roa_units': 'annualized percent of average total assets',
        'unit_evidence': {'downloaded_openapi': 'DEP example: 50000 thousands of dollars',
            'reviewed_official_display': 'https://banks.data.fdic.gov/bankfind-suite/financialreporting/report?reportPeriod=20260630&unitType=%24',
            'display_units': 'Values in Thousands USD',
            'review_scope': 'ASSET, DEP and EQ are money; ROA is percent, never scaled by 1000'},
        'equity_ratio': 'book equity/assets, not risk-weighted regulatory capital',
        'peer_bins': 'custom contemporaneous asset bands, not FDIC regulatory peer groups',
        'aggregation': 'reported bank records; consolidated subsidiaries may overlap parents',
        'availability': acquisition['availability'], 'model_qualified': False})
    rows = []
    for item in acquisition['quarters']:
        payload = json.loads((source / item['file']).read_text(encoding='utf-8'), parse_float=Decimal)
        typed = normalize(payload, item['report_date'])
        if len(typed) != item['rows']:
            raise ValueError('Receipt row count changed')
        rows.extend(typed)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    pq.write_table(table, output / 'bank-quarter.parquet', compression='zstd')
    con = duckdb.connect()
    con.register('source_rows', table)
    con.read_parquet(str(output / 'bank-quarter.parquet')).create_view('saved')
    differences = con.execute('SELECT count(*) FROM ((SELECT * FROM source_rows EXCEPT ALL SELECT * FROM saved) UNION ALL (SELECT * FROM saved EXCEPT ALL SELECT * FROM source_rows))').fetchone()[0]
    if differences:
        raise ValueError('Saved bank panel differs from typed source')
    con.execute('''CREATE VIEW peers AS SELECT report_date, asset_peer, count(*) AS records,
        count(assets_usd_thousands) AS assets_known,
        sum(assets_usd_thousands)::HUGEINT AS reported_assets_usd_thousands,
        count(deposits_usd_thousands) AS deposits_known,
        sum(deposits_usd_thousands)::HUGEINT AS reported_deposits_usd_thousands,
        count(equity_usd_thousands) AS equity_known,
        sum(equity_usd_thousands)::HUGEINT AS reported_equity_usd_thousands,
        count(roa_annualized_percent) AS roa_known,
        median(roa_annualized_percent) AS bank_median_roa_annualized_percent,
        median(equity_assets_percent) AS bank_median_book_equity_assets_percent,
        count(*) FILTER(WHERE consolidating_parent_cert > 0) AS consolidated_subsidiary_reports,
        count(*) FILTER(WHERE consolidating_parent_cert IS NULL) AS consolidation_unknown,
        count(*) FILTER(WHERE assets_usd_thousands <= 0) AS nonpositive_assets,
        count(*) FILTER(WHERE equity_usd_thousands < 0) AS negative_book_equity
        FROM saved GROUP BY report_date, asset_peer''')
    pq.write_table(con.execute('SELECT * FROM peers ORDER BY report_date, asset_peer').to_arrow_table(),
                   output / 'peer-quarter.parquet', compression='zstd')
    changes = con.execute('''WITH previous AS (SELECT *, lag(report_date) OVER w AS previous_date,
        lag(assets_usd_thousands) OVER w AS previous_assets FROM saved
        WINDOW w AS (PARTITION BY cert ORDER BY report_date))
        SELECT report_date, count(*) AS matched_reports,
        count(*) FILTER(WHERE assets_usd_thousands IS NOT NULL AND previous_assets IS NOT NULL) AS paired_assets_known,
        sum(assets_usd_thousands::HUGEINT - previous_assets::HUGEINT) FILTER
            (WHERE assets_usd_thousands IS NOT NULL AND previous_assets IS NOT NULL) AS paired_asset_change_usd_thousands
        FROM previous WHERE date_diff('month', previous_date, report_date)=3
        GROUP BY report_date ORDER BY report_date''').to_arrow_table()
    pq.write_table(changes, output / 'matched-quarter-changes.parquet', compression='zstd')
    summaries = con.execute('''SELECT report_date::VARCHAR AS report_date, count(*) AS records,
        count(*) FILTER(WHERE consolidating_parent_cert > 0) AS consolidated_subsidiary_reports,
        count(*) FILTER(WHERE consolidating_parent_cert IS NULL) AS consolidation_unknown,
        count(*) FILTER(WHERE assets_usd_thousands IS NULL) AS assets_missing,
        count(*) FILTER(WHERE deposits_usd_thousands IS NULL) AS deposits_missing,
        count(*) FILTER(WHERE equity_usd_thousands IS NULL) AS equity_missing,
        count(*) FILTER(WHERE assets_usd_thousands <= 0) AS nonpositive_assets,
        count(*) FILTER(WHERE equity_usd_thousands < 0) AS negative_book_equity,
        count(*) FILTER(WHERE roa_annualized_percent IS NULL) AS roa_missing,
        median(roa_annualized_percent) AS bank_median_roa_annualized_percent
        FROM saved GROUP BY report_date ORDER BY report_date''').to_arrow_table().to_pylist()
    if sum(row['records'] for row in summaries) != acquisition['rows']:
        raise ValueError('Panel totals mismatch')
    con.close()
    verify_acquisition(root, acquisition_id)
    complete = {'case_id': identifier, 'status': 'DESCRIPTIVE_PANEL_COMPLETE',
        'completed_at': timestamp(), 'acquisition_id': acquisition_id, 'records': len(rows),
        'unique_certificates': len({row['cert'] for row in rows}), 'quarters': summaries,
        'reconciliation_differing_rows': differences,
        'methods': {'bank_panel.py': sha256(Path(__file__))},
        'files': [{'file': p.name, 'sha256': sha256(p), 'bytes': p.stat().st_size}
                  for p in sorted(output.iterdir()) if p.is_file()],
        'limitations': ['Latest revised observations; historical release availability unknown.',
            'Subsidiaries and consolidated parent reports can overlap; sums are not industry totals.',
            'Stocks cannot be summed across quarters; matched changes do not adjust for mergers.',
            'Certificate continuity is not stable economic-entity continuity.',
            'No loan book, borrower PD, failure forecasting or regulatory capital adequacy model.'],
        'model_qualified': False, 'public_release_approved': False}
    write_new(output / 'panel-complete.json', complete)
    return complete


def verify_bank_panel(root, identifier):
    if not re.fullmatch(r'bank-panel-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bank panel identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    complete = read_json(folder / 'panel-complete.json')
    if complete['case_id'] != identifier or complete['status'] != 'DESCRIPTIVE_PANEL_COMPLETE':
        raise ValueError('Bank panel completion contract changed')
    if complete['methods'] != {'bank_panel.py': sha256(Path(__file__))}:
        raise ValueError('Bank panel implementation changed')
    _, acquisition = verify_acquisition(root, complete['acquisition_id'])
    expected_files = {'bank-quarter.parquet', 'peer-quarter.parquet',
                      'matched-quarter-changes.parquet', 'field-contract.json'}
    if (len(complete['files']) != len(expected_files)
            or {item['file'] for item in complete['files']} != expected_files
            or complete['records'] != acquisition['rows']
            or len(complete['quarters']) != len(acquisition['dates'])
            or sum(item['records'] for item in complete['quarters']) != complete['records']):
        raise ValueError('Bank panel coverage/output contract changed')
    for item in complete['files']:
        path = contained(folder, item['file'])
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Bank panel output changed')
    if pq.read_metadata(folder / 'bank-quarter.parquet').num_rows != complete['records']:
        raise ValueError('Bank panel row count changed')
    return complete
