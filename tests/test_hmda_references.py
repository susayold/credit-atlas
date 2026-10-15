import csv
import json
import copy
import importlib.util
from pathlib import Path

import pytest

from credit_atlas import hmda_references as refs
from credit_atlas.workspace import read_json, sha256, write_new


def filer_rows(year):
    return [{'period': year, 'lei': 'A' * 20, 'name': f'Lender {year}', 'count': 8},
            {'period': year, 'lei': 'B' * 20, 'name': 'First name', 'count': 2},
            {'period': year, 'lei': 'B' * 20, 'name': 'Other name', 'count': 2}]


def county_text(year):
    delimiter = '|' if year == 2025 else '\t'
    header = ['USPS', 'GEOID', 'ANSICODE', 'NAME']
    rows = [['MD', '24005', '01695314', 'Baltimore County'], ['MD', '24510', '01702381', 'Baltimore city']]
    if year == 2025:
        header.append('GEOIDFQ')
        for row in rows: row.append('0500000US' + row[1])
    return '\n'.join(delimiter.join(row) for row in [header, *rows]) + '\n'


@pytest.fixture
def acquired(tmp_path, monkeypatch, request):
    source = tmp_path / 'data/private/hmda/fixture'; source.mkdir(parents=True)
    files = []
    for year in refs.YEARS:
        path = source / f'{year}-MD-home-purchase-site-built.csv'
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream); writer.writerow(['activity_year', 'lei', 'county_code'])
            writer.writerows([[year, 'A' * 20, '24005'], [year, 'B' * 20, '24510'], [year, 'C' * 20, 'NA']])
        files.append({'file': path.name, 'sha256': sha256(path)})
    write_new(source / 'source-complete.json', {'source_id': 'fixture', 'files': files})
    monkeypatch.setattr(refs, 'verify_source', lambda root, identifier: (source, {'files': files}))
    def download(url, destination):
        name = destination.name
        if name == 'api.html': body = '<html>Official API</html>'
        elif name.endswith('.html'): body = '<html>' + refs.urls()[name[:4] + '-counties.txt'] + '</html>'
        elif name.endswith('.txt'): body = county_text(int(name[:4]))
        else: body = json.dumps({'institutions': filer_rows(int(name[:4]))})
        destination.write_text(body, encoding='utf-8')
        return {'file': name, 'url': url, 'http_status': 200, 'bytes': destination.stat().st_size,
                'sha256': sha256(destination), 'retrieved_at': 'fixture'}
    monkeypatch.setattr(refs, 'download', download)
    receipt, payload = refs.acquire_references(tmp_path, 'fixture', getattr(request, 'param', 'lender_and_county'))
    folder = tmp_path / 'data/private/hmda' / receipt['reference_id']
    return tmp_path, folder, receipt, payload


def test_exact_year_join_retains_ambiguity_missing_and_distinct_geographies(acquired):
    root, folder, receipt, payload = acquired
    assert len(receipt['files']) == 10
    _, _, verified = refs.verify_references(root, receipt['reference_id'])
    assert verified == payload
    for year in refs.YEARS:
        row = payload['references'][str(year)]
        assert row['lender']['A' * 20]['names'] == [f'Lender {year}']
        assert row['lender']['B' * 20] == {'names': ['First name', 'Other name'], 'status': 'AMBIGUOUS'}
        assert row['county']['24005']['names'] == ['Baltimore County']
        assert row['county']['24510']['names'] == ['Baltimore city']
        coverage = next(item for item in payload['coverage'] if item['year'] == year)
        assert coverage['lender']['row_status_counts'] == {'AMBIGUOUS': 1, 'MATCHED': 1, 'UNMATCHED': 1}
        assert coverage['county']['unresolved_source_keys'] == {'NA': 1}


@pytest.mark.parametrize('change', ['year', 'bool_period', 'bad_lei', 'empty_name', 'bool_count'])
def test_filer_rejects_wrong_year_and_malformed_identity(tmp_path, change):
    rows = filer_rows(2024)
    field, value = {'year': ('period', 2025), 'bool_period': ('period', True),
        'bad_lei': ('lei', 'short'), 'empty_name': ('name', ' '), 'bool_count': ('count', True)}[change]
    rows[0][field] = value
    path = tmp_path / 'filers.json'; write_new(path, {'institutions': rows})
    with pytest.raises(ValueError): refs.filers(path, 2024)


