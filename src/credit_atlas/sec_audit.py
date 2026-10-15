"""Independent raw SEC JSON reconciliation and exact-ratio arithmetic audit."""
import json
import uuid
from decimal import Decimal, localcontext
from pathlib import Path

import duckdb
import pyarrow as pa

from .sec_financials import FACT_SCHEMA, FILING_SCHEMA, verify_case
from .sec_sources import verify_source
from .workspace import contained, read_json, sha256, timestamp, write_new

DIFFERENCES = """SELECT count(*) FROM ((SELECT * FROM expected EXCEPT ALL SELECT * FROM canonical)
 UNION ALL (SELECT * FROM canonical EXCEPT ALL SELECT * FROM expected))"""


def run_audit(root, case_id):
    folder, case = verify_case(root, case_id)
    source, receipt = verify_source(root, case['source_id'])
    native_facts, native_filings = [], []
    for item in receipt['files']:
        payload = json.loads((source / item['file']).read_text(encoding='utf-8'), parse_float=Decimal)
        cik = item['cik']
        if item['kind'] == 'companyfacts':
            for taxonomy, concepts in payload['facts'].items():
                for concept, definition in concepts.items():
                    for unit, observations in definition['units'].items():
                        for index, row in enumerate(observations):
                            native_facts.append({'cik': cik, 'taxonomy': taxonomy, 'concept': concept, 'unit': unit,
                                'source_ordinal': index, 'start_date': row.get('start'), 'end_date': row['end'],
                                'value_exact': format(Decimal(row['val']), 'f'), 'accession': row['accn'],
                                'fiscal_year': row.get('fy'), 'fiscal_period': row.get('fp'), 'form': row['form'],
                                'filed_date': row['filed'], 'frame': row.get('frame'),
                                'extra_json': json.dumps({key: value for key, value in row.items() if key not in
                                  {'start', 'end', 'val', 'accn', 'fy', 'fp', 'form', 'filed', 'frame'}}, sort_keys=True, default=str)})
        else:
            columns = payload['filings']['recent'] if item['kind'] == 'submissions' else payload
            for index in range(len(columns['accessionNumber'])):
                def at(key):
                    return columns[key][index] if key in columns else None
                native_filings.append({'cik': cik, 'accession': at('accessionNumber'), 'filing_date': at('filingDate'),
                    'report_date': at('reportDate') or None, 'acceptance_datetime': at('acceptanceDateTime'),
                    'form': at('form'), 'primary_document': at('primaryDocument'),
                    'is_xbrl': None if at('isXBRL') is None else bool(at('isXBRL')), 'occurrences': 1})
    differences = {}
    with duckdb.connect() as db:
        for label, rows, schema, parquet in (
            ('facts', native_facts, FACT_SCHEMA, 'facts.parquet'),
            ('filings', native_filings, FILING_SCHEMA, 'filings.parquet')):
            db.register('native', pa.Table.from_pylist(rows, schema=schema))
            db.execute('DROP TABLE IF EXISTS expected'); db.execute('DROP TABLE IF EXISTS canonical')
            projection = 'SELECT * FROM native' if label == 'facts' else 'SELECT * EXCLUDE(occurrences),CAST(count(*) AS INTEGER) AS occurrences FROM native GROUP BY ALL'
            db.execute('CREATE TABLE expected AS ' + projection)
            db.execute('CREATE TABLE canonical AS SELECT * FROM read_parquet(?)', [str(folder / parquet)])
            differences[label] = db.execute(DIFFERENCES).fetchone()[0]
    if any(differences.values()):
        raise ValueError('Independent SEC source reconciliation failed')
    statements = read_json(folder / 'annual-statements.json')
    checks, statuses = 0, {}
    for statement in statements:
        for name, ratio in statement['ratios'].items():
            statuses[ratio['status']] = statuses.get(ratio['status'], 0) + 1
            numerator = statement['fields'][ratio['numerator']]
            denominator = statement['fields'][ratio['denominator']]
            if ratio['status'] == 'supported':
                if numerator['status'] != 'supported' or denominator['status'] != 'supported' or Decimal(denominator['value_exact']) <= 0:
                    raise ValueError('Unsupported arithmetic inputs')
                if numerator['kind'] == 'annual_duration' and numerator['start_date'] != denominator['start_date']:
                    raise ValueError('Mismatched annual arithmetic periods')
                with localcontext() as context:
                    context.prec = 60
                    expected = Decimal(numerator['value_exact']) / Decimal(denominator['value_exact'])
                    if Decimal(ratio['value_exact']) != expected:
                        raise ValueError('Independent exact ratio mismatch')
                checks += 1
            elif ratio['value_exact'] is not None:
                raise ValueError('Unsupported ratio has a value')
    identifier = 'sec-audit-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier); output.mkdir(parents=True)
    result = {'audit_id': identifier, 'case_id': case_id, 'source_id': case['source_id'], 'status': 'PASS',
        'completed_at': timestamp(), 'raw_fact_entries': len(native_facts), 'raw_filing_occurrences': len(native_filings),
        'differing_rows': differences, 'annual_snapshots': len(statements), 'exact_supported_ratio_checks': checks,
        'ratio_status_counts': statuses, 'case_receipt_sha256': sha256(folder / 'case-complete.json'),
        'methods': {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('sec_audit', 'sec_financials', 'sec_sources', 'workspace')},
        'visibility': 'private', 'public_release_approved': False}
    notebook = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {}, 'cells': [
        {'cell_type': 'markdown', 'metadata': {}, 'source': ['# SEC raw source / exact ratio audit\n',
          'Review/rerun companion; saved audit is executed evidence. This notebook has not separately run.\n',
          'Independent per-source record extraction and bidirectional SQL; 60-digit Decimal ratio arithmetic.\n', '```sql\n'+DIFFERENCES+';\n```']},
        {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': [
            'from credit_atlas.sec_audit import run_audit\n', 'from credit_atlas.workspace import app_root\n',
            f'result = run_audit(app_root(), {case_id!r})\n', 'result']} ]}
    write_new(output / 'source-quality.ipynb', notebook)
    result['notebook_sha256'] = sha256(output / 'source-quality.ipynb')
    write_new(output / 'audit-complete.json', result)
    return result
