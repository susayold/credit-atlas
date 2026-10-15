import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
import pytest
from credit_atlas.retail_policy_views import RetailPolicyViews
from credit_atlas.server import handler_for
from tests.test_retail_policy import evidence,FREEZE,plan

def test_private_policy_report_preview_mutation_and_origin_contract(evidence):
    root,identifier,_=evidence
    service=SimpleNamespace(root=root,retail_policy_views=RetailPolicyViews(root))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service)); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base='http://127.0.0.1:'+str(server.server_port); query={'policy_id':identifier,'freeze_id':FREEZE}
    try:
        with urlopen(base+'/api/retail-policy-report?'+urlencode(query)) as response:
            result=json.load(response); assert result['records']==4 and 'source_client_id' not in str(result)
            assert 'attachment' in response.headers['Content-Disposition'] and 'no-store' in response.headers['Cache-Control']
        preview={**query,'lower_threshold':'0.2','upper_threshold':'0.5','review_capacity':'2',
            **{a+'_'+y:v for a,row in plan()['cost_matrix'].items() for y,v in row.items()}}
        with urlopen(base+'/api/retail-policy-preview?'+urlencode(preview)) as response: assert json.load(response)['status']=='UNSAVED_POLICY_PREVIEW'
        with pytest.raises(HTTPError) as error: urlopen(base+'/api/retail-policy?'+urlencode({**query,'final_test':'true'}))
        assert error.value.code==400
        data=json.dumps(plan()).encode(); headers={'Origin':base,'Content-Type':'application/json','X-CreditAtlas-Client':'local'}
        with urlopen(Request(base+'/api/retail-policies',data=data,headers=headers)) as response:
            assert response.status==201 and json.load(response)['policy_id']!=identifier
        with pytest.raises(HTTPError) as error: urlopen(Request(base+'/api/retail-policies',data=data,headers={**headers,'Origin':'https://external.example'}))
        assert error.value.code==403
        with pytest.raises(HTTPError) as error: urlopen(base+'/api/retail-policies?'+urlencode({'freeze_id':FREEZE,'case':'all'}))
        assert error.value.code==400
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
