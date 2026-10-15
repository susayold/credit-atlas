"""Acquire issuer-hosted 2026 amendment bundle; never infer legal qualification."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess,uuid

root=Path(__file__).resolve().parents[1]
folder=root/'data/private/sec-documents'/('sec-documents-'+uuid.uuid4().hex[:12])
folder.mkdir(parents=True)
url='https://d18rn0p25nwr6d.cloudfront.net/CIK-0000037996/9b2691ed-e80a-4036-a128-2c2b22ec8668.pdf'
path=folder/'ford-credit-amendments-20260415.pdf'
partial=path.with_suffix('.partial')
r=subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https','--user-agent','CreditAtlas/1.0 local financial research','--connect-timeout','20','--max-time','90','--max-filesize','20000000','--output',str(partial),'--write-out','%{http_code}',url],capture_output=True,timeout=100)
receipt={'url':url,'discovered_on':'https://www.sec.gov/Archives/edgar/data/37996/000003799626000079/f-20260415.htm','discovery_method':'Web search issuer CIK-hosted PDF; identity checked separately','http_status':r.stdout.decode(),'curl_exit':r.returncode,'retrieved_at':datetime.now(timezone.utc).isoformat(),'visibility':'private','legal_terms_qualified':False}
if r.returncode==0 and r.stdout==b'200' and partial.read_bytes().startswith(b'%PDF'):
    partial.rename(path)
    receipt.update(status='ACQUIRED',bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),file=path.name)
else:
    receipt.update(status='HTTP_OR_PDF_FAILED')
(folder/'acquisition.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(folder)
print(json.dumps(receipt))
