import json,uuid,subprocess,time,hashlib
from pathlib import Path
root=Path.cwd();out=root/'data/private/sec-documents'/('sec-documents-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
url='https://www.sec.gov/Archives/edgar/data/37996/000003799626000093/f-20260520.htm';target=out/'ford-obligation-8k.htm';partial=target.with_suffix('.partial')
r=subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https','--user-agent','CreditAtlas/1.0 local financial research','--connect-timeout','20','--max-time','90','--max-filesize','10000000','--output',str(partial),'--write-out','%{http_code}',url],capture_output=True,timeout=100)
receipt={'url':url,'http_status':r.stdout.decode(errors='replace'),'curl_exit':r.returncode,'full_text_reviewed':False,'legal_terms_extracted':False,'visibility':'private'}
if r.returncode==0 and r.stdout==b'200':
 partial.rename(target);receipt.update(status='ACQUIRED',file=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
else:receipt.update(status='HTTP_FAILED',error=r.stderr.decode(errors='replace')[:400])
(out/'acquisition.json').write_text(json.dumps(receipt,indent=2));print(out);print(json.dumps(receipt))
