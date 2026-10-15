"""Acquire disclosed note terms for source-based contractual cash-flow research."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,uuid
root=Path(__file__).resolve().parents[1]
folder=root/'data/private/sec-documents'/('sec-documents-'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
url='https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/268bd5d1-342f-4db5-b2e7-2dcdf8c95598.pdf'
p=folder/'apple-notes-20250512.pdf';partial=p.with_suffix('.partial')
r=subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https','--user-agent','CreditAtlas/1.0 local financial research','--connect-timeout','20','--max-time','90','--max-filesize','10000000','--output',str(partial),'--write-out','%{http_code}',url],capture_output=True,timeout=100)
receipt={'url':url,'discovered_on':'https://www.sec.gov/Archives/edgar/data/320193/000114036125018400/ef20048691_ex4-1.htm','discovery_method':'Search CIK-hosted PDF; identity/terms verified separately','http_status':r.stdout.decode(),'curl_exit':r.returncode,'retrieved_at':datetime.now(timezone.utc).isoformat(),'visibility':'private','legal_terms_qualified':False}
if r.returncode==0 and r.stdout==b'200' and partial.read_bytes().startswith(b'%PDF'):
 partial.rename(p);receipt.update(status='ACQUIRED',file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
else:receipt.update(status='HTTP_OR_PDF_FAILED')
(folder/'acquisition.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print(folder);print(json.dumps(receipt))