@pytest.mark.parametrize('change', ['duplicate', 'wrong_state', 'wrong_delimiter', 'wrong_qualified_key'])
def test_county_rejects_conflicting_keys_scope_and_schema(tmp_path, change):
    text = county_text(2025)
    if change == 'duplicate': text += text.splitlines()[1] + '\n'
    elif change == 'wrong_state': text = text.replace('MD|', 'ME|')
    elif change == 'wrong_delimiter': text = text.replace('|', '\t')
    else: text = text.replace('0500000US24005', '0500000US24003')
    path = tmp_path / 'county.txt'; path.write_text(text, encoding='utf-8')
    with pytest.raises(ValueError): refs.counties(path, 2025)


@pytest.mark.parametrize('change', ['payload', 'forged_labels', 'false_to_zero', 'duplicate_file', 'url'])
def test_reference_reverification_rejects_corruption_and_self_attested_rewrite(acquired, change):
    root, folder, receipt, payload = acquired
    if change == 'payload':
        with (folder / '2024-filers.json').open('a') as stream: stream.write(' ')
    elif change == 'duplicate_file': receipt['files'][1] = receipt['files'][0]
    elif change == 'url': receipt['files'][0]['url'] = 'https://example.com/'
    else:
        if change == 'forged_labels': payload['references']['2024']['lender']['A' * 20]['names'] = ['Invented']
        else: payload['contract']['name_is_identity'] = 0
        (folder / 'labels.json').write_text(json.dumps(payload), encoding='utf-8')
        receipt['labels_sha256'] = sha256(folder / 'labels.json')
    (folder / 'reference-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError): refs.verify_references(root, receipt['reference_id'])


def test_downloader_does_not_follow_arbitrary_urls(tmp_path):
    with pytest.raises(ValueError): refs.download('https://example.com/', tmp_path / 'x')


@pytest.mark.parametrize('acquired', ['lender_only'], indirect=True)
def test_lender_only_does_not_claim_county_acquisition(acquired):
    root, folder, receipt, payload = acquired
    assert len(receipt['files']) == 4
    assert receipt['status'] == 'VERIFIED_DATED_HMDA_LENDER_REFERENCES'
    _, _, verified = refs.verify_references(root, receipt['reference_id'])
    assert verified['county_names_acquired'] is False
    assert all(row['county']['row_status_counts'] == {'UNMATCHED': 3} for row in verified['coverage'])
    assert all(row['county'] == {} for row in verified['references'].values())


def test_reference_does_not_accept_rebinding_to_modified_source_receipt(acquired, monkeypatch):
    root, folder, receipt, payload = acquired
    original = refs.verify_source(root, receipt['source_id'])
    (original[0] / 'source-complete.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='Bound HMDA source'): refs.verify_references(root, receipt['reference_id'])


def audit_module():
    path = Path(__file__).resolve().parents[1] / 'scripts/audit_hmda_references.py'
    spec = importlib.util.spec_from_file_location('reference_auditor', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('acquired', ['lender_only'], indirect=True)
def test_independent_raw_sql_reference_audit(acquired):
    root, folder, receipt, payload = acquired
    result = audit_module().audit(root, receipt['reference_id'])
    assert result['status'] == 'PASS'
    assert len(result['checks']) == 15


@pytest.mark.parametrize('acquired', ['lender_only'], indirect=True)
@pytest.mark.parametrize('change', ['labels', 'coverage'])
def test_independent_auditor_detects_bad_projection_even_if_primary_verifier_accepts(acquired, monkeypatch, change):
    root, folder, receipt, payload = acquired
    module = audit_module(); wrong = copy.deepcopy(payload)
    if change == 'labels': wrong['references']['2024']['lender']['A' * 20]['names'] = ['Invented']
    else: wrong['coverage'][1]['lender']['row_status_counts']['MATCHED'] = 0
    monkeypatch.setattr(module, 'verify_references', lambda *args: (folder, receipt, wrong))
    with pytest.raises(ValueError, match='Independent reference'): module.audit(root, receipt['reference_id'])
