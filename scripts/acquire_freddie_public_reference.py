"""Capture bounded publisher reference files, without authentication or terms actions."""
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4

ROOT=Path.cwd();out=ROOT/'data/private/mortgage'/('freddie-public-reference-'+uuid4().hex[:12]);out.mkdir()
sources=[
 ('general-user-guide.pdf','https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf'),
 ('clarity-download-announcement.html','https://capitalmarkets.freddiemac.com/clarity/whats-new/december-2025-clarity-updates'),
 ('release-47-sample-files.zip','https://www.freddiemac.com/fmac-resources/research/docs/release-47-sample-files.zip'),
 ('file-layout-july-2026.xlsx','https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx'),
]
files=[]
for name,url in sources:
    result=subprocess.run(['curl.exe','--fail','--location','--silent','--show-error','--max-time','45','--max-filesize','5242880','--output',str(out/name),'--write-out','%{json}',url],capture_output=True,text=True,timeout=55)
    if result.returncode:
        (out/'failed.json').write_text(json.dumps({'status':'DOWNLOAD_FAILED','url':url,'curl_exit_code':result.returncode,'annual_vintages_added':0,'successful_files':files},indent=2),encoding='utf-8')
        raise RuntimeError(f'Public reference download failed: curl exit {result.returncode}')
    meta=json.loads(result.stdout);data=(out/name).read_bytes()
    assert len(data)<=5*1024*1024,'Source exceeded bounded reference size'
    if name.endswith('.pdf'):assert data.startswith(b'%PDF-')
    if name.endswith(('.zip','.xlsx')):
        with zipfile.ZipFile(out/name) as archive:
            bad=archive.testzip()
            if bad is not None: raise ValueError(f'ZIP CRC failure: {bad}')
            members=archive.infolist()
            if not members or any(x.filename.startswith(('/', '\\')) or '..' in Path(x.filename).parts for x in members):
                raise ValueError('Unexpected or unsafe public reference ZIP members')
            if sum(x.file_size for x in members)>20*1024*1024:
                raise ValueError('Expanded ZIP exceeds public reference bound')
    files.append({'file':name,'requested_url':url,'resolved_url':meta['url_effective'],'http_status':meta['http_code'],'content_type':meta.get('content_type'),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat(),'publisher_publication_at':None})
receipt={'status':'ACQUIRED','source_role':'public_reference_not_annual_loan_dataset','files':files,'added_annual_vintages':0,'publisher_release_authenticated_for_supplied_zip':False,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'files':len(files),'bytes':sum(x['bytes'] for x in files),'added_annual_vintages':0}))
