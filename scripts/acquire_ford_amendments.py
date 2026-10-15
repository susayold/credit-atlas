from pathlib import Path
import json,subprocess,uuid,hashlib
root=Path.cwd();folder=root/'data/private/sec-documents'/('sec-documents-'+uuid.uuid4().hex[:12]);folder.mkdir();url='https://d18rn0p25nwr6d.cloudfront.net/CIK-0000037996/6462578d-a644-47e9-b4f6-ac4078ebb2fb.pdf';p=folder/'ford-credit-amendments-20250417.pdf';partial=p.with_suffix('.partial');r=subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https','--user-agent','CreditAtlas/1.0 local financial research','--connect-timeout','20','--max-time','90','--max-filesize','10000000','--output',str(partial),'--write-out','%{http_code}',url],capture_output=True,timeout=100);receipt={'url':url,'discovered_on':'https://shareholder.ford.com/financials/sec-filings/sec-filings-details/default.aspx?FilingId=18377894','http_status':r.stdout.decode(),'curl_exit':r.returncode,'visibility':'private','legal_terms_qualified':False}
if r.returncode==0 and r.stdout==b'200':
 partial.rename(p);receipt.update(status='ACQUIRED',bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),file=p.name)
else:receipt.update(status='HTTP_FAILED')
(folder/'acquisition.json').write_text(json.dumps(receipt,indent=2));print(folder);print(json.dumps(receipt))
