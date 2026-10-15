"""Acquire source-linked older editions; never infer an original publication vintage."""
import json,time,uuid,zipfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from credit_atlas.workspace import sha256,timestamp,write_new

ROOT=Path(__file__).resolve().parents[1]
EDITIONS={
 2023:('https://www.bankofcanada.ca/2023/07/staff-analytical-note-2023-10/',
       'https://www.bankofcanada.ca/wp-content/uploads/2023/07/BoC-BoE-Database-2023-08-29.xlsx',
       'https://www.bankofcanada.ca/wp-content/uploads/2023/07/san2023-10.pdf'),
 2024:('https://www.bankofcanada.ca/2024/07/staff-analytical-note-2024-19/',
       'https://www.bankofcanada.ca/wp-content/uploads/2024/07/BoC-BoE-Database-2024.xlsx',
       'https://www.bankofcanada.ca/wp-content/uploads/2024/07/SAN2024-19.pdf')}

def run():
    if ROOT.drive.upper()!='D:':raise ValueError('D: workspace required')
    out=ROOT/'data/private/country'/('sovereign-archive-source-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
    records=[]
    try:
        for edition,urls in EDITIONS.items():
            for i,url in enumerate(urls):
                name=f'edition-{edition}.html' if i==0 else urlsplit(url).path.rsplit('/',1)[-1]
                partial=out/(name+'.partial');time.sleep(.4)
                with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 local sovereign archive research'}),timeout=45) as r:
                    if r.status!=200 or urlsplit(r.url).scheme!='https' or urlsplit(r.url).hostname!='www.bankofcanada.ca':raise ValueError('Unexpected origin')
                    headers={k:r.headers.get(k) for k in ['Last-Modified','ETag','Content-Type']}
                    size=0
                    with partial.open('xb') as f:
                        while chunk:=r.read(1024**2):
                            size+=len(chunk)
                            if size>16*1024**2:raise ValueError('Source size bound exceeded')
                            f.write(chunk)
                if not size:raise ValueError('Empty source')
                package=None
                if name.endswith('.xlsx'):
                    with zipfile.ZipFile(partial) as z:
                        if 'xl/workbook.xml' not in z.namelist() or any('vbaProject' in n for n in z.namelist()) or z.testzip():raise ValueError('Invalid workbook')
                        package={'external_link_parts':len([n for n in z.namelist() if n.startswith('xl/externalLinks/') and n.endswith('.xml')]),'external_links_followed':False,'source_recalculation_performed':False}
                if name.endswith('.pdf') and not partial.read_bytes().startswith(b'%PDF-'):raise ValueError('Invalid PDF')
                target=out/name;partial.rename(target)
                if i and url not in (out/f'edition-{edition}.html').read_text(encoding='utf8'):raise ValueError('File not linked by edition source page')
                record={'edition':edition,'file':name,'url':url,'bytes':size,'sha256':sha256(target),'retrieved_at':timestamp(),'response_headers':headers}
                if package:record['package']=package
                records.append(record);print(name,size,flush=True)
        write_new(out/'acquisition-complete.json',{'status':'OFFICIAL_ARCHIVE_EDITIONS_ACQUIRED','source_id':out.name,'sources':records,
            'script_sha256':sha256(Path(__file__)),'edition_years':sorted(EDITIONS),'completed_at':timestamp(),
            'original_publication_bytes_proven':False,'historical_publication_vintages_complete':False,'macro_stress_linkage_qualified':False,
            'visibility':'private','public_release_approved':False})
        print(out);print(sha256(out/'acquisition-complete.json'))
    except Exception as e:
        write_new(out/'acquisition-failed.json',{'status':'INCOMPLETE','sources':records,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)})
        raise

if __name__=='__main__':run()
