from pathlib import Path
import base64
import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import pytest
from credit_atlas.excel_workbench import ExcelWorkbench
from credit_atlas.server import handler_for
from credit_atlas.workspace import sha256
from tests.test_excel_workspace import TEMPLATE


def test_http_template_intake_and_origin_contract(tmp_path):
    source=Path(__file__).parents[1]/'apps/excel/build_workbook.mjs'
    builder=tmp_path/'apps/excel/build_workbook.mjs'; builder.parent.mkdir(parents=True); builder.write_bytes(source.read_bytes())
    service=SimpleNamespace(root=tmp_path); service.excel_workbench=ExcelWorkbench(service)
    service.excel_workbench.template_file=TEMPLATE; service.excel_workbench.template_hash=sha256(TEMPLATE)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service)); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    data=json.dumps({'filename':'input.xlsx','content_base64':base64.b64encode(TEMPLATE.read_bytes()).decode()}).encode()
    headers={'Content-Type':'application/json','X-CreditAtlas-Client':'local','Origin':base}
    try:
        with urlopen(base+'/api/exposure-excel-template') as response:
            assert response.read()==TEMPLATE.read_bytes() and 'no-store' in response.headers['Cache-Control']
        with urlopen(Request(base+'/api/exposure-excel-import',data=data,headers=headers)) as response:
            result=json.load(response); assert response.status==201 and result['rows']==3
        with pytest.raises(HTTPError) as error: urlopen(Request(base+'/api/exposure-excel-import',data=data,headers={**headers,'Origin':'https://external.example'}))
        assert error.value.code==403
        with pytest.raises(HTTPError) as error: urlopen(base+'/api/exposure-excel-template?path=other')
        assert error.value.code==400
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
