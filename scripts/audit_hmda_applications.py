"""Independent DuckDB CSV reader, exact-decimal marts and denominator audit."""
import json
import sys
import uuid
from decimal import Decimal, localcontext
from pathlib import Path

import duckdb
import pyarrow as pa

from credit_atlas.hmda_applications import verify_case
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new

DIMENSIONS = ('county_code', 'lei', 'loan_type', 'derived_race', 'derived_ethnicity', 'derived_sex',
              'debt_to_income_ratio', 'derived_dwelling_category')


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def run(root, identifier):
    folder, case = verify_case(root, identifier)
    source = root / 'data/private/hmda' / case['source_id']
    receipt = read_json(source / 'source-complete.json'); evidence = read_json(folder / 'evidence.json')
    output = root / 'artifacts/private' / ('hmda-audit-' + uuid.uuid4().hex[:12]); output.mkdir(parents=True)
    connection = duckdb.connect()
    connection.execute("SET threads=1"); connection.execute("SET memory_limit='768MB'")
    connection.execute('SET temp_directory=?', [str(output / 'sql-temp')])
    checks = []; queries = []
    try:
        header = receipt['profiles'][0]['header']; columns = ','.join(quoted(name) for name in header)
        for index, profiled in enumerate(receipt['profiles']):
            name = f"{profiled['year']}-MD-home-purchase-site-built.csv"
            query = ('SELECT ?::VARCHAR AS source_file, row_number() OVER ()::BIGINT AS source_row, * '
                     'FROM read_csv(?, header=true, all_varchar=true, force_not_null=?, strict_mode=true)')
            connection.execute(('CREATE TABLE native AS ' if index == 0 else 'INSERT INTO native ') + query,
                               [name, str(source / name), header])
        connection.from_parquet(str(folder / 'source_rows.parquet')).create_view('canonical_raw')
        connection.from_parquet(str(folder / 'applications.parquet')).create_view('canonical')
        raw_difference = connection.execute('''SELECT count(*) FROM (
            (SELECT * FROM native EXCEPT ALL SELECT * FROM canonical_raw)
            UNION ALL (SELECT * FROM canonical_raw EXCEPT ALL SELECT * FROM native))''').fetchone()[0]
        checks.append({'check': 'all_99_fields_and_source_ordinals_bidirectional', 'differences': raw_difference, 'pass': raw_difference == 0})
        # Fully qualify columns in joins rather than trusting derived pass flags.
        conditions = {
            'source_count_and_unique_keys': 'SELECT count(*) FROM (SELECT source_file,source_row,count(*) n FROM canonical GROUP BY 1,2 HAVING n<>1)',
            'action_codes': 'n.action_taken IS DISTINCT FROM c.action_code',
            'decision_denominator_eligibility': "(n.action_taken IN ('1','2','3')) IS DISTINCT FROM c.decision_denominator_eligible",
            'year_and_reporting_entity': 'CAST(n.activity_year AS INTEGER) IS DISTINCT FROM c.activity_year OR n.lei IS DISTINCT FROM c.lei',
            'public_amount_exact_usd': 'CAST(n.loan_amount AS DECIMAL(38,2)) IS DISTINCT FROM CAST(c.public_loan_amount_usd_exact AS DECIMAL(38,2))',
            'public_dti_not_imputed': 'n.debt_to_income_ratio IS DISTINCT FROM c.dti_public_category',
            'public_age_not_imputed': 'n.applicant_age IS DISTINCT FROM c.applicant_age_public_category',
            'unqualified_ltv_raw_retained': 'n.loan_to_value_ratio IS DISTINCT FROM c.ltv_source_raw_unqualified',
        }
        for field, typed in [('income','income_thousands_usd'), ('property_value','property_value_usd'), ('interest_rate','interest_rate_percent')]:
            status = {'income': 'income_status', 'property_value': 'property_value_status', 'interest_rate': 'interest_rate_status'}[field]
            conditions[field + '_value_status_units'] = f'''c.{status} IS DISTINCT FROM CASE WHEN n.{field}='' THEN 'SOURCE_BLANK'
                WHEN n.{field}='NA' THEN 'NOT_APPLICABLE' WHEN n.{field}='Exempt' THEN 'EXEMPT' ELSE 'VALUE' END
                OR TRY_CAST(n.{field} AS DECIMAL(38,18)) IS DISTINCT FROM TRY_CAST(c.{typed}_exact AS DECIMAL(38,18))'''
        for name, condition in conditions.items():
            query = condition if condition.startswith('SELECT ') else 'SELECT count(*) FROM native n JOIN canonical c USING(source_file,source_row) WHERE ' + condition
            differences = connection.execute(query).fetchone()[0]; queries.append({'check': name, 'sql': query})
            checks.append({'check': name, 'differences': differences, 'pass': differences == 0})
        typed_count = connection.execute('SELECT count(*) FROM canonical').fetchone()[0]
        checks.append({'check': 'canonical_row_count', 'actual': typed_count, 'expected': case['records'], 'pass': typed_count == case['records']})
        for year in evidence['years']:
            rows = connection.execute('SELECT action_taken,count(*),sum(CAST(loan_amount AS DECIMAL(38,2))) FROM native WHERE activity_year=? GROUP BY 1', [str(year['year'])]).fetchall()
            actual_counts = {code: count for code, count, _ in rows}
            actual_amounts = {code: amount for code, _, amount in rows}
            count_match = actual_counts == {code: count for code, count in year['actions'].items() if count}
            amount_match = actual_amounts == {code: Decimal(value) for code, value in year['public_amounts_by_action_usd'].items()}
            denominator = sum(actual_counts.get(code, 0) for code in ('1','2','3')); numerator = actual_counts.get('3', 0)
            with localcontext() as context:
                context.prec = 50
                delta = abs(Decimal(year['descriptive_denial_rate']) - Decimal(numerator) / denominator) if denominator else None
            checks.extend([{'check': 'annual_actions_' + str(year['year']), 'pass': count_match},
                {'check': 'annual_public_amounts_' + str(year['year']), 'pass': amount_match},
                {'check': 'decision_rate_' + str(year['year']), 'denominator': denominator, 'numerator': numerator,
                 'rounding_delta': str(delta) if delta is not None else None,
                 'pass': denominator == year['decision_denominator'] and numerator == year['denied_numerator']
                    and (delta <= Decimal('1e-27') if delta is not None else year['descriptive_denial_rate'] is None)}])
        union = ' UNION ALL '.join('SELECT CAST(activity_year AS INTEGER) AS "year",\'' + dimension + '\' dimension,'
            + quoted(dimension) + ' bucket,action_taken action_code,count(*) records,sum(CAST(loan_amount AS DECIMAL(38,2))) amount FROM native GROUP BY 1,3,4'
            for dimension in DIMENSIONS)
        connection.execute('CREATE TABLE expected_marts AS ' + union)
        saved = [{'year': row['year'], 'dimension': row['dimension'], 'bucket': row['bucket'], 'action_code': row['action_code'],
                  'records': row['records'], 'amount': row['public_loan_amount_sum_usd']} for row in evidence['marts']]
        connection.register('saved_marts', pa.Table.from_pylist(saved))
        connection.execute('CREATE VIEW actual_marts AS SELECT "year",dimension,bucket,action_code,records,CAST(amount AS DECIMAL(38,2)) amount FROM saved_marts')
        differences = connection.execute('SELECT count(*) FROM ((SELECT * FROM expected_marts EXCEPT ALL SELECT * FROM actual_marts) UNION ALL (SELECT * FROM actual_marts EXCEPT ALL SELECT * FROM expected_marts))').fetchone()[0]
        checks.append({'check': 'all_eight_dimension_marts_bidirectional', 'differences': differences, 'pass': differences == 0})
        groups, beyond = connection.execute('SELECT count(*),coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM native GROUP BY ' + columns + ') WHERE n>1').fetchone()
        checks.append({'check': 'public_duplicates_retained', 'groups': groups, 'rows_beyond_first': int(beyond),
            'pass': groups == evidence['quality']['exact_public_duplicate_groups']
                and beyond == evidence['quality']['exact_public_duplicate_rows_beyond_first']})
        result = {'audit_id': output.name, 'case_id': identifier, 'source_id': case['source_id'],
            'status': 'PASS' if all(row['pass'] for row in checks) else 'FAIL', 'completed_at': timestamp(),
            'raw_records': connection.execute('SELECT count(*) FROM native').fetchone()[0], 'raw_fields': len(header),
            'checks': checks, 'failed_checks': sum(not row['pass'] for row in checks), 'queries': queries,
            'case_receipt_sha256': sha256(folder / 'case-complete.json'), 'audit_script_sha256': sha256(Path(__file__)),
            'visibility': 'private', 'public_release_approved': False,
            'qualification': 'Accounting/transformation and descriptive-denominator audit, not PD/compliance/causal certification'}
        write_new(output / 'audit.json', result)
        return {'audit_id': result['audit_id'], 'status': result['status'], 'records': result['raw_records'],
                'checks': len(checks), 'failed_checks': result['failed_checks']}
    finally:
        connection.close()


if __name__ == '__main__':
    print(json.dumps(run(app_root(), sys.argv[1]), indent=2))
