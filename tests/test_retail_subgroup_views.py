import json
import threading
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
from urllib.request import urlopen,Request
from urllib.parse import urlencode
from urllib.error import HTTPError
import pytest
from credit_atlas import retail_subgroups as groups
from credit_atlas.retail_subgroup_views import RetailSubgroupViews
from credit_atlas.server import handler_for
from credit_atlas.workspace import sha256
from tests.test_retail_subgroups import rows,plan,RULE

def test_scoped_aggregate_export_cached_corruption_and_http_contract(tmp_path,monkeypatch):
    file=tmp_path/'source.txt';file.write_text('verified validation')
    monkeypatch.setattr(groups,'source',lambda root,p:(rows(),RULE,{'source.txt':sha256(file)}))
    import credit_atlas.retail_subgroups_saved as saved
    monkeypatch.setattr(saved,'source_saved',lambda root,p,policy_storage=None:(rows(),RULE,{'source.txt':sha256(file)}))
    identifier=groups.build(tmp_path,plan())['subgroups_id'];view=RetailSubgroupViews(tmp_path)
    scope={k:plan()[k] for k in ('policy_id','freeze_id')};query={**scope,'subgroups_id':identifier,'dimension':'sex'}
    report=view.report(query);assert len(report['groups'])==2 and all(r['dimension']=='sex' for r in report['groups'])
    assert 'source_client_id' not in str(report)
    with pytest.raises(ValueError,match='source mismatch'):view.report({**query,'freeze_id':'retail-freeze-cccccccccccc'})
    # A rewritten digest must not make numerically corrupted groups acceptable.
    folder=tmp_path/'artifacts/private'/identifier
    original_report=(folder/'report.json').read_bytes();original_receipt=(folder/'subgroups-complete.json').read_bytes()
    broken=json.loads(original_report);broken['overall']['records']+=1
    (folder/'report.json').write_text(json.dumps(broken))
    changed=json.loads(original_receipt);changed['outputs_sha256']['report.json']=sha256(folder/'report.json')
    (folder/'subgroups-complete.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='replay'):RetailSubgroupViews(tmp_path).report(query)
    (folder/'report.json').write_bytes(original_report);(folder/'subgroups-complete.json').write_bytes(original_receipt)
    service=SimpleNamespace(root=tmp_path,retail_subgroup_views=view)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
    try:
        with urlopen(base+'/api/retail-subgroup-report?'+urlencode(query)) as response:
            assert json.load(response)==report and 'attachment' in response.headers['Content-Disposition'] and 'no-store' in response.headers['Cache-Control']
        with pytest.raises(HTTPError) as error:urlopen(base+'/api/retail-subgroup?'+urlencode({**query,'dimension':'income'}))
        assert error.value.code==400
        data=json.dumps(plan()).encode();headers={'Origin':base,'Content-Type':'application/json','X-CreditAtlas-Client':'local'}
        with urlopen(Request(base+'/api/retail-subgroups',data=data,headers=headers)) as response:
            assert response.status==201 and json.load(response)['subgroups_id']!=identifier
        with pytest.raises(HTTPError) as error:urlopen(Request(base+'/api/retail-subgroups',data=data,headers={**headers,'Origin':'https://external.example'}))
        assert error.value.code==403
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    file.write_text('corrupt')
    with pytest.raises(ValueError,match='input evidence'):view.report(query)

def test_sql_demographic_join_materializes_only_selected_validation_ids(tmp_path,monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from credit_atlas.workspace import write_new
    folder=tmp_path/'artifacts/private'/plan()['policy_id'];folder.mkdir(parents=True)
    write_new(folder/'policy-complete.json',{})
    canonical=tmp_path/'artifacts/private/retail-case-fixture';canonical.mkdir()
    data=rows()+[{'source_client_id':1000,'target':1,'probability':.9,'SEX':999,'EDUCATION':None,'MARRIAGE':None,'AGE':999}]
    path=canonical/'clients.parquet';pq.write_table(pa.Table.from_pylist(data),path)
    report={'freeze_id':plan()['freeze_id'],'case_id':canonical.name,'cases':[{'id':'declared','rule':RULE}]}
    monkeypatch.setattr(groups,'verify_policy',lambda *args:(folder,{'outputs_sha256':{}},report))
    monkeypatch.setattr(groups,'lineage_pins',lambda *args:{str(path.relative_to(tmp_path)):sha256(path)})
    monkeypatch.setattr(groups,'pinned_scores',lambda *args:[{k:r[k] for k in ('source_client_id','target','probability')} for r in rows()])
    selected,_,_=groups.source(tmp_path,plan())
    assert len(selected)==80 and all(r['source_client_id']<80 for r in selected)
    import credit_atlas.retail_subgroups_saved as saved
    monkeypatch.setattr(saved,'verify_saved',lambda *args:(folder,{'outputs_sha256':{}},report))
    monkeypatch.setattr(saved,'lineage_pins',lambda *args:{str(path.relative_to(tmp_path)):sha256(path)})
    monkeypatch.setattr(saved,'pinned_scores',lambda *args:[{k:r[k] for k in ('source_client_id','target','probability')} for r in rows()])
    assert saved.source_saved(tmp_path,plan())[0]==selected
