"""Audited historical SBA aggregates; never join snapshots or expose borrower rows."""
import json
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path

from .workspace import contained, read_json, sha256

AUDIT = 'artifacts/private/sba-historical-audit-e953b55508eb/receipt.json'
AUDIT_SHA = 'd3bcdce3d0fc9110c8b0aa674d867933a9dd04a4be38ee34e0451b60a8def89e'
METHOD_SHA = sha256(Path(__file__))


def aggregate(profiles):
    """Retain native program monetary scopes and raw status spellings."""
    groups = {}
    for p in profiles:
        program = p['program']
        if program not in {'7A', '504'}:
            raise ValueError('Unknown SBA program')
        n = p['records']
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise ValueError('Invalid record count')
        if sum(x['records'] for x in p['source_status_counts']) != n:
            raise ValueError('Status population mismatch')
        if sum(x['records'] for x in p['source_program_counts']) != n:
            raise ValueError('Program population mismatch')
        if len(p['source_program_counts']) != 1 or p['source_program_counts'][0]['raw'].strip().casefold() != program.casefold():
            raise ValueError('Native program differs from file program')
        if p['actual_snapshot_dates'] != [{'raw': '3/31/2026', 'parsed': '2026-03-31', 'records': n}]:
            raise ValueError('Unqualified snapshot date')
        g = groups.setdefault(program, {'program': program, 'records': 0, 'files': [], 'statuses': Counter(), 'amounts': {}})
        g['records'] += n
        g['files'].append(p['file'])
        for s in p['source_status_counts']:
            g['statuses'][s['raw']] += s['records']
        for field, a in p['reported_amounts'].items():
            if field not in {'GrossApproval', 'GrossChargeOffAmount'}:
                raise ValueError('Unsupported amount')
            if a['unparsed_nonblank_records'] != 0 or a['known_records'] + a['blank_records'] != n:
                raise ValueError('Amount coverage mismatch')
            if (a['sum_exact'] is None) != (a['known_records'] == 0):
                raise ValueError('Amount missingness mismatch')
            total = g['amounts'].setdefault(field, {'known_records': 0, 'blank_records': 0, 'sum_exact': None})
            total['known_records'] += a['known_records']
            total['blank_records'] += a['blank_records']
            if a['sum_exact'] is not None:
                value = Decimal(a['sum_exact'])
                if not value.is_finite():
                    raise ValueError('Nonfinite source amount')
                with localcontext() as ctx:
                    ctx.prec = 60
                    total['sum_exact'] = str(Decimal(total['sum_exact'] or '0') + value)
    result = []
    for g in groups.values():
        g['source_status_counts'] = [{'raw': k, 'records': v} for k, v in sorted(g.pop('statuses').items(), key=lambda x: x[0] or '')]
        g['amount_scope'] = 'Full approved loan amount' if g['program'] == '7A' else 'SBA/CDC approved component;not full project financing'
        result.append(g)
    return sorted(result, key=lambda g: g['program'])


def report(root: Path):
    """Verify the accepted audit graph and all raw bytes before projection."""
    if sha256(Path(__file__)) != METHOD_SHA:
        raise ValueError('Archive serving method changed;restart required')
    audit_path = contained(root, AUDIT)
    if sha256(audit_path) != AUDIT_SHA:
        raise ValueError('Archive audit changed')
    audit = read_json(audit_path)
    profile_path = contained(root, audit['source_profile'])
    if audit['status'] != 'PASS' or sha256(profile_path) != audit['source_profile_sha256']:
        raise ValueError('Archive profile changed or unaudited')
    method = contained(root, 'scripts/audit_sba_historical_profile.py')
    if sha256(method) != audit['method_sha256']:
        raise ValueError('Archive audit method changed')
    profile = read_json(profile_path)
    folder = contained(root, profile['source_folder'])
    if not folder.is_relative_to((root / 'data/private/business-archive').resolve()):
        raise ValueError('Archive outside private source boundary')
    receipt_path = folder / 'receipt.json'
    if sha256(receipt_path) != audit['source_receipt_sha256'] or profile['source_receipt_sha256'] != audit['source_receipt_sha256']:
        raise ValueError('Archive acquisition changed')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
    profiles = profile['profiles']
    sources = {s['file']: s for s in receipt['files']}
    checked = {s['file']: s for s in audit['files']}
    if len(profiles) != 6 or len(sources) != 6 or len(checked) != 6 or {p['file'] for p in profiles} != set(sources) or set(sources) != set(checked):
        raise ValueError('Archive segment completeness mismatch')
    digests = {AUDIT: AUDIT_SHA, str(profile_path.relative_to(root)): audit['source_profile_sha256'], str(receipt_path.relative_to(root)): audit['source_receipt_sha256']}
    for p in profiles:
        source = sources[p['file']]
        raw = contained(folder, p['file'])
        if source['http_status'] != 200 or raw.stat().st_size != source['bytes'] or not (sha256(raw) == source['sha256'] == p['sha256'] == checked[p['file']]['sha256']):
            raise ValueError('Archive raw source changed')
        if p['records'] != checked[p['file']]['records']:
            raise ValueError('Archive audit population mismatch')
        digests[str(raw.relative_to(root))] = p['sha256']
    groups = aggregate(profiles)
    total = sum(g['records'] for g in groups)
    if total != profile['total_source_records'] or total != audit['source_records']:
        raise ValueError('Archive total mismatch')
    return {'schema_version': 'sba-historical-archive-v1', 'snapshot_date': audit['snapshot_date'],
            'records': total, 'record_grain': 'Published CSV source record;not unique loan or borrower',
            'programs': groups, 'segments': [{**p, 'source_url': sources[p['file']]['resolved_url']} for p in profiles],
            'evidence_hashes': digests, 'visibility': 'private', 'borrower_rows_included': False,
            'qualified': {'identity': False, 'transitions': False, 'fixed_horizon_PD': False,
                          'publication_time': False, 'EAD': False, 'subprogram_dictionary': False},
            'limitations': profile['limitations'] + ['March headers are lowercase with extra subprogram;June adapter/dictionary cannot silently qualify this version.',
                                                   'Program approval/chargeoff sums remain separate;no cross-program pooled severity.',
                                                   'Archive does not modify the frozen June business case.']}


def view_report(views, query):
    if set(query) != {'view_id'}:
        raise ValueError('SBA archive accepts view_id only')
    view = views.view(query['view_id'])
    if view.get('business', {}).get('business_id') != 'business-sba-21c568f10f7d':
        raise ValueError('SBA archive is not registered for this business source')
    result = report(views.root)
    result['view_id'] = query['view_id']
    result['anchor_business_id'] = view['business']['business_id']
    result['scope'] = 'Separate historical archive;current June cohort filters do not apply'
    return result
