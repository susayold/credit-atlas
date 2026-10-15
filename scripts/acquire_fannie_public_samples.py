"""Acquire issuer-linked public samples/reference layouts; no authenticated dataset."""
import json
import subprocess
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from credit_atlas.workspace import sha256,timestamp,write_new

ROOT=Path(__file__).resolve().parents[1]
HOST='capitalmarkets.fanniemae.com'
PAGES={'single-family':'https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data',
       'multifamily':'https://capitalmarkets.fanniemae.com/credit-risk-transfer/multifamily-loan-performance-data'}
LIMIT=16*1024**2

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a' and dict(attrs).get('href'):self.links.append(dict(attrs)['href'])

def run():
    if ROOT.drive.upper()!='D:':raise ValueError('D: storage required')
    out=ROOT/'data/private/mortgage'/('fannie-public-samples-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
    records=[]
    def fetch(name,url,family,kind):
        if urlsplit(url).scheme!='https' or urlsplit(url).hostname!=HOST:raise ValueError('Unapproved source host')
        partial=out/(name+'.partial')
        response=subprocess.run(['curl.exe','--fail','--silent','--show-error','--location','--max-redirs','3','--proto','=https','--proto-redir','=https','--max-time','60','--max-filesize',str(LIMIT),'--output',str(partial),'--write-out','%{json}',url],capture_output=True,timeout=65)
        if response.returncode:raise RuntimeError(f'Public source transport failed ({response.returncode})')
        meta=json.loads(response.stdout)
        if meta['http_code']!=200 or urlsplit(meta['url_effective']).hostname!=HOST:raise ValueError('Unexpected source response')
        size=partial.stat().st_size
        if not 0<size<=LIMIT:raise ValueError('Invalid source size')
        if kind=='layout' and not partial.read_bytes().startswith(b'%PDF-'):raise ValueError('Expected PDF layout')
        if kind=='sample' and b'<html' in partial.read_bytes()[:1000].lower():raise ValueError('HTML is not a sample')
        target=out/name;partial.rename(target)
        records.append({'file':name,'requested_url':url,'response_url':meta['url_effective'],'family':family,'kind':kind,'bytes':size,'sha256':sha256(target),'retrieved_at':timestamp(),'content_type':meta['content_type'],'http_status':200})
        print(name,size,flush=True)
        return target
    try:
        for family,url in PAGES.items():
            page=fetch(family+'-index.html',url,family,'index')
            links=Links();links.feed(page.read_text(encoding='utf-8'))
            selected=[]
            for href in links.links:
                link=urljoin(url,href);path=urlsplit(link).path.lower()
                if urlsplit(link).hostname==HOST and ('sample' in path or ('glossary' in path and path.endswith('.pdf'))):
                    if link not in selected:selected.append(link)
            if not selected:raise ValueError('No issuer-linked sample/layout found')
            for i,link in enumerate(selected,1):
                kind='layout' if 'glossary' in urlsplit(link).path.lower() else 'sample'
                extension='.pdf' if kind=='layout' else '.csv'
                fetch(f'{family}-{kind}-{i}{extension}',link,family,kind)
        write_new(out/'acquisition-complete.json',{'status':'PUBLIC_ISSUER_SAMPLES_AND_LAYOUTS_ACQUIRED','source_id':out.name,'sources':records,'script_sha256':sha256(Path(__file__)),'completed_at':timestamp(),'authenticated_full_dataset_acquired':False,'representative_training_population_qualified':False,'source_rights_for_external_use_qualified':False,'visibility':'private','public_release_approved':False})
        print(out);print(sha256(out/'acquisition-complete.json'))
    except Exception as error:
        write_new(out/'acquisition-failed.json',{'status':'FAIL','sources_completed':records,'error_type':type(error).__name__,'error':str(error),'completed_at':timestamp()})
        print(out,flush=True);raise

if __name__=='__main__':run()
