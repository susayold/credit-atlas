"""Acquire SEC ABS v3.1 specification and safely extract its source bundle."""
import json,time,uuid,zipfile
from pathlib import Path,PurePosixPath
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from credit_atlas.workspace import sha256,timestamp,write_new

ROOT=Path(__file__).resolve().parents[1]
URL='https://www.sec.gov/files/absxml-31.zip'
INDEX='https://www.sec.gov/submit-filings/technical-specifications'

def acquire():
    if ROOT.drive.upper()!='D:':raise ValueError('D: workspace required')
    folder=ROOT/'data/private/structured'/('absee-spec-'+uuid.uuid4().hex[:12]);folder.mkdir()
    records=[]
    def fetch(name,url,limit):
        partial=folder/(name+'.partial');target=folder/name
        with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 local source qualification research'}),timeout=60) as r:
            if r.status!=200 or urlsplit(r.url).scheme!='https' or urlsplit(r.url).hostname!='www.sec.gov':raise ValueError('Unexpected official source origin/status')
            size=0
            with partial.open('xb') as f:
                while chunk:=r.read(1024**2):
                    size+=len(chunk)
                    if size>limit:raise ValueError('Source size bound exceeded')
                    f.write(chunk)
        if not size:raise ValueError('Empty source')
        partial.rename(target)
        records.append({'file':name,'url':url,'bytes':size,'sha256':sha256(target),'retrieved_at':timestamp()})
        return target
    try:
        # ZIP URL was discovered directly from the official specification index.
        pack=fetch('absxml-31.zip',URL,8*1024**2)
        time.sleep(.5)
        index=fetch('technical-specifications.html',INDEX,4*1024**2)
        if 'absxml-31.zip' not in index.read_text(encoding='utf8'):raise ValueError('Official index does not reference acquired version')
        extracted=[];base=folder/'bundle';base.mkdir()
        with zipfile.ZipFile(pack) as z:
            if len(z.infolist())>150 or sum(x.file_size for x in z.infolist())>32*1024**2:raise ValueError('ZIP inventory bound exceeded')
            if z.testzip():raise ValueError('Invalid ZIP CRC')
            for item in z.infolist():
                relative=PurePosixPath(item.filename)
                if relative.is_absolute() or '..' in relative.parts or '\\' in item.filename or ':' in item.filename:raise ValueError('Unsafe ZIP path')
                if item.is_dir():continue
                target=base.joinpath(*relative.parts);target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(z.read(item))
                extracted.append({'file':target.relative_to(folder).as_posix(),'bytes':item.file_size,'sha256':sha256(target)})
        receipt={'source_id':folder.name,'status':'OFFICIAL_SPECIFICATION_ACQUIRED','completed_at':timestamp(),
                 'version':'3.1','specification_date':'2023-09-18','sources':records,'extracted':extracted,
                 'script_sha256':sha256(Path(__file__)),'raw_filing_xml_acquired':False,'mirror_fidelity_verified':False,
                 'model_ready':False,'visibility':'private','public_release_approved':False}
        write_new(folder/'acquisition-complete.json',receipt)
        print(folder);print(json.dumps({'files':len(extracted),'download_bytes':sum(x['bytes'] for x in records)}))
    except Exception as e:
        write_new(folder/'acquisition-failed.json',{'status':'INCOMPLETE','error_type':type(e).__name__,'http_status':getattr(e,'code',None),'sources':records})
        raise

if __name__=='__main__':acquire()
