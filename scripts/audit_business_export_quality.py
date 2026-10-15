"""Source quality, complete report filters and supported empty SBA intersections."""
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlencode
from urllib.request import urlopen
from credit_atlas.workspace import read_json,sha256,write_new
import json

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'artifacts/private/business-review-export-audit-1d5eda8fb468';prior=read_json(folder/'receipt.json')
assert prior['status']=='PASS' and all(sha256(folder/p)==h for p,h in prior['private_exports_sha256'].items())
assert all(sha256(ROOT/p)==h for p,h in prior['inputs_sha256'].items())
quality=read_json(ROOT/'artifacts/private/sec-case-33077fe45722/quality.json')
sba=ROOT/'artifacts/private/business-sba-21c568f10f7d';aggregates=read_json(sba/'aggregates.json')
sba_quality=read_json(sba/'quality.json');sba_contract=read_json(sba/'contract.json')
checked_sec=checked_sba=0
for name in prior['private_exports_sha256']:
    report=read_json(folder/name)
    if name.startswith('sba-'):
        assert report['selected_record_count']==sum(r['records'] for r in report['rows'])
        assert report['quality']==sba_quality and report['contract']==sba_contract
        assert report['amount_scope']==aggregates['amount_scope'] and report['business_id']==sba.name
        assert report['public_release_approved'] is report['model_training_performed'] is False
        checked_sba+=1
    else:
        assert report['quality']==next(q for q in quality if q['cik']==report['filters']['cik'])
        assert report['status']=='FILING_SPECIFIC_RESEARCH_STATEMENT'
        assert report['source_id']=='sec-source-13cf03606e0c'
        assert all(o['cik']==report['filters']['cik'] and o['filing_date']<=report['filters']['asof'] for o in report['annual_options'])
        assert report['filters']['accession'] in {o['accession'] for o in report['annual_options']}
        checked_sec+=1
assert checked_sec==67 and checked_sba==371
out=ROOT/'artifacts/private'/('business-export-quality-audit-'+uuid4().hex[:12]);out.mkdir();empty=[]
covered={(q['program'],q['dimension'],q['bucket']) for q in prior['sba_scopes']}
for program in ['all','7A','504']:
    for dimension,population in aggregates['dimensions'].items():
        for bucket in sorted({r['bucket'] for r in population if r['bucket']!='all'}):
            if (program,dimension,bucket) in covered:continue
            expected=[r for r in population if r['bucket']==bucket and (program=='all' or r['program']==program)]
            assert expected==[]
            query={'view_id':'suite-view-74e07524f6d0','program':program,'dimension':dimension,'bucket':bucket}
            with urlopen('http://127.0.0.1:8770/api/business-report?'+urlencode(query),timeout=120) as response:
                assert response.headers['Cache-Control']=='no-store' and 'attachment;' in response.headers['Content-Disposition']
                raw=response.read();r=json.loads(raw)
            assert r['filters']=={k:v for k,v in query.items() if k!='view_id'}
            assert r['rows']==[] and r['selected_record_count']==0 and r['quality']==sba_quality
            assert not r['fixed_horizon_default_target_qualified'] and not r['contract']['amounts_are_current_exposure']
            path=out/('empty-'+str(len(empty)+1)+'.json');path.write_bytes(raw)
            empty.append({'query':query,'export':path.name,'sha256':sha256(path)})
write_new(out/'receipt.json',{'status':'PASS','sec_quality_scopes':checked_sec,'sba_quality_scopes':checked_sba,
    'supported_empty_intersections':empty,'total_sba_program_dimension_bucket_scopes':checked_sba+len(empty),
    'export_receipt_sha256':sha256(folder/'receipt.json'),'method_sha256':sha256(Path(__file__)),
    'inputs_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in [folder/'receipt.json',ROOT/'artifacts/private/sec-case-33077fe45722/quality.json',sba/'aggregates.json',sba/'quality.json',sba/'contract.json']}})
print(out);print('All SBA scopes',checked_sba+len(empty),'supported empty intersections',len(empty))
