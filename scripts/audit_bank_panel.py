"""Independent DuckDB JSON-to-Parquet reconciliation without adapter transforms."""
import argparse
import json
import uuid
from pathlib import Path

import duckdb

from credit_atlas.bank_panel import verify_acquisition, verify_bank_panel
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def audit(root, panel_id):
    case = verify_bank_panel(root, panel_id)
    source, acquisition = verify_acquisition(root, case['acquisition_id'])
    folder = root / 'artifacts/private' / panel_id
    con = duckdb.connect()
    con.read_parquet(str(folder / 'bank-quarter.parquet')).create_view('saved')
    differences = []
    for receipt in acquisition['quarters']:
        con.read_json(str(source / receipt['file']), sample_size=-1,
                      maximum_object_size=64 * 1024**2).create_view('raw', replace=True)
        day = receipt['report_date']
        # Explicit projection independent of Python normalization / Arrow schema.
        count = con.execute('''WITH native AS (SELECT
            r.data.CERT::BIGINT AS cert,
            strptime(r.data.REPDTE::VARCHAR, '%Y%m%d')::DATE AS report_date,
            r.data.NAME::VARCHAR AS name,
            r.data.ASSET::BIGINT AS assets_usd_thousands,
            r.data.DEP::BIGINT AS deposits_usd_thousands,
            r.data.EQ::BIGINT AS equity_usd_thousands,
            r.data.ROA::DOUBLE AS roa_annualized_percent,
            NULLIF(r.data.CERTCONS::VARCHAR, '')::BIGINT AS consolidating_parent_cert
            FROM raw, UNNEST(data) AS records(r)), persisted AS (
            SELECT cert, report_date, name, assets_usd_thousands, deposits_usd_thousands,
            equity_usd_thousands, roa_annualized_percent, consolidating_parent_cert
            FROM saved WHERE report_date=strptime(?, '%Y%m%d')::DATE)
            SELECT count(*) FROM ((SELECT * FROM native EXCEPT ALL SELECT * FROM persisted)
              UNION ALL (SELECT * FROM persisted EXCEPT ALL SELECT * FROM native))''', [day]).fetchone()[0]
        differences.append({'report_date': day, 'source_rows': receipt['rows'],
                            'differing_rows': count})
    quality = con.execute('''SELECT count(*) AS records,
        count(DISTINCT (cert, report_date)) AS unique_bank_quarters,
        count(DISTINCT cert) AS unique_certificates,
        count(*) FILTER(WHERE equity_usd_thousands<0) AS negative_equity_records,
        count(*) FILTER(WHERE consolidating_parent_cert>0) AS consolidated_subsidiary_records,
        count(*) FILTER(WHERE assets_usd_thousands IS NULL OR deposits_usd_thousands IS NULL
            OR equity_usd_thousands IS NULL OR roa_annualized_percent IS NULL) AS missing_financial_records
        FROM saved''').to_arrow_table().to_pylist()[0]
    peers = con.read_parquet(str(folder / 'peer-quarter.parquet'))
    peer_rows = peers.aggregate('sum(records)').fetchone()[0]
    changes = con.read_parquet(str(folder / 'matched-quarter-changes.parquet'))
    matched_rows = changes.aggregate('sum(matched_reports)').fetchone()[0]
    con.close()
    verify_bank_panel(root, panel_id)
    total_differences = sum(item['differing_rows'] for item in differences)
    passed = (total_differences == 0 and quality['records'] == case['records']
              and quality['records'] == quality['unique_bank_quarters'] == peer_rows)
    result = dict(panel_id=panel_id, audit_id='bank-panel-audit-' + uuid.uuid4().hex[:12],
        status='PASS' if passed else 'FAIL', audited_at=timestamp(),
        audit_script_sha256=sha256(Path(__file__)), differing_rows=total_differences,
        quarter_reconciliations=differences, quality=quality,
        peer_record_denominator=peer_rows, adjacent_quarter_matched_records=matched_rows,
        source_publication_time='unknown; retrieved latest revised reports',
        qualification='Descriptive records only; equity<0 is not a bank failure label')
    write_new(folder / (result['audit_id'] + '.json'), result)
    if not passed:
        raise ValueError('Independent raw reconciliation failed')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--panel', required=True)
    result = audit(app_root(), parser.parse_args().panel)
    print(json.dumps({key: result[key] for key in ('audit_id', 'status', 'differing_rows', 'quality',
                    'peer_record_denominator', 'adjacent_quarter_matched_records')}, indent=2))
