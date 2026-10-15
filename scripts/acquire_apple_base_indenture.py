"""Discover document via the issuer's public SEC feed, then acquire selected PDF."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from datetime import datetime,timezone
import hashlib,json,subprocess,uuid
root=Path(__file__).resolve().parents[1]
folder=root/'data/private/sec-documents'/('sec-documents-'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
q={'exchange':'CIK','symbol':'0000320193','year':2024,'pageSize':100,'pageNumber':0,'formGroupIdList':'','filingTypeList':'S-3ASR','excludeNoDocuments':'true','includeHtmlDocument':'true','LanguageId':1,'includeTags':'true','excludeSelection':1}
feed='https://investor.apple.com/feed/SECFiling.svc/GetEdgarFilingList?'+urlencode(q)
with urlopen(Request(feed,headers={'User-Agent':'CreditAtlas/1.0 local financial research'}),timeout=30) as response:
    raw=response.read(4000001)
    if len(raw)>4000000:raise ValueError('Oversize issuer metadata')
(folder/'issuer-feed.json').write_bytes(raw)
items=json.loads(raw)['GetEdgarFilingListResult']
item=next(x for x in items if x['FilingDate']=='11/01/2024 00:00:00' and x['FilingTypeMnemonic']=='S-3ASR' and x['StockSymbol']=='0000320193')
url=next(d['Url'] for d in item['DocumentList'] if d['DocumentType']=='CONVPDF')
if not url.startswith('https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/') or not url.endswith('.pdf'):raise ValueError('Unexpected issuer document host/type')
p=folder/'apple-base-indenture-20241101.pdf';partial=p.with_suffix('.partial')
r=subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https','--user-agent','CreditAtlas/1.0 local financial research','--connect-timeout','20','--max-time','90','--max-filesize','10000000','--output',str(partial),'--write-out','%{http_code}',url],capture_output=True,timeout=100)
receipt={'url':url,'discovered_on':'https://investor.apple.com/sec-filings/default.aspx','discovery_method':'Issuer public SEC feed used by its widget; no authentication','feed_url':feed,'feed_file':'issuer-feed.json','feed_sha256':hashlib.sha256(raw).hexdigest(),'issuer_filing_id':item['FilingId'],'cik':'0000320193','filing_date':'2024-11-01','form':'S-3ASR','http_status':r.stdout.decode(),'curl_exit':r.returncode,'retrieved_at':datetime.now(timezone.utc).isoformat(),'visibility':'private','legal_terms_qualified':False}
if r.returncode==0 and r.stdout==b'200' and partial.read_bytes().startswith(b'%PDF'):
    partial.rename(p);receipt.update(status='ACQUIRED',file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
else:receipt.update(status='HTTP_OR_PDF_FAILED')
(folder/'acquisition.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print(folder);print(json.dumps(receipt))
