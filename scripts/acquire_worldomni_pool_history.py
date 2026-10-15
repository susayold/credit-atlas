"""Acquire issuer-linked historical pool workbooks, retaining original files."""
from pathlib import Path
from urllib.request import urlopen,Request
from html.parser import HTMLParser
import json,uuid,zipfile
from credit_atlas.workspace import timestamp,sha256,write_new

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=set()
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.links.add(dict(attrs).get('href',''))

root=Path.cwd();identifier='pool-history-source-'+uuid.uuid4().hex[:12]
folder=root/'data/private/structured'/identifier;folder.mkdir(parents=True)
records=[]
def fetch(name,url):
    with urlopen(Request(url,headers={'User-Agent':'CreditAtlas internal research'}),timeout=45) as r:
        if r.status!=200 or r.url!=url:raise ValueError('Unexpected response/redirect')
        content=r.read(16*1024**2+1)
        if not content or len(content)>16*1024**2:raise ValueError('Empty/oversize issuer file')
        (folder/name).write_bytes(content)
        records.append({'file':name,'url':url,'http_status':200,'retrieved_at':timestamp(),'bytes':len(content),'sha256':sha256(folder/name)})
fetch('issuer-index.html','https://www.worldomni.com/asset_securities.html')
parser=Links();parser.feed((folder/'issuer-index.html').read_text(encoding='utf-8'))
for name in ['StaticPool-WOART.xlsx','ManagedPool-Retail.xlsx']:
    url='https://www.worldomni.com/abs/'+name
    if url not in parser.links:raise ValueError('Workbook not linked by issuer')
    fetch(name,url)
    with zipfile.ZipFile(folder/name) as z:
        if 'xl/workbook.xml' not in z.namelist() or sum(x.file_size for x in z.infolist())>128*1024**2 or z.testzip():
            raise ValueError('Invalid workbook')
write_new(folder/'acquisition-complete.json',{'source_id':identifier,'status':'ISSUER_POOL_HISTORY_ACQUIRED',
    'sources':records,'visibility':'private','public_release_approved':False,
    'scope':'Issuer-reported pool/cohort aggregates; not loan-level data, not WOART2025-A owned collateral',
    'formula_recalculated':False,'script_sha256':sha256(Path(__file__))})
print(identifier);print(json.dumps({'files':len(records),'bytes':sum(x['bytes'] for x in records)}))
