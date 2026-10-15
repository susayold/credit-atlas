"""Issuer annual debt reconciliation, tied to the exact selected filing."""
from pathlib import Path
from .workspace import read_json, sha256, contained
from .sec_debt import report as maturity_report

AUDIT = 'artifacts/private/apple-annual-debt-bridge-1c634704d304/receipt.json'
AUDIT_SHA256 = '503ae5d831146f6adee5b50cd2e2f5dabbdde2221c9939efe7de6a22e1e27367'

def verified(root):
    if sha256(root / AUDIT) != AUDIT_SHA256:
        raise ValueError('Annual debt audit capture changed')
    audit = read_json(root / AUDIT)
    if audit.get('status') != 'PASS' or audit['method_sha256'] != sha256(root / 'scripts/audit_apple_annual_debt_bridge.py'):
        raise ValueError('Annual debt audit or method changed')
    for relative, expected in audit['inputs_sha256'].items():
        if sha256(contained(root, relative)) != expected:
            raise ValueError('Annual debt source evidence changed')
    folder = contained(root, audit['source'])
    acquisition = read_json(folder / 'acquisition.json')
    tables = read_json(folder / 'debt-tables.json')['tables']
    return audit, acquisition, tables

def report(views, identifier, query):
    selected = maturity_report(views, identifier, query)
    audit, acquisition, tables = verified(views.root)
    filters = selected['filters']
    filing = selected['statement']
    supported = (filters['cik'] == audit['cik'] and filters['debt_scope'] == 'debt_only'
                 and filing is not None and filing['accession'] == audit['accession']
                 and filing['report_date'] == audit['report_end']
                 and filing['filing_date'] == acquisition['filing_date'])
    result = {
        'view_id': identifier, 'filters': filters, 'entity': selected['entity'],
        'status': 'VERIFIED_ANNUAL_DEBT_BRIDGE' if supported else 'NO_MATCHING_ANNUAL_DEBT_EVIDENCE',
        'selected_statement': filing, 'source': None, 'bridges': [], 'maturities': [],
        'first_year_principal_minus_current_carrying_usd_exact': None,
        'tables': [], 'qualification': dict(audit['qualification']),
        'limitations': [
            'Source covers Apple 2025 annual filing only; no fallback across issuers, filings or debt/lease families.',
            'Carrying debt includes discount/cost and hedge adjustments; principal maturity buckets are a different basis.',
            'Fiscal maturity buckets are not exact calendar payment dates.',
            'Original aggregate issuance reconciliation does not prove per-series current outstanding or actual payments.',
            'No EAD, DSCR, covenant compliance or full issuer debt-service qualification is supplied.'],
        'audit_sha256': sha256(views.root / AUDIT), 'method_source_sha256': sha256(Path(__file__)),
        'visibility': 'private', 'public_release_approved': False,
    }
    if not supported:
        return result
    labels = ['2026', '2027', '2028', '2029', '2030', 'Thereafter']
    for label, bucket in zip(labels, selected['buckets']):
        exact = str(audit['maturity_usd_millions'][label] * 1000000)
        if bucket['field']['status'] != 'supported' or bucket['field']['value_exact'] != exact:
            raise ValueError('Annual debt bucket no longer reconciles with selected evidence')
        result['maturities'].append({'fiscal_label': label, 'bucket': bucket['bucket'], 'principal_usd_exact': exact})
    for bridge in audit['bridges']:
        result['bridges'].append({'year': bridge['year'], **{
            key + '_usd_exact': str(bridge[key] * 1000000)
            for key in ['principal', 'discount_and_costs', 'hedge_fair_value_adjustment', 'carrying', 'current_carrying', 'noncurrent_carrying']}})
    result['source'] = {'url': acquisition['url'], 'cik': audit['cik'], 'accession': audit['accession'],
                        'report_end': audit['report_end'], 'filing_date': acquisition['filing_date'],
                        'filing_id': audit['filing_id'], 'html_sha256': acquisition['sha256']}
    result['tables'] = tables
    result['first_year_principal_minus_current_carrying_usd_exact'] = str(audit['first_year_principal_minus_current_carrying_usd_millions'] * 1000000)
    return result
