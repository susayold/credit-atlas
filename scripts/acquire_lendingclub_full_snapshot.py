"""Acquire public publisher version, retaining issuer fidelity/rights uncertainty."""
import hashlib,json,time,uuid
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from credit_atlas.workspace import sha256,timestamp,write_new
root=Path(__file__).resolve().parents[1]
base='https://www.kaggle.com/api/v1/datasets/'
slug='wordsforthewise/lending-club';wanted=['accepted_2007_to_2018Q4.csv.gz','rejected_2007_to_2018Q4.csv.gz']
def run():
    if root.drive.upper()!='D:':raise ValueError('D: storage required')
    out=root/'data/private/retail'/('lendingclub-full-source-'+uuid.uuid4().hex[:12]);out.mkdir();records=[]
    def fetch(name,url,size=None):
        if urlsplit(url).scheme!='https' or urlsplit(url).hostname!='www.kaggle.com':raise ValueError('Unapproved publisher URL')
        p=out/(name+'.partial');n=0;h=hashlib.sha256();last=time.monotonic()
        with urlopen(Request(url,headers={'User-Agent':'CreditAtlas private credit research','Accept':'application/json' if name.endswith('.json') else '*/*'}),timeout=45) as r:
            if r.status!=200 or urlsplit(r.url).scheme!='https' or urlsplit(r.url).hostname not in {'www.kaggle.com','storage.googleapis.com'}:raise ValueError('Unexpected public publisher response')
            headers={k:r.headers.get(k) for k in ['Last-Modified','ETag','Content-Type','Content-Length']};host=urlsplit(r.url).hostname
            with p.open('xb') as f:
                while chunk:=r.read(1024**2):
                    n+=len(chunk)
                    if n>(512*1024**2 if size else 8*1024**2):raise ValueError('Publisher size bound exceeded')
                    if n==len(chunk) and name.endswith('.gz') and not chunk.startswith(b'\x1f\x8b'):raise ValueError('Expected GZIP,not login/error payload')
                    f.write(chunk);h.update(chunk)
                    if time.monotonic()-last>12:print(name,round(n/1024**2,1),'MiB',flush=True);last=time.monotonic()
        if not n or size and n!=size:raise ValueError('Publisher byte size mismatch')
        target=out/name;p.rename(target)
        records.append({'file':name,'url':url,'bytes':n,'sha256':h.hexdigest(),'response_final_host':host,'response_headers':headers,'retrieved_at':timestamp(),'publisher_size_verified':bool(size)})
        print(name,n,flush=True);return target
    try:
        metadata=json.loads(fetch('dataset.json',base+'view/'+slug).read_text())
        files=json.loads(fetch('files.json',base+'list/'+slug).read_text())
        if metadata['id']!=902 or metadata['currentVersionNumber']!=3 or metadata['licenseName']!='CC0: Public Domain':raise ValueError('Unexpected publisher dataset/version/license')
        if files.get('hasNextPageToken') or files.get('hasErrorMessage'):raise ValueError('Incomplete publisher inventory')
        inventory={f['name']:f for f in files['datasetFiles']}
        for name in wanted:
            if name not in inventory:raise ValueError('Missing accepted/rejected publisher file')
            fetch(name,base+'download/'+slug+'/'+name+'?datasetVersionNumber=3',inventory[name]['totalBytes'])
        write_new(out/'acquisition-complete.json',{'status':'PUBLIC_PUBLISHER_SNAPSHOT_ACQUIRED','source_id':out.name,'sources':records,
            'dataset_ref':slug,'dataset_version':3,'dataset_metadata':metadata,'publisher_file_inventory':files,
            'completed_at':timestamp(),'script_sha256':sha256(Path(__file__)),'gzip_full_integrity_verified':False,
            'original_issuer_fidelity_verified':False,'issuer_redistribution_rights_verified':False,
            'rights_note':'Publisher declaresCC0;uploader description mentions original issuer TOS concerns and signed-in FICO acquisition. No issuer-rights certification or public-release approval inferred.',
            'temporal_target_qualified':False,'model_training_performed':False,'visibility':'private','public_release_approved':False})
        print(out);print(sha256(out/'acquisition-complete.json'))
    except Exception as e:
        write_new(out/'acquisition-failed.json',{'status':'INCOMPLETE','sources':records,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)})
        raise
if __name__=='__main__':run()
