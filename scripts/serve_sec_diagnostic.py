"""Owned local server with private SEC exception trace for runtime diagnosis."""
import traceback
from pathlib import Path
from uuid import uuid4
from credit_atlas.service import ResearchService
from credit_atlas.server import LocalResearchServer,handler_for
from credit_atlas.workspace import write_new,timestamp

root=Path.cwd().resolve();out=root/'artifacts/private'/('sec-http-diagnostic-'+uuid4().hex[:12]);out.mkdir()
service=ResearchService(root);service.runs()
original=service.sec_views.report
def traced_report(identifier,query):
    try:return original(identifier,query)
    except Exception as error:
        token=uuid4().hex[:12]
        (out/(token+'.txt')).write_text(traceback.format_exc(),encoding='utf-8')
        write_new(out/(token+'.json'),{'exception_type':type(error).__name__,'query':query,'time':timestamp()})
        raise
service.sec_views.report=traced_report
with LocalResearchServer(('127.0.0.1',8770),handler_for(service)) as server:
    server.daemon_threads=True
    print('Diagnostic server '+str(out),flush=True)
    server.serve_forever()
