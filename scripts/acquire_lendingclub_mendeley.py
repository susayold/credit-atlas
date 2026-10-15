"""Credential-free published dataset with publisher content-hash verification."""
import hashlib,json,re,time,uuid
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,urlopen
from credit_atlas.workspace import sha256,timestamp,write_new
root=Path(__file__).resolve().parents[1]
index='https://data.mendeley.com/datasets/mvvd3dnfyz/1'
api='https://data.mendeley.com/public-api/datasets/mvvd3dnfyz/files?'+urlencode({'folder_id':'root','version':'1','$start':'0','$limit':'1000'})
def run():
    if root.drive.upper()!='D:':raise ValueError('D: storage required')
    out=root/'data/private/retail'/('lendingclub-source-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
    sources=[]
    def fetch(name,url,expected=None):
        parts=urlsplit(url)
        if parts.scheme!='https' or parts.hostname!='data.mendeley.com':raise ValueError('Unapproved publisher origin')
        partial=out/(name+'.partial');size=0;h=hashlib.sha256();last=time.monotonic()
        with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 private credit research','Accept':'application/vnd.mendeley-public-dataset.1+json' if name.endswith('.json') else '*/*'}),timeout=45) as r:
            if r.status!=200 or urlsplit(r.url).scheme!='https':raise ValueError('Unexpected publisher response')
            headers={k:r.headers.get(k) for k in ['Last-Modified','ETag','Content-Type']};final_host=urlsplit(r.url).hostname
            with partial.open('xb') as f:
                while chunk:=r.read(1024**2):
                    size+=len(chunk)
                    if size>512*1024**2:raise ValueError('Publisher file exceeds size bound')
                    f.write(chunk);h.update(chunk)
                    if time.monotonic()-last>12:print(name,round(size/1024**2,1),'MiB',flush=True);last=time.monotonic()
        if not size:raise ValueError('Empty publisher file')
        if expected and (size!=expected['size'] or h.hexdigest()!=expected['sha256_hash']):raise ValueError('Publisher size/SHA mismatch')
        target=out/name;partial.rename(target)
        sources.append({'file':name,'url':url,'bytes':size,'sha256':h.hexdigest(),'retrieved_at':timestamp(),
            'response_headers':headers,'response_final_host':final_host,'publisher_hash_verified':bool(expected)})
        print(name,size,flush=True);return target
    try:
        page=fetch('dataset.html',index);html=page.read_text(encoding='utf8')
        initial=json.JSONDecoder().raw_decode(html.split('window.INITIAL_STATE = ',1)[1])[0]['dataset']['snapshot']
        if initial['id']!='mvvd3dnfyz' or initial['version']!=1 or initial['doi']!='10.17632/mvvd3dnfyz.1' or initial['is_confidential']:raise ValueError('Unexpected dataset identity')
        if initial['licence']['short_name']!='CC BY 4.0':raise ValueError('Dataset license changed')
        filelist=fetch('files.json',api);items=json.loads(filelist.read_text())
        if not isinstance(items,list) or len(items)!=1:raise ValueError('Unexpected publisher file inventory')
        item=items[0];details=item['content_details']
        if item['status']!='COMPLETED' or not re.fullmatch(r'[a-zA-Z0-9_.-]+\.csv',item['filename']) or details['size']>512*1024**2:raise ValueError('Unexpected dataset file')
        fetch(item['filename'],details['download_url'],details)
        write_new(out/'acquisition-complete.json',{'status':'PUBLISHED_DATASET_ACQUIRED','source_id':out.name,'sources':sources,
            'dataset':initial,'publisher_file_metadata':items,'script_sha256':sha256(Path(__file__)),'completed_at':timestamp(),
            'original_lendingclub_fidelity_verified':False,'temporal_target_qualified':False,'model_training_performed':False,
            'visibility':'private','public_release_approved':False})
        print(out);print(sha256(out/'acquisition-complete.json'))
    except Exception as e:
        write_new(out/'acquisition-failed.json',{'status':'INCOMPLETE','sources':sources,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)})
        raise
if __name__=='__main__':run()
