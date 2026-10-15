"""Source UPB observations only; never turn mortgage balances into model EAD."""
import argparse
import csv
import hashlib
import json
import uuid

import duckdb

from credit_atlas.exposure_imports import FIELDS, import_exposures, verify_import
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, contained, sha256, write_new


def prepare(root, case_id, month):
    service = ResearchService(root); case = service.case(case_id); manifest = case['manifest']
    import re
    from datetime import date
    if not re.fullmatch(r'\d{4}-\d{2}', month): raise ValueError('Explicit ISO observation month required')
    period = date.fromisoformat(month + '-01')
    source = contained(root, manifest['canonical_run'])
    connection = duckdb.connect()
    try:
        connection.from_parquet(str(source / 'fact_loan_month.parquet')).create_view('months')
        connection.from_parquet(str(source / 'dim_loan.parquet')).create_view('loans')
        values = connection.execute('''SELECT m.loan_id,m.raw_current_upb,d.property_state,m.delinquency_state,
          CASE WHEN d.is_relief_refinance THEN 'relief' WHEN d.is_relief_refinance IS FALSE THEN 'non_relief' ELSE 'unknown' END
          FROM months m JOIN loans d USING(loan_id) WHERE m.period=? ORDER BY m.loan_id''', [period]).fetchall()
    finally: connection.close()
    if not values: raise ValueError('No observations in requested month; no carry-forward')
    package = root / 'data/private/portfolio' / ('mortgage-exposure-input-' + uuid.uuid4().hex[:12]); package.mkdir(parents=True)
    with (package / 'positions.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream); writer.writerow(FIELDS)
        for key, amount, region, state, segment in values:
            writer.writerow([hashlib.sha256((case_id + ':' + key).encode()).hexdigest()[:24],
                'sample-observation-cohort:' + case_id, 'DIRECT_ASSET', month, 'USD', 'major',
                amount, segment, region or 'SOURCE_REGION_UNAVAILABLE', state or 'SOURCE_STATE_UNAVAILABLE', '', '', ''])
    lineage = {item['path']: item['sha256'] for item in manifest['verified_inputs']}
    lineage['artifacts/private/' + case_id + '/case-complete.json'] = case['complete_hash']
    metadata = {'schema_version': 1, 'dataset_kind': 'source_observation', 'amount_kind': 'reported_outstanding_principal',
        'as_of': month, 'date_grain': 'month', 'source_namespace': 'Freddie-Mac-2012-annual-sample',
        'source_description': 'Loan-month observations in sample; reported raw UPB, not owned positions, EAD or default PD; sampling cohort pool key is not a securitization pool.',
        'risk_contract': None, 'source_lineage': [{'path': path, 'sha256': digest} for path, digest in sorted(lineage.items())],
        'visibility': 'private', 'public_release_approved': False}
    write_new(package / 'metadata.json', metadata)
    service.case(case_id)
    receipt = import_exposures(root, str((package / 'positions.csv').relative_to(root)), str((package / 'metadata.json').relative_to(root)))
    _, _, report = verify_import(root, receipt['import_id'])
    return receipt, report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--case', required=True); parser.add_argument('--month', required=True)
    receipt, report = prepare(app_root(), parser.parse_args().case, parser.parse_args().month)
    print(json.dumps({'import_id': receipt['import_id'], 'records': report['records'], 'currencies': report['currencies']}, indent=2))
