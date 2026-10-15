from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from credit_atlas.business_archive import aggregate
from credit_atlas import business_archive as archive
from credit_atlas.workspace import sha256


def segment(program='7A', amount='9007199254740993.123456789123456789'):
    return {'program': program, 'file': 'example.csv', 'records': 3,
            'source_status_counts': [{'raw': 'P I F', 'records': 1}, {'raw': 'EXEMPT', 'records': 2}],
            'source_program_counts': [{'raw': ' 7A' if program == '7A' else '504', 'records': 3}],
            'actual_snapshot_dates': [{'raw': '3/31/2026', 'parsed': '2026-03-31', 'records': 3}],
            'reported_amounts': {'GrossApproval': {'known_records': 2, 'blank_records': 1,
                               'unparsed_nonblank_records': 0, 'sum_exact': amount}}}


def test_decimal_scope_and_native_status_preservation():
    a = segment()
    b = segment(amount='0.000000000000000001')
    c = segment('504', '10')
    groups = aggregate([a, b, c])
    assert [g['program'] for g in groups] == ['504', '7A']
    assert groups[1]['amounts']['GrossApproval']['sum_exact'] == '9007199254740993.123456789123456790'
    assert groups[1]['amounts']['GrossApproval']['blank_records'] == 2
    assert groups[1]['source_status_counts'] == [{'raw': 'EXEMPT', 'records': 4}, {'raw': 'P I F', 'records': 2}]
    assert groups[0]['amounts']['GrossApproval']['sum_exact'] == '10'


def test_all_missing_amount_stays_missing():
    p = segment()
    p['reported_amounts']['GrossApproval'].update(known_records=0, blank_records=3, sum_exact=None)
    assert aggregate([p])[0]['amounts']['GrossApproval']['sum_exact'] is None


@pytest.mark.parametrize('change', ['date', 'status', 'program', 'coverage', 'invalid', 'nan', 'missing', 'count'])
def test_unqualified_source_rejected(change):
    p = deepcopy(segment())
    if change == 'date': p['actual_snapshot_dates'][0]['parsed'] = '2026-06-30'
    if change == 'status': p['source_status_counts'][0]['records'] = 0
    if change == 'program': p['source_program_counts'][0]['raw'] = '504'
    if change == 'coverage': p['reported_amounts']['GrossApproval']['blank_records'] = 0
    if change == 'invalid': p['reported_amounts']['GrossApproval']['unparsed_nonblank_records'] = 1
    if change == 'nan': p['reported_amounts']['GrossApproval']['sum_exact'] = 'NaN'
    if change == 'missing': p['reported_amounts']['GrossApproval']['sum_exact'] = None
    if change == 'count': p['records'] = True
    with pytest.raises(ValueError): aggregate([p])


@pytest.fixture
def graph(tmp_path, monkeypatch):
    folder = tmp_path / 'data/private/business-archive/example'
    folder.mkdir(parents=True)
    profiles = []
    sources = []
    audited = []
    for i in range(6):
        p = segment('504' if i < 2 else '7A', '10')
        p['file'] = f'part-{i}.csv'
        raw = folder / p['file']
        raw.write_text('synthetic fixture bytes')
        p['sha256'] = sha256(raw)
        p['columns'] = 40 if i < 2 else 43
        p['headers'] = ['asofdate', 'subprogram']
        p['headers_match_existing_dictionary'] = False
        profiles.append(p)
        sources.append({'file': p['file'], 'http_status': 200, 'bytes': raw.stat().st_size,
                        'sha256': p['sha256'], 'resolved_url': 'https://data.sba.gov/example.csv'})
        audited.append({'file': p['file'], 'sha256': p['sha256'], 'records': p['records']})
    acquisition = folder / 'receipt.json'
    acquisition.write_text(json.dumps({'files': sources}))
    profile_path = tmp_path / 'profile.json'
    profile_path.write_text(json.dumps({'profiles': profiles, 'source_folder': str(folder.relative_to(tmp_path)),
        'source_receipt_sha256': sha256(acquisition), 'total_source_records': 18, 'limitations': []}))
    method = tmp_path / 'scripts/audit_sba_historical_profile.py'
    method.parent.mkdir();method.write_text('synthetic fixture audit method')
    audit = tmp_path / archive.AUDIT
    audit.parent.mkdir(parents=True)
    audit.write_text(json.dumps({'status': 'PASS', 'source_profile': 'profile.json',
        'source_profile_sha256': sha256(profile_path), 'method_sha256': sha256(method),
        'source_receipt_sha256': sha256(acquisition), 'files': audited,
        'source_records': 18, 'snapshot_date': '2026-03-31'}))
    monkeypatch.setattr(archive, 'AUDIT_SHA', sha256(audit))
    return tmp_path


def test_verified_graph_projection(graph):
    r = archive.report(graph)
    assert r['records'] == 18 and r['borrower_rows_included'] is False
    assert not any(r['qualified'].values())
    assert len(r['segments']) == 6 and len(r['evidence_hashes']) == 9


@pytest.mark.parametrize('target', ['raw', 'profile', 'acquisition', 'audit', 'method'])
def test_modified_evidence_fails_closed(graph, target):
    paths = {'raw': 'data/private/business-archive/example/part-0.csv', 'profile': 'profile.json',
             'acquisition': 'data/private/business-archive/example/receipt.json',
             'audit': archive.AUDIT, 'method': 'scripts/audit_sba_historical_profile.py'}
    f = graph / paths[target]
    f.write_bytes(f.read_bytes() + b' ')
    with pytest.raises(ValueError): archive.report(graph)


@pytest.mark.parametrize('query', [{}, {'view_id': 'x', 'program': '7A'}, {'view_id': 'x', 'source_file': '../raw'}])
def test_query_scope_rejected_before_archive_read(graph, query):
    views = SimpleNamespace(root=graph, view=lambda _: pytest.fail('Unexpected view read'))
    with pytest.raises(ValueError): archive.view_report(views, query)


def test_unregistered_business_rejected(graph):
    views = SimpleNamespace(root=graph, view=lambda _: {'business': {'business_id': 'another-source'}})
    with pytest.raises(ValueError, match='not registered'): archive.view_report(views, {'view_id': 'x'})
