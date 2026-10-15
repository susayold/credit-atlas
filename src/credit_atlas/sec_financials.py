"""SEC source-native facts and filing-specific research statement snapshots.

No universal concept equivalence, debt terms, default labels or PIT qualification.
"""
import json
import re
import uuid
from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .sec_sources import filing_columns, verify_source
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'sec-case-[0-9a-f]{12}\Z')
ACCESSION = re.compile(r'\d{10}-\d{2}-\d{6}\Z')
FACT_SCHEMA = pa.schema([
    ('cik', pa.string()), ('taxonomy', pa.string()), ('concept', pa.string()), ('unit', pa.string()),
    ('source_ordinal', pa.int32()), ('start_date', pa.string()), ('end_date', pa.string()),
    ('value_exact', pa.string()), ('accession', pa.string()), ('fiscal_year', pa.int32()),
    ('fiscal_period', pa.string()), ('form', pa.string()), ('filed_date', pa.string()),
    ('frame', pa.string()), ('extra_json', pa.string()),
])
FILING_SCHEMA = pa.schema([
    ('cik', pa.string()), ('accession', pa.string()), ('filing_date', pa.string()), ('report_date', pa.string()),
    ('acceptance_datetime', pa.string()), ('form', pa.string()), ('primary_document', pa.string()),
    ('is_xbrl', pa.bool_()), ('occurrences', pa.int32()),
])
FIELDS = {
    'assets': ('instant', ('Assets',)),
    'liabilities': ('instant', ('Liabilities',)),
    'current_assets': ('instant', ('AssetsCurrent',)),
    'current_liabilities': ('instant', ('LiabilitiesCurrent',)),
    'cash_equivalents': ('instant', ('CashAndCashEquivalentsAtCarryingValue',)),
    'revenue': ('annual_duration', ('RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'Revenues')),
    'net_income': ('annual_duration', ('NetIncomeLoss',)),
    'operating_cashflow': ('annual_duration', ('NetCashProvidedByUsedInOperatingActivities',)),
}


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('sec_financials', 'sec_sources', 'workspace')}


def _date(value, optional=False):
    if optional and (value is None or value == ''):
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('SEC ISO reference date required')
    date.fromisoformat(value)
    return value


def _text(value, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise ValueError('SEC string annotation required')
    return value


def fact_rows(payload, cik):
    if str(payload['cik']).zfill(10) != cik:
        raise ValueError('SEC facts issuer mismatch')
    rows, definitions = [], {}
    known_keys = {'start', 'end', 'val', 'accn', 'fy', 'fp', 'form', 'filed', 'frame'}
    for taxonomy, concepts in payload['facts'].items():
        for concept, definition in concepts.items():
            definitions[taxonomy + ':' + concept] = {'label': definition.get('label'), 'description': definition.get('description'),
                                                    'units': list(definition['units'])}
            for unit, observations in definition['units'].items():
                if not isinstance(unit, str) or not unit or not isinstance(observations, list):
                    raise ValueError('Invalid SEC concept/unit observations')
                for ordinal, item in enumerate(observations):
                    value = item['val']
                    if type(value) not in (int, Decimal) or not Decimal(value).is_finite():
                        raise ValueError('SEC finite exact numeric fact required')
                    accession = item['accn']
                    if not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
                        raise ValueError('SEC fact accession invalid')
                    fy = item.get('fy')
                    if fy is not None and (type(fy) is not int or not 1900 <= fy <= 2200):
                        raise ValueError('SEC fiscal year invalid')
                    start, end = _date(item.get('start'), True), _date(item['end'])
                    if start is not None and start > end:
                        raise ValueError('SEC fact inverted period')
                    rows.append({'cik': cik, 'taxonomy': taxonomy, 'concept': concept, 'unit': unit,
                        'source_ordinal': ordinal, 'start_date': start, 'end_date': end,
                        'value_exact': format(Decimal(value), 'f'), 'accession': accession, 'fiscal_year': fy,
                        'fiscal_period': _text(item.get('fp'), True), 'form': _text(item['form']),
                        'filed_date': _date(item['filed']), 'frame': _text(item.get('frame'), True),
                        'extra_json': json.dumps({key: val for key, val in item.items() if key not in known_keys},
                                                 sort_keys=True, default=str)})
    return rows, definitions


def normalize_filings(folder, receipt, cik):
    by_accession, occurrences = {}, []
    for source in receipt['files']:
        if source['cik'] != cik or source['kind'] not in {'submissions', 'history'}:
            continue
        content = read_json(folder / source['file'])
        columns = content['filings']['recent'] if source['kind'] == 'submissions' else content
        count = filing_columns(columns)
        for ordinal in range(count):
            accession = columns['accessionNumber'][ordinal]
            if not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
                raise ValueError('Invalid SEC filing accession')
            def value(name):
                return columns[name][ordinal] if name in columns else None
            xbrl = value('isXBRL')
            if xbrl is not None and (type(xbrl) is not int or xbrl not in (0, 1)):
                raise ValueError('SEC XBRL indicator invalid')
            row = {'cik': cik, 'accession': accession, 'filing_date': _date(value('filingDate')),
                'report_date': _date(value('reportDate'), True), 'acceptance_datetime': _text(value('acceptanceDateTime'), True),
                'form': _text(value('form')), 'primary_document': _text(value('primaryDocument')),
                'is_xbrl': None if xbrl is None else bool(xbrl)}
            existing = by_accession.get(accession)
            if existing is not None and existing != row:
                raise ValueError('Conflicting SEC filing occurrences')
            by_accession[accession] = row
            occurrences.append({'cik': cik, 'accession': accession, 'source_file': source['file'], 'source_ordinal': ordinal})
    counts = Counter(row['accession'] for row in occurrences)
    return [{**row, 'occurrences': counts[key]} for key, row in by_accession.items()], occurrences


def derive_source(folder, receipt):
    facts, filings, occurrences, definitions, quality = [], [], [], {}, []
    for entity in receipt['entities']:
        cik = entity['cik']
        source = [item for item in receipt['files'] if item['cik'] == cik and item['kind'] == 'companyfacts']
        if len(source) != 1:
            raise ValueError('SEC facts source missing/ambiguous')
        payload = json.loads((folder / source[0]['file']).read_text(encoding='utf-8'), parse_float=Decimal)
        issuer_facts, concepts = fact_rows(payload, cik)
        issuer_filings, issuer_occurrences = normalize_filings(folder, receipt, cik)
        definitions[cik] = concepts
        facts.extend(issuer_facts); filings.extend(issuer_filings); occurrences.extend(issuer_occurrences)
        matched = {row['accession']: row for row in issuer_filings}
        quality.append({'cik': cik, 'ticker': entity['ticker'], 'fact_entries': len(issuer_facts),
            'concepts': len(concepts), 'units': sorted({row['unit'] for row in issuer_facts}),
            'taxonomies': sorted({row['taxonomy'] for row in issuer_facts}),
            'unique_filings': len(issuer_filings), 'filing_occurrences': len(issuer_occurrences),
            'facts_without_filing_manifest': sum(row['accession'] not in matched for row in issuer_facts),
            'facts_filed_before_period_end': sum(row['filed_date'] < row['end_date'] for row in issuer_facts),
            'facts_manifest_date_or_form_mismatch': sum(row['accession'] in matched and
                (row['filed_date'] != matched[row['accession']]['filing_date'] or row['form'] != matched[row['accession']]['form']) for row in issuer_facts)})
    return facts, filings, occurrences, definitions, quality


def statement(filing, facts):
    end = filing['report_date']
    selected = [row for row in facts if row['cik'] == filing['cik'] and row['accession'] == filing['accession']]
    values = {}
    for field, (kind, concepts) in FIELDS.items():
        candidates = []
        for row in selected:
            if row['taxonomy'] != 'us-gaap' or row['concept'] not in concepts or row['unit'] != 'USD' or row['end_date'] != end:
                continue
            if row['filed_date'] != filing['filing_date'] or row['form'] != filing['form']:
                continue
            if kind == 'instant' and row['start_date'] is not None:
                continue
            if kind == 'annual_duration' and (row['start_date'] is None or
                    not 330 <= (date.fromisoformat(row['end_date']) - date.fromisoformat(row['start_date'])).days + 1 <= 400):
                continue
            candidates.append(row)
        signatures = {(row['start_date'], row['end_date'], Decimal(row['value_exact'])) for row in candidates}
        status = 'missing' if not candidates else 'ambiguous' if len(signatures) != 1 else 'supported'
        values[field] = {'status': status, 'unit': 'USD', 'kind': kind,
            'value_exact': candidates[0]['value_exact'] if status == 'supported' else None,
            'start_date': candidates[0]['start_date'] if status == 'supported' else None,
            'end_date': end, 'evidence': [{key: row[key] for key in
                ('taxonomy', 'concept', 'unit', 'source_ordinal', 'start_date', 'end_date', 'value_exact', 'filed_date', 'frame')} for row in candidates]}
    ratios = {}
    for name, numerator, denominator, align in (
        ('current_ratio', 'current_assets', 'current_liabilities', False),
        ('liabilities_assets', 'liabilities', 'assets', False),
        ('net_income_margin', 'net_income', 'revenue', True),
        ('operating_cashflow_revenue', 'operating_cashflow', 'revenue', True)):
        n, d = values[numerator], values[denominator]
        status = 'supported'
        if n['status'] != 'supported' or d['status'] != 'supported':
            status = 'missing_or_ambiguous_input'
        elif align and n['start_date'] != d['start_date']:
            status = 'period_mismatch'
        elif Decimal(d['value_exact']) <= 0:
            status = 'nonpositive_denominator'
        with localcontext() as context:
            context.prec = 60
            ratio = format(Decimal(n['value_exact']) / Decimal(d['value_exact']), 'f') if status == 'supported' else None
        ratios[name] = {'status': status, 'value_exact': ratio, 'unit': 'ratio (not percent)',
                        'numerator': numerator, 'denominator': denominator}
    return {'cik': filing['cik'], 'accession': filing['accession'], 'filing_date': filing['filing_date'],
        'report_date': end, 'form': filing['form'], 'primary_document': filing['primary_document'],
        'fields': values, 'ratios': ratios,
        'filing_url': f"https://www.sec.gov/Archives/edgar/data/{int(filing['cik'])}/{filing['accession']}-index.html",
        'limitations': ['Whole-filing entity non-custom taxonomy API facts only; custom/dimensional disclosures missing.',
            '330–400-day duration screen identifies annual candidates, not universal accounting equivalence.',
            'Equal repeated candidates retained as evidence; conflicting values/periods stay ambiguous.',
            'Missing tags are not zero. USD only for this statement view; no FX or unit conversion.',
            'Filing-specific snapshot from current SEC API is not a certified point-in-time backtest.',
            'Ratios do not provide sovereign/borrower PD, covenant terms, maturity schedule or recovered losses.']}


def prepare_sec_case(root, identifier):
    source, acquired = verify_source(root, identifier)
    frozen = methods()
    facts, filings, occurrences, definitions, quality = derive_source(source, acquired)
    case_id = 'sec-case-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'artifacts/private/' + case_id); folder.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(facts, schema=FACT_SCHEMA), folder / 'facts.parquet')
    pq.write_table(pa.Table.from_pylist(filings, schema=FILING_SCHEMA), folder / 'filings.parquet')
    write_new(folder / 'filing-occurrences.json', occurrences)
    write_new(folder / 'concepts.json', definitions)
    write_new(folder / 'quality.json', quality)
    grouped = {}
    for row in facts:
        grouped.setdefault((row['cik'], row['accession']), []).append(row)
    snapshots = [statement(row, grouped.get((row['cik'], row['accession']), [])) for row in filings
                 if row['form'] in {'10-K', '10-K/A'} and row['report_date'] is not None and
                 (row['cik'], row['accession']) in grouped]
    write_new(folder / 'annual-statements.json', snapshots)
    verify_source(root, identifier)
    if methods() != frozen:
        raise ValueError('SEC adapter methods changed')
    completed = {'case_id': case_id, 'source_id': identifier, 'status': 'SEC_FINANCIALS_DESCRIPTIVE_READY',
        'completed_at': timestamp(), 'methods': frozen, 'source_receipt_sha256': sha256(source / 'acquisition-complete.json'),
        'entities': acquired['entities'], 'fact_entries': len(facts), 'unique_filings': len(filings),
        'filing_occurrences': len(occurrences), 'annual_statements': len(snapshots),
        'visibility': 'private', 'public_release_approved': False, 'model_qualified': False,
        'files': {name: sha256(folder / name) for name in ('facts.parquet', 'filings.parquet', 'filing-occurrences.json',
                                                       'concepts.json', 'quality.json', 'annual-statements.json')}}
    write_new(folder / 'case-complete.json', completed)
    return completed


def verify_case(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
        raise ValueError('Invalid SEC case identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'case-complete.json')
    if (receipt['case_id'] != identifier or receipt['methods'] != methods() or receipt['status'] != 'SEC_FINANCIALS_DESCRIPTIVE_READY'
            or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False
            or receipt['model_qualified'] is not False):
        raise ValueError('SEC canonical methods/receipt changed')
    source, acquired = verify_source(root, receipt['source_id'])
    if sha256(source / 'acquisition-complete.json') != receipt['source_receipt_sha256']:
        raise ValueError('SEC source receipt changed')
    for name, digest in receipt['files'].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError('SEC canonical bytes changed')
    facts, filings, occurrences, concepts, quality = derive_source(source, acquired)
    fact_table, filing_table = pq.read_table(folder / 'facts.parquet'), pq.read_table(folder / 'filings.parquet')
    if fact_table.schema != FACT_SCHEMA or filing_table.schema != FILING_SCHEMA:
        raise ValueError('SEC canonical schema changed')
    if (fact_table.to_pylist() != facts or filing_table.to_pylist() != filings
            or read_json(folder / 'filing-occurrences.json') != occurrences or read_json(folder / 'concepts.json') != concepts
            or read_json(folder / 'quality.json') != quality or receipt['fact_entries'] != len(facts) or receipt['unique_filings'] != len(filings)
            or receipt['filing_occurrences'] != len(occurrences)):
        raise ValueError('SEC canonical projection differs from source')
    grouped = {}
    for row in facts:
        grouped.setdefault((row['cik'], row['accession']), []).append(row)
    expected = [statement(row, grouped.get((row['cik'], row['accession']), [])) for row in filings
                if row['form'] in {'10-K', '10-K/A'} and row['report_date'] is not None and (row['cik'], row['accession']) in grouped]
    if read_json(folder / 'annual-statements.json') != expected or receipt['annual_statements'] != len(expected):
        raise ValueError('SEC statement calculations differ from source')
    return folder, receipt
