import json,uuid,subprocess,time,hashlib
from pathlib import Path
root=Path.cwd();out=root/'data/private/sec-documents'/('sec-documents-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
url='https://d18rn0p25nwr6d.cloudfront.net/CIK-0000037996/db1e36e1-15dc-4195-944a-6476ccd41e63.pdf';target=out/'ford-term-loan-20250728.pdf';partial=target.with_suffix('.partial')
r=subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https','--user-agent','CreditAtlas/1.0 local financial research','--connect-timeout','20','--max-time','90','--max-filesize','10000000','--output',str(partial),'--write-out','%{http_code}',url],capture_output=True,timeout=100)
receipt={'url':url,'discovery':'Ford investor relations filing PDF; identity must be checked against document before mapping','http_status':r.stdout.decode(errors='replace'),'curl_exit':r.returncode,'full_text_reviewed':False,'legal_terms_extracted':False,'visibility':'private'}
if r.returncode==0 and r.stdout==b'200':
 partial.rename(target);receipt.update(status='ACQUIRED',file=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
else:receipt.update(status='HTTP_FAILED',error=r.stderr.decode(errors='replace')[:400])
(out/'acquisition.json').write_text(json.dumps(receipt,indent=2));print(out);print(json.dumps(receipt))
