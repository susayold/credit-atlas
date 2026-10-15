"""Independent file/ZIP/receipt parity for the complete current source-run explorer."""
import json
import zipfile
from pathlib import Path
from uuid import uuid4

from credit_atlas.workspace import contained, sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21'
out=ROOT/'artifacts/private'/('source-run-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
case=ROOT/'artifacts/private'/CASE
manifest=json.loads((case/'case-complete.json').read_text())
foundation=json.loads((case/'foundation-complete.json').read_text())
snapshot=json.loads((case/'snapshot.json').read_text())
asset=next(a for a in json.loads((ROOT/'workspace.local.json').read_text())['annual_assets'] if a['sha256']==manifest['raw_sha256'])
archive=contained(ROOT,asset['archive']);receipt_path=contained(ROOT,asset['receipt'])
raw=json.loads(receipt_path.read_text())
assert sha256(archive)==asset['sha256']==raw['sha256']==manifest['raw_sha256']==foundation['raw_sha256']
assert sha256(receipt_path)==foundation['source_use_receipt_sha256']
assert raw['release_confirmation']=='user_supplied; not authenticated by file hash registry'
files=[]
for item in manifest['verified_inputs']:
    assert sha256(contained(ROOT,item['path']))==item['sha256']
    files.append(item)
for name,digest in manifest['outputs_sha256'].items():
    assert sha256(case/name)==digest
    files.append({'path':str((case/name).relative_to(ROOT)),'sha256':digest})
source_dir=contained(ROOT,foundation['source_run'])
source=json.loads((source_dir/'run-complete.json').read_text())
assert sha256(source_dir/'run-complete.json')==foundation['source_manifest_sha256']
assert source['release']==raw['release']==snapshot['source_release']
assert source['source_sha256']==raw['sha256']
pipeline=contained(ROOT,foundation['pipeline_run'])/'run-complete.json'
assert sha256(pipeline)==foundation['pipeline_manifest_sha256']
pipe=json.loads(pipeline.read_text())
assert pipe['status']=='DEVELOPMENT_PIPELINE_COMPLETE'
assert len(pipe['stages'])==8 and all(s['status']=='PASS' for s in pipe['stages'])
assert manifest['pipeline_run']==snapshot['pipeline_run']==pipeline.parent.name
members=[]
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist())=={'sample_orig_2012.txt','sample_perf_2012.txt'}
    for info in z.infolist():
        count=0
        with z.open(info) as f:
            for line in f:
                assert line.strip(), 'Unexpected blank raw record'
                count+=1
        expected=50000 if info.filename.startswith('sample_orig') else 4510559
        assert count==expected
        members.append({'name':info.filename,'bytes':info.file_size,'rows':count,'crc_verified_by_full_read':True})
assert snapshot['source_years']==manifest['source_years']==[2012]
assert snapshot['snapshot']['loans']==members[0]['rows']==50000
assert snapshot['snapshot']['monthly_rows']==members[1]['rows']==4510559
split_path=contained(ROOT,next(i['path'] for i in manifest['verified_inputs'] if i['path'].endswith('splits-d6baaaa686cb\\audit.json')))
split=json.loads(split_path.read_text());ready=snapshot['model_readiness']
for field in ['support','missing_years','blocking_reasons']:assert ready[field]==split[field]
assert ready['exclusions']==split['excluded']
assert split['training_ready'] is False and ready['actual_model_fit'] is False and ready['status']=='not_qualified'
assert manifest['actual_model_fit'] is False
assert ready['target']['source_claim']=='retrospective_latest_release_not_strict_historical_PIT'
assert sha256(ledger)==before
result={'status':'PASS','requirement':'P2.01','case_id':CASE,'case_receipt_sha256':sha256(case/'case-complete.json'),'raw_sha256':sha256(archive),'source_receipt_sha256':sha256(receipt_path),'source_inputs':files,'zip_members':members,'pipeline_stages':8,'data_readiness_receipt_parity':True,'publisher_publication_at':None,'publisher_release_authenticated':False,'source_years':[2012],'ledger_unchanged':True,'methods':{'scripts/audit_source_run_acceptance.py':sha256(Path(__file__)),'src/credit_atlas/mortgage_provenance.py':sha256(ROOT/'src/credit_atlas/mortgage_provenance.py')}}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','verified_file_entries':len(files),'zip_rows':sum(m['rows'] for m in members)}))
