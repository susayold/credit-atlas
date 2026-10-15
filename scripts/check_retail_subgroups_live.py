"""Check live private API parity against the immutable subgroup study."""
import json
import uuid
from urllib.parse import urlencode
from urllib.request import urlopen
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new


def run(root):
    output = root / 'artifacts/private' / ('retail-subgroups-live-' + uuid.uuid4().hex[:12])
    output.mkdir()
    base = 'http://127.0.0.1:8770'
    study = 'retail-subgroups-3cf671cf3152'
    source = read_json(root / 'artifacts/private' / study / 'report.json')
    plan = source['assumptions']
    ledger = root / 'artifacts/private/retail-holdout-access.sqlite'
    before = sha256(ledger)
    query = {key: plan[key] for key in ('policy_id', 'freeze_id')}
    with urlopen(base + '/api/retail-subgroups?' + urlencode(query), timeout=300) as response:
        catalog = json.load(response)
        assert any(row['subgroups_id'] == study for row in catalog['studies'])
    query.update(subgroups_id=study, dimension='education')
    expected = source | {
        'groups': [row for row in source['groups'] if row['dimension'] == 'education'],
        'subgroups_id': study, 'filters': {'dimension': 'education'},
        'visibility': 'private', 'public_release_approved': False,
    }
    for endpoint in ('retail-subgroup', 'retail-subgroup-report'):
        with urlopen(base + '/api/' + endpoint + '?' + urlencode(query), timeout=300) as response:
            assert 'no-store' in response.headers['Cache-Control']
            assert json.load(response) == expected
    assert sha256(ledger) == before
    receipt = {'status': 'PASS', 'completed_at': timestamp(), 'subgroups_id': study,
               'catalog_binding': True, 'api_file_parity': True,
               'education_groups': len(expected['groups']), 'private_no_store': True,
               'holdout_ledger_unchanged': True, 'visibility': 'private',
               'public_release_approved': False}
    write_new(output / 'receipt.json', receipt)
    return {'status': 'PASS', 'directory': str(output)}


if __name__ == '__main__':
    print(json.dumps(run(app_root()), indent=2))
