"""Acquire issuer-linked EBMUD actual debt-service disclosures; no guessed URLs."""
import time,uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,urlopen
from credit_atlas.workspace import sha256,timestamp,write_new

ROOT=Path(__file__).resolve().parents[1]
INDEX='https://www.ebmud.com/about-us/financial-information/financial-reports'
LABELS={
 'FY 2025 Annual Comprehensive Financial Report':'ebmud-acfr-2025.pdf',
 'FY 2024 Annual Comprehensive Financial Report':'ebmud-acfr-2024.pdf',
 'FY 2023 Annual Comprehensive Financial Report':'ebmud-acfr-2023.pdf',
 'FY 2025 Unaudited Continuing Disclosure Information Statement':'ebmud-continuing-2025.pdf',
 'FY 2024 Unaudited Continuing Disclosure Information Statement':'ebmud-continuing-2024.pdf'}

class Links(HTMLParser):
    def __init__(self):super().__init__();self.href=None;self.text=[];self.links={}
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.text=[]
    def handle_data(self,text):
        if self.href:self.text.append(text)
    def handle_endtag(self,tag):
        if tag=='a' and self.href:
            label=' '.join(''.join(self.text).split())
            if label in LABELS:
                if label in self.links:raise ValueError('Duplicate source label')
                self.links[label]=urljoin(INDEX,self.href)
            self.href=None

def run():
    if ROOT.drive.upper()!='D:':raise ValueError('D: workspace required')
    out=ROOT/'data/private/business'/('utility-debt-source-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
    records=[]
    def fetch(name,url,label):
        if urlsplit(url).scheme!='https' or urlsplit(url).hostname!='www.ebmud.com':raise ValueError('Unapproved issuer origin')
        partial=out/(name+'.partial')
        with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 local debt-service research'}),timeout=45) as r:
            if r.status!=200 or urlsplit(r.url).scheme!='https' or urlsplit(r.url).hostname!='www.ebmud.com':raise ValueError('Unexpected source origin')
            headers={k:r.headers.get(k) for k in ['Last-Modified','ETag','Content-Type']};size=0
            with partial.open('xb') as f:
                while chunk:=r.read(1024**2):
                    size+=len(chunk)
                    if size>32*1024**2:raise ValueError('Source size bound exceeded')
                    f.write(chunk)
        if not size:raise ValueError('Empty source')
        if name.endswith('.pdf') and not partial.read_bytes().startswith(b'%PDF-'):raise ValueError('Invalid PDF')
        target=out/name;partial.rename(target)
        records.append({'file':name,'url':url,'index_label':label,'bytes':size,'sha256':sha256(target),'retrieved_at':timestamp(),'response_headers':headers})
        print(name,size,flush=True);return target
    try:
        index=fetch('financial-reports.html',INDEX,'Issuer financial reports index')
        links=Links();links.feed(index.read_text(encoding='utf8'))
        if set(links.links)!=set(LABELS):raise ValueError('Missing issuer-linked source documents')
        for label,name in LABELS.items():time.sleep(.4);fetch(name,links.links[label],label)
        write_new(out/'acquisition-complete.json',{'status':'ISSUER_DEBT_SERVICE_DOCUMENTS_ACQUIRED','source_id':out.name,'sources':records,
            'script_sha256':sha256(Path(__file__)),'completed_at':timestamp(),'source_tables_extracted':False,
            'contractual_compliance_qualified':False,'dscr_recomputed':False,'visibility':'private','public_release_approved':False})
        print(out);print(sha256(out/'acquisition-complete.json'))
    except Exception as e:
        write_new(out/'acquisition-failed.json',{'status':'INCOMPLETE','sources':records,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)})
        raise

if __name__=='__main__':run()
