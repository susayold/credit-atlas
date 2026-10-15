"""Issuer workbook captured from verified server-side SEC analyses."""
import json
import os
from pathlib import Path
import subprocess
import uuid
from .sec_trends import report as trend_report
from .sec_coverage import report as coverage_report


def document(views,query):
    if not isinstance(query,dict) or set(query)-{'view_id','cik','asof','years','interest_concept'} or 'view_id' not in query:
        raise ValueError('SEC workbook accepts bounded source filters only')
    if any(not isinstance(v,str) for v in query.values()):raise ValueError('SEC workbook string filters required')
    key=query['view_id']
    coverage=coverage_report(views,key,query)
    trend=trend_report(views,key,{k:v for k,v in query.items() if k!='interest_concept'})
    if not trend['periods']:raise ValueError('No SEC annual periods before cutoff')
    if coverage['source_capture']!= {**trend['source_capture'],**{k:coverage['source_capture'][k] for k in ['facts_sha256','concepts_sha256']}}:
        raise ValueError('SEC source captures changed during workbook capture')
    return {'schema_version':1,'trend':trend,'coverage':coverage,'visibility':'private','public_release_approved':False}


def export_workbook(service,query):
    report=document(service.sec_views,query)
    return _export_document(service,report,'build_sec_workbook.mjs','CreditAtlas-SEC.xlsx','sec-workbook-')


def _export_document(service,report,builder,filename,prefix):
    # Builder, filename and prefix are fixed by server code, never client filters.
    directory=service.root/'artifacts/private'/(prefix+uuid.uuid4().hex[:12]);directory.mkdir()
    source=directory/'report.json';source.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
    node=Path(os.environ.get('CREDIT_ATLAS_NODE',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')))
    if not node.is_file():raise ValueError('Bundled Node runtime unavailable')
    tmp=service.root/'artifacts/private/tmp';tmp.mkdir(exist_ok=True)
    output=directory/filename
    subprocess.run([str(node),str(service.root/'scripts'/builder),str(source),str(output)],cwd=service.root,
                   env={**os.environ,'TEMP':str(tmp),'TMP':str(tmp)},check=True,capture_output=True,timeout=180)
    return output.read_bytes()
