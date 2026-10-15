"""Acquire dated BoC-BoE sovereign default editions and their methodology."""
import json,time,uuid,zipfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from credit_atlas.workspace import sha256,timestamp,write_new

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 ('edition-2025.html','https://www.bankofcanada.ca/2025/10/staff-analytical-note-2025-24/'),
 ('edition-2026.html','https://www.bankofcanada.ca/2026/10/staff-analytical-paper-2026-48/'),
 ('BoC-BoE-Database-2025.xlsx','https://www.bankofcanada.ca/wp-content/uploads/2025/10/BoC-BoE-Database-2025.xlsx'),
 ('BoC-BoE-Database-2026.xlsx','https://www.bankofcanada.ca/wp-content/uploads/2026/10/BoC-BoE-Database-2026.xlsx'),
 ('sap2026-48.pdf','https://www.bankofcanada.ca/wp-content/uploads/2026/10/sap2026-48.pdf'),
 ('methodology-tr124.pdf','https://www.bankofcanada.ca/wp-content/uploads/2023/07/tr124.pdf')]

def acquire():
    if ROOT.drive.upper()!='D:':raise ValueError('D: workspace required')
    folder=ROOT/'data/private/country'/('sovereign-default-source-'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
    records=[]
    try:
        for name,url in SOURCES:
            time.sleep(.4)
            partial=folder/(name+'.partial')
            with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 local sovereign-credit research'}),timeout=60) as r:
                if r.status!=200 or urlsplit(r.url).scheme!='https' or urlsplit(r.url).hostname!='www.bankofcanada.ca':raise ValueError('Unexpected official source origin')
                size=0
                with partial.open('xb') as f:
                    while chunk:=r.read(1024**2):
                        size+=len(chunk)
                        if size>16*1024**2:raise ValueError('Download bound exceeded')
                        f.write(chunk)
            if not size:raise ValueError('Empty source')
            package=None
            if name.endswith('.xlsx'):
                with zipfile.ZipFile(partial) as z:
                    if 'xl/workbook.xml' not in z.namelist() or any('vbaProject' in n for n in z.namelist()):raise ValueError('Unexpected workbook content')
                    if z.testzip():raise ValueError('ZIP CRC failed')
                    package={'external_link_parts':len([n for n in z.namelist() if n.startswith('xl/externalLinks/') and n.endswith('.xml')]),
                             'external_links_followed':False,'source_formula_recalculation_performed':False}
            if name.endswith('.pdf') and not partial.read_bytes().startswith(b'%PDF-'):raise ValueError('Invalid PDF')
            path=folder/name;partial.rename(path)
            record={'file':name,'url':url,'bytes':size,'sha256':sha256(path),'retrieved_at':timestamp()}
            if package:record['package']=package
            records.append(record)
            print(name,size,flush=True)
        for edition in (2025,2026):
            if f'BoC-BoE-Database-{edition}.xlsx' not in (folder/f'edition-{edition}.html').read_text(encoding='utf8'):raise ValueError('Edition page/source link mismatch')
        write_new(folder/'acquisition-complete.json',{'source_id':folder.name,'status':'OFFICIAL_SOVEREIGN_DEFAULT_EDITIONS_ACQUIRED',
            'sources':records,'completed_at':timestamp(),'script_sha256':sha256(Path(__file__)),
            'edition_years':[2025,2026],'historical_publication_vintages_complete':False,
            'historical_pd_lgd_calibrated':False,'macro_stress_linkage_qualified':False,
            'visibility':'private','public_release_approved':False})
        print(folder,flush=True)
    except Exception as e:
        write_new(folder/'acquisition-failed.json',{'status':'INCOMPLETE','sources':records,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)})
        raise

if __name__=='__main__':acquire()
