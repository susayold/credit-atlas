"""Acquire latest issuer-linked official statements, preserving actual identity."""
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,urlopen
from credit_atlas.workspace import sha256,timestamp,write_new

root=Path(__file__).resolve().parents[1]
index='https://www.ebmud.com/about-us/financial-information/official-statements'
labels={'Water System Revenue Bonds, Series 2026A & 2026B':'water-official-statement.pdf',
        'Wastewater System Revenue Bonds, Series 2026A & 2026B':'wastewater-official-statement.pdf'}
class Links(HTMLParser):
    def __init__(self):super().__init__();self.href=None;self.parts=[];self.links={}
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.parts=[]
    def handle_data(self,data):
        if self.href:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href:
            text=' '.join(''.join(self.parts).split())
            if text in labels:
                if text in self.links:raise ValueError('Duplicate issuer source label')
                self.links[text]=urljoin(index,self.href)
            self.href=None

def run():
    if root.drive.upper()!='D:':raise ValueError('D: storage required')
    out=root/'data/private/business'/('utility-contract-source-'+uuid.uuid4().hex[:12]);out.mkdir()
    records=[]
    def fetch(name,url,label):
        if urlsplit(url).scheme!='https' or urlsplit(url).hostname!='www.ebmud.com':raise ValueError('Unapproved source origin')
        partial=out/(name+'.partial');size=0
        with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 private historical credit research'}),timeout=45) as response:
            if response.status!=200 or urlsplit(response.url).hostname!='www.ebmud.com' or urlsplit(response.url).scheme!='https':raise ValueError('Unexpected response origin')
            headers={k:response.headers.get(k) for k in ['Last-Modified','ETag','Content-Type']}
            with partial.open('xb') as f:
                while chunk:=response.read(1024**2):
                    size+=len(chunk)
                    if size>32*1024**2:raise ValueError('Source size bound exceeded')
                    f.write(chunk)
        if not size or name.endswith('.pdf') and not partial.read_bytes().startswith(b'%PDF-'):raise ValueError('Invalid source file')
        target=out/name;partial.rename(target)
        records.append({'file':name,'url':url,'index_label':label,'bytes':size,'sha256':sha256(target),'retrieved_at':timestamp(),'response_headers':headers})
        print(name,size,flush=True);return target
    try:
        p=fetch('official-statements.html',index,'Official statements index')
        parser=Links();parser.feed(p.read_text(encoding='utf8'))
        if set(parser.links)!=set(labels):raise ValueError('Missing issuer-linked statements')
        for label,name in labels.items():fetch(name,parser.links[label],label)
        write_new(out/'acquisition-complete.json',{'status':'OFFICIAL_STATEMENTS_ACQUIRED','source_id':out.name,'sources':records,
            'script_sha256':sha256(Path(__file__)),'completed_at':timestamp(),'document_identity_verified':False,
            'contractual_compliance_qualified':False,'visibility':'private','public_release_approved':False})
        print(out);print(sha256(out/'acquisition-complete.json'))
    except Exception as e:
        write_new(out/'acquisition-failed.json',{'status':'INCOMPLETE','sources':records,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)})
        raise
if __name__=='__main__':run()
