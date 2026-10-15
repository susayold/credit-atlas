import json,threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
from credit_atlas.server import handler_for

@pytest.mark.parametrize('message,public',[
    ('Numeric Excel cells support up to 15 significant digits; use text for exact larger amounts/IDs','15 significant digits'),
    ('Input formulas must be replaced with explicit values; cached formula values are not trusted','Input formulas'),
    ('Sensitive path D:/private/customer-file.xlsx','Invalid Excel workbook')])
def test_excel_validation_messages_allowlisted(tmp_path,message,public):
    def upload(payload):raise ValueError(message)
    service=SimpleNamespace(root=tmp_path,excel_workbench=SimpleNamespace(upload=upload))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service));server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    try:
        request=Request(base+'/api/exposure-excel-import',data=b'{}',headers={'Content-Type':'application/json','Origin':base,'X-CreditAtlas-Client':'local'})
        with pytest.raises(HTTPError) as e:urlopen(request)
        assert e.value.code==400
        body=json.load(e.value);assert public in body['error']
        assert 'Sensitive path' not in body['error']
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
