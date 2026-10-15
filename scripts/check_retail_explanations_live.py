import json
import uuid
from urllib.parse import urlencode
from urllib.request import urlopen
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new


def run(root):
    output = root / 'artifacts/private' / ('retail-explanations-live-' + uuid.uuid4().hex[:12]); output.mkdir()
    study = 'retail-explanations-84b3ac3bab6e'; base = 'http://127.0.0.1:8770'
    source = read_json(root / 'artifacts/private' / study / 'report.json')
    ledger = root / 'artifacts/private/retail-holdout-access.sqlite'; before = sha256(ledger)
    with urlopen(base + '/api/retail-explanations?' + urlencode({'freeze_id': source['freeze_id']}), timeout=300) as response:
        assert any(row['explanations_id'] == study for row in json.load(response)['studies'])
    query = {'freeze_id': source['freeze_id'], 'explanations_id': study, 'case': 'validation_case_12'}
    expected = source | {'local_explanations': [row for row in source['local_explanations'] if row['case'] == query['case']],
                         'explanations_id': study, 'filters': {'case': query['case']},
                         'visibility': 'private', 'public_release_approved': False}
    for endpoint in ('retail-explanation', 'retail-explanation-report'):
        with urlopen(base + '/api/' + endpoint + '?' + urlencode(query), timeout=300) as response:
            assert 'no-store' in response.headers['Cache-Control'] and json.load(response) == expected
    assert sha256(ledger) == before
    write_new(output / 'receipt.json', {'status':'PASS','completed_at':timestamp(),'explanations_id':study,
                                       'api_file_parity':True,'selected_case':'validation_case_12',
                                       'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False})
    return {'status':'PASS','directory':str(output)}


if __name__ == '__main__': print(json.dumps(run(app_root()), indent=2))
