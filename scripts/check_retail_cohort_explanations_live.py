import json
import uuid
from urllib.parse import urlencode
from urllib.request import urlopen
import pyarrow.parquet as pq
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new


def run(root):
    output=root/'artifacts/private'/('retail-cohort-live-'+uuid.uuid4().hex[:12]);output.mkdir()
    cohort='retail-cohort-explanations-02487bb9d1a2';folder=root/'artifacts/private'/cohort
    source=read_json(folder/'report.json');rows=pq.read_table(folder/'private-client-explanations.parquet').to_pylist()
    base='http://127.0.0.1:8770';ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    scope={'cohort_id':cohort,'freeze_id':source['freeze_id'],'explanations_id':source['explanations_id']}
    with urlopen(base+'/api/retail-cohort-explanations?'+urlencode({k:v for k,v in scope.items() if k!='cohort_id'}),timeout=600) as response:
        assert any(r['cohort_id']==cohort for r in json.load(response)['studies'])
    by_rank={r['score_rank']:r for r in rows};seen=set()
    # Complete pagination reconciles every public token/rank/probability, with no raw IDs.
    for offset in range(0,len(rows),50):
        with urlopen(base+'/api/retail-explanation-clients?'+urlencode(scope|{'offset':str(offset),'limit':'50'}),timeout=120) as response:
            page=json.load(response);assert 'no-store' in response.headers['Cache-Control'] and page['total']==len(rows)
        assert 'source_client_id' not in json.dumps(page)
        for actual in page['clients']:
            expected=by_rank[actual['score_rank']]
            assert actual=={k:expected[k] for k in ('client_token','score_rank','predicted_probability')}
            assert actual['client_token'] not in seen;seen.add(actual['client_token'])
    assert len(seen)==4499
    selected=by_rank[4470];query=scope|{'client_token':selected['client_token']}
    expected=source|{'cohort_id':cohort,'client':{k:selected[k] for k in ('client_token','score_rank','predicted_probability','reference_probability','reconstruction_residual')},
                     'filters':{'client_token':selected['client_token']},'visibility':'private','public_release_approved':False}
    expected['client']['contributions']=[{'group':g,'probability_contribution':selected[g]} for g in source['feature_groups']]
    for endpoint in ('retail-client-explanation','retail-client-explanation-report'):
        with urlopen(base+'/api/'+endpoint+'?'+urlencode(query),timeout=120) as response:
            assert json.load(response)==expected and 'no-store' in response.headers['Cache-Control']
    assert sha256(ledger)==before
    write_new(output/'receipt.json',{'status':'PASS','completed_at':timestamp(),'cohort_id':cohort,'paged_records':len(seen),
              'selected_case_rank':4470,'api_file_parity':True,'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False})
    return {'status':'PASS','directory':str(output),'paged_records':len(seen)}


if __name__=='__main__':print(json.dumps(run(app_root()),indent=2))
