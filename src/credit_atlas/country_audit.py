"""Independent raw JSON -> SQL reconciliation of the World Bank canonical case."""
import json
import uuid
from pathlib import Path

import duckdb
import pyarrow as pa

from .country_observatory import verify_case, verify_source
from .workspace import contained, read_json, sha256, timestamp, write_new

PROJECTION = """SELECT r.indicator_id,c.code country_code,c.iso2 country_iso2,c.name country_name,
 c.region_id='NA' is_aggregate,c.region region,c.income income_group_current,
 CAST(r.reference_year AS SMALLINT) AS year,r.value,r.unit source_unit,r.declared_unit,
 r.obs_status,CAST(r.precision AS SMALLINT) source_decimal,r.footnote,r.updated source_lastupdated,
 r.iso3 source_country_iso3,r.name source_country_name,
 CASE WHEN r.iso3='' THEN 'exact_catalog_iso2_missing_source_iso3' ELSE 'source_iso3' END country_join_basis
 FROM native r JOIN definitions c ON
 (r.iso3<>'' AND r.iso3=c.code) OR (r.iso3='' AND r.iso2=c.iso2)"""
DIFFERENCES = """SELECT count(*) FROM (
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM canonical)
 UNION ALL (SELECT * FROM canonical EXCEPT ALL SELECT * FROM expected))"""
QUALITY = """SELECT count(*) AS rows,count(*) FILTER(WHERE value IS NULL) AS missing,
 count(*) FILTER(WHERE NOT is_aggregate) economy_rows,
 count(*) FILTER(WHERE is_aggregate) aggregate_rows,
 count(*) FILTER(WHERE source_country_iso3='') blank_iso3_rows,
 count(*) FILTER(WHERE source_country_name<>country_name) native_name_difference_rows,
 count(*) FILTER(WHERE footnote<>'') footnoted_rows,
 count(*) FILTER(WHERE source_unit='') blank_source_unit_rows,
 count(DISTINCT country_code) returned_entities FROM canonical"""
YEAR_COVERAGE = """SELECT indicator_id,is_aggregate,year,count(*) AS rows,count(value) AS known,
 count(*)-count(value) missing FROM canonical GROUP BY ALL ORDER BY indicator_id,is_aggregate,year"""


def run_audit(root, case_id):
    folder, case = verify_case(root, case_id)
    source, acquired = verify_source(root, case['source_id'])
    definitions, native = [], []
    for item in acquired['files']:
        if item['group'] == 'countries':
            for row in read_json(source / item['file'])[1]:
                definitions.append({'code': row['id'], 'iso2': row['iso2Code'], 'name': row['name'],
                    'region_id': row['region']['id'], 'region': row['region']['value'], 'income': row['incomeLevel']['value']})
    contract = read_json(folder / 'contract.json')
    for item in acquired['files']:
        if item['group'].endswith('-data'):
            meta, rows = read_json(source / item['file'])
            for row in rows:
                native.append({'indicator_id': row['indicator']['id'], 'iso3': row['countryiso3code'],
                    'iso2': row['country']['id'], 'name': row['country']['value'], 'reference_year': row['date'],
                    'value': row['value'], 'unit': row['unit'], 'obs_status': row['obs_status'],
                    'precision': row['decimal'], 'footnote': row['footnote'], 'updated': meta['lastupdated'],
                    'declared_unit': contract['indicators'][row['indicator']['id']]['unit']})
    identifier = 'country-audit-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    with duckdb.connect() as db:
        db.register('native', pa.Table.from_pylist(native))
        db.register('definitions', pa.Table.from_pylist(definitions))
        db.execute('CREATE TABLE expected AS ' + PROJECTION)
        db.execute('CREATE TABLE canonical AS SELECT * FROM read_parquet(?)', [str(folder / 'observations.parquet')])
        differences = db.execute(DIFFERENCES).fetchone()[0]
        expected_rows = db.execute('SELECT count(*) FROM expected').fetchone()[0]
        key_duplicates = db.execute('SELECT count(*) FROM (SELECT indicator_id,country_code,year FROM canonical GROUP BY ALL HAVING count(*)>1)').fetchone()[0]
        orphan_or_name_disagreement = db.execute("""SELECT count(*) FROM native r LEFT JOIN definitions c ON
             (r.iso3<>'' AND r.iso3=c.code) OR (r.iso3='' AND r.iso2=c.iso2)
             WHERE c.code IS NULL OR r.iso2<>c.iso2 OR trim(r.name)<>trim(c.name)""").fetchone()[0]
        quality = dict(zip([item[0] for item in db.execute(QUALITY).description], db.execute(QUALITY).fetchone()))
        result = db.execute(YEAR_COVERAGE)
        coverage = [dict(zip([item[0] for item in result.description], row)) for row in result.fetchall()]
        vnm = db.execute("SELECT indicator_id,year,value FROM canonical WHERE country_code='VNM' AND year>=2020 ORDER BY indicator_id,year").fetchall()
    if differences or key_duplicates or orphan_or_name_disagreement or expected_rows != len(native):
        raise ValueError('Independent source reconciliation failed')
    write_new(output / 'annual-coverage.json', coverage)
    write_new(output / 'queries.json', {'projection': PROJECTION, 'bidirectional_except_all': DIFFERENCES,
                                      'quality': QUALITY, 'annual_coverage': YEAR_COVERAGE})
    receipt = {'audit_id': identifier, 'case_id': case_id, 'source_id': case['source_id'], 'status': 'PASS',
        'completed_at': timestamp(), 'raw_native_rows': len(native), 'independent_join_rows': expected_rows,
        'differing_rows': differences, 'duplicate_keys': key_duplicates,
        'orphan_or_name_disagreement': orphan_or_name_disagreement, 'quality': quality,
        'vietnam_2020_2025': [{'indicator_id': code, 'year': year, 'value': value} for code, year, value in vnm],
        'case_receipt_sha256': sha256(folder / 'case-complete.json'),
        'methods': {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('country_audit', 'country_observatory', 'workspace')},
        'visibility': 'private', 'public_release_approved': False}
    notebook = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
        'cells': [
            {'cell_type': 'markdown', 'metadata': {}, 'source': ['# Country source reconciliation\n',
              'Review/rerun companion; evidence is the saved audit receipt. This notebook has not been separately executed.\n',
              'Raw JSON, exact ISO2 missing-ISO3 join, preserved nulls/footnotes, duplicate and bidirectional SQL checks.']},
            {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
             'source': ['from credit_atlas.country_audit import run_audit, PROJECTION, DIFFERENCES, QUALITY, YEAR_COVERAGE\n',
                        'from credit_atlas.workspace import app_root\n', f"result = run_audit(app_root(), {case_id!r})\n", 'result']},
            {'cell_type': 'markdown', 'metadata': {}, 'source': ['## Exact executed SQL\n',
                '```sql\n' + PROJECTION + ';\n' + DIFFERENCES + ';\n' + QUALITY + ';\n' + YEAR_COVERAGE + ';\n```']} ]}
    write_new(output / 'source-quality.ipynb', notebook)
    receipt['files'] = {name: sha256(output / name) for name in ('annual-coverage.json', 'queries.json', 'source-quality.ipynb')}
    write_new(output / 'audit-complete.json', receipt)
    return receipt
