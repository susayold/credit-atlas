"""Bounded third-party Parquet acquisition; official metadata is a distinct source."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from urllib.error import HTTPError
import json,re,time,uuid
from credit_atlas.workspace import sha256,timestamp,write_new

ROOT=Path(__file__).resolve().parents[1]
REPO='DenyTranDFW/World_Omni_Auto_Receivables_Trust_2025_A_2046523'
CIK='0002046523'

def acquire():
    if ROOT.drive.upper()!='D:':raise ValueError('D: workspace required')
    folder=ROOT/'data/private/structured'/('absee-mirror-'+uuid.uuid4().hex[:12]);folder.mkdir()
    records=[]
    def fetch(name,url,limit=32*1024**2):
        time.sleep(.4)
        partial=folder/(name+'.partial');target=folder/name
        with urlopen(Request(url,headers={'User-Agent':'CreditAtlas/1.0 local financial research'}),timeout=60) as r:
            host=urlsplit(r.url).hostname
            if r.status!=200 or urlsplit(r.url).scheme!='https' or not (host in ('data.sec.gov','huggingface.co') or host.endswith('.hf.co') or host.endswith('.huggingface.co')):
                raise ValueError('Unexpected download origin/status')
            size=0
            with partial.open('xb') as f:
                while True:
                    b=r.read(1024**2)
                    if not b:break
                    size+=len(b)
                    if size>limit:raise ValueError('Download exceeds bound')
                    f.write(b)
        if not size:raise ValueError('Empty source')
        if name.endswith('.parquet'):
            with partial.open('rb') as f:
                if f.read(4)!=b'PAR1':raise ValueError('Invalid Parquet header')
                f.seek(-4,2)
                if f.read()!=b'PAR1':raise ValueError('Invalid Parquet footer')
        partial.rename(target)
        records.append({'file':name,'url':url,'bytes':size,'sha256':sha256(target),'retrieved_at':timestamp()})
        print(name,size,flush=True)
        return target
    try:
        sec=fetch('sec-submissions.json','https://data.sec.gov/submissions/CIK'+CIK+'.json',4*1024**2)
        metadata=json.loads(sec.read_text());assert str(metadata['cik']).zfill(10)==CIK
        assert metadata['name']=='World Omni Auto Receivables Trust 2025-A'
        recent=metadata['filings']['recent'];filings={}
        for i,form in enumerate(recent['form']):
            if form=='ABS-EE':
                row={key:recent[key][i] for key in ('accessionNumber','form','reportDate','filingDate','primaryDocument')}
                filings[row['accessionNumber'].replace('-','')]=row
        api=fetch('mirror-api.json','https://huggingface.co/api/datasets/'+REPO,4*1024**2)
        repo=json.loads(api.read_text());commit=repo['sha']
        if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Invalid mirror revision')
        fetch('mirror-README.md','https://huggingface.co/datasets/'+REPO+'/resolve/'+commit+'/README.md',1024**2)
        selected=[]
        for entry in repo['siblings']:
            path=entry['rfilename']
            if not re.fullmatch(r'\d{18}/woart2025aex102[a-z]{3}\d{2}\.parquet',path):continue
            accession=path.split('/')[0]
            if accession not in filings:raise ValueError('Mirror accession absent from official ABS-EE metadata')
            row=filings[accession]
            if not re.fullmatch(r'20\d{2}-\d{2}-\d{2}',row['reportDate']):raise ValueError('Missing official report date')
            name=path.replace('/','__')
            fetch(name,'https://huggingface.co/datasets/'+REPO+'/resolve/'+commit+'/'+path)
            selected.append({**row,'file':name,'mirror_path':path,'source_value_fidelity_verified':False})
        if not selected or len(selected)>24:raise ValueError('Mirror scope invalid')
        receipt={'source_id':folder.name,'status':'THIRD_PARTY_PARQUET_ACQUIRED','completed_at':timestamp(),
            'repo':REPO,'mirror_commit':commit,'cik':CIK,'deal':metadata['name'],'official_absee_filings':len(filings),
            'selected_filings':selected,'sources':records,'script_sha256':sha256(Path(__file__)),
            'source_value_fidelity_verified':False,'raw_xml_acquired':False,'visibility':'private','public_release_approved':False,
            'limitations':['Official SEC submission metadata confirms accessions/dates/form only; it does not verify mirror values or XML completeness.',
                'SEC archive exhibit HTTP returned403 during discovery. No authenticated endpoint or access restriction bypass used.',
                'Mirror values and license must be separately reviewed; no model or public release qualification. Missing months remain gaps.']}
        write_new(folder/'acquisition-complete.json',receipt)
        print(folder,flush=True)
        return folder
    except Exception as e:
        write_new(folder/'acquisition-failed.json',{'status':'INCOMPLETE','error_type':type(e).__name__,'http_status':e.code if isinstance(e,HTTPError) else None,'sources':records})
        raise

if __name__=='__main__':acquire()
