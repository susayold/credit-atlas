"""Capture legacy issuer resource and documented successor-domain provenance."""
import uuid,zipfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from credit_atlas.workspace import sha256,timestamp,write_new
root=Path(__file__).resolve().parents[1]
sources=[('LCDataDictionary.xlsx','https://resources.lendingclub.com/LCDataDictionary.xlsx')]
def run():
    if root.drive.upper()!='D:':raise ValueError('D: storage required')
    out=root/'data/private/retail'/('lendingclub-dictionary-source-'+uuid.uuid4().hex[:12]);out.mkdir();records=[]
    for name,url in sources:
        with urlopen(Request(url,headers={'User-Agent':'CreditAtlas private credit research'}),timeout=30) as r:
            host=urlsplit(r.url).hostname
            if r.status!=200 or urlsplit(r.url).scheme!='https' or host not in {'resources.lendingclub.com','resources.happen.com','www.happen.com'}:raise ValueError('Unexpected issuer/successor origin')
            data=r.read(8*1024**2+1)
            if not data or len(data)>8*1024**2:raise ValueError('Invalid resource size')
            final_url=r.url;headers={k:r.headers.get(k) for k in ['Last-Modified','ETag','Content-Type']}
        p=out/name;p.write_bytes(data)
        if name.endswith('.xlsx'):
            with zipfile.ZipFile(p) as z:
                if z.testzip() is not None or sum(i.file_size for i in z.infolist())>32*1024**2 or 'xl/workbook.xml' not in z.namelist():raise ValueError('Invalid workbook package')
        records.append({'file':name,'requested_url':url,'response_url':final_url,'bytes':len(data),'sha256':sha256(p),'retrieved_at':timestamp(),'response_headers':headers})
        print(name,len(data),flush=True)
    write_new(out/'acquisition-complete.json',{'status':'ISSUER_DICTIONARY_ACQUIRED','source_id':out.name,'sources':records,
        'completed_at':timestamp(),'script_sha256':sha256(Path(__file__)),'workbook_metadata_is_publication_vintage':False,
        'successor_identity_references':[
            {'url':'https://www.happen.com/company/media-center','scope':'Official web page read via research browser; historical LendingClub name and June2026 successor brand,not locally acquired bytes'},
            {'url':'https://www.sec.gov/Archives/edgar/data/1409970/000140997026000163/hapn-20260630.htm','scope':'SEC issuer filing read via research browser:corporate/bank name change June22,2026;not locally acquired bytes'}],
        'contributor_preprocessing_verified':False,'application_time_features_qualified':False,'visibility':'private','public_release_approved':False})
    print(out);print(sha256(out/'acquisition-complete.json'))
if __name__=='__main__':run()
