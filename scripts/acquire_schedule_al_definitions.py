"""Download the official 2025 CFR Schedule AL PDF/XML; no SEC restriction bypass."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
import uuid,json
from credit_atlas.workspace import sha256,timestamp,write_new

ROOT=Path(__file__).resolve().parents[1]
BASE='https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/'

def acquire():
    folder=ROOT/'data/private/structured'/('schedule-al-'+uuid.uuid4().hex[:12]);folder.mkdir()
    records=[]
    try:
        for extension in ['pdf','xml']:
            name='CFR-2025-title17-vol3-sec229-1125.'+extension
            url=BASE+extension+'/'+name
            with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 local source qualification research'}),timeout=60) as r:
                if r.status!=200 or urlsplit(r.url).hostname!='www.govinfo.gov' or urlsplit(r.url).scheme!='https':raise ValueError('Unexpected source origin/status')
                payload=r.read(4*1024**2+1)
                if not payload or len(payload)>4*1024**2:raise ValueError('Download bound exceeded')
            if extension=='pdf' and not payload.startswith(b'%PDF-'):raise ValueError('Invalid PDF')
            if extension=='xml' and not payload.lstrip().startswith(b'<?xml'):raise ValueError('Invalid XML')
            path=folder/name;path.write_bytes(payload)
            records.append({'file':name,'url':url,'bytes':len(payload),'sha256':sha256(path),'retrieved_at':timestamp()})
            print(name,len(payload),flush=True)
        write_new(folder/'acquisition-complete.json',{'source_id':folder.name,'status':'OFFICIAL_CFR_DEFINITIONS_ACQUIRED',
            'edition':'2025-04-01','section':'17 CFR229.1125, Schedule AL','sources':records,
            'completed_at':timestamp(),'script_sha256':sha256(Path(__file__)),
            'current_2026_rule_verified':False,'xsd_acquired':False,'raw_filing_xml_acquired':False,
            'mirror_fidelity_verified':False,'model_ready':False,'visibility':'private','public_release_approved':False})
        print(folder)
    except Exception as e:
        write_new(folder/'acquisition-failed.json',{'status':'INCOMPLETE','sources':records,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)})
        raise

if __name__=='__main__':acquire()
