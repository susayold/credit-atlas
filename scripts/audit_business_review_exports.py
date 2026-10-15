"""Full SEC statement exports and all SBA program/dimension/bucket exports."""
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from uuid import uuid4
import json
from credit_atlas.workspace import read_json,sha256,write_new

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'artifacts/private'/('business-review-export-audit-'+uuid4().hex[:12]);out.mkdir()
normalization=ROOT/'artifacts/private/sec-normalization-acceptance-e466059ee35f/receipt.json'
proof=read_json(normalization);assert proof['status']=='PASS'
assert all(sha256(ROOT/p)==h for p,h in proof['inputs_sha256'].items())
sec=ROOT/'artifacts/private/sec-case-33077fe45722';statements=read_json(sec/'annual-statements.json')
sba=ROOT/'artifacts/private/business-sba-21c568f10f7d';aggregates=read_json(sba/'aggregates.json');quality=read_json(sba/'quality.json')
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
graph={str(p.relative_to(ROOT)):sha256(p) for p in [normalization,sec/'annual-statements.json',sba/'business-complete.json',sba/'aggregates.json',sba/'quality.json']}
def api(endpoint,query):
    with urlopen('http://127.0.0.1:8770'+endpoint+'?'+urlencode(query),timeout=120) as response:
        assert response.headers['Cache-Control']=='no-store'
        assert 'attachment;' in response.headers['Content-Disposition']
        raw=response.read();return json.loads(raw),raw
checks=[];exports={}
for statement in statements:
    query={'view_id':'sec-view-b92d9914f1dc','cik':statement['cik'],'accession':statement['accession'],'asof':'2026-10-15'}
    result,raw=api('/api/sec-report',query)
    assert result['statement']==statement and result['case_id']==sec.name
    assert result['filters']=={k:v for k,v in query.items() if k!='view_id'}
    assert result['visibility']=='private' and result['public_release_approved'] is result['model_qualified'] is result['historical_availability_qualified'] is False
    assert 'program' not in result['filters']
    path=out/(statement['cik']+'-'+statement['accession']+'.json');path.write_bytes(raw);exports[path.name]=sha256(path)
    checks.append({'cik':statement['cik'],'accession':statement['accession'],'fields':len(statement['fields']),'ratios':len(statement['ratios'])})
sba_scopes=[];scope_number=0
for program in ['all','7A','504']:
    for dimension,population in aggregates['dimensions'].items():
        rows=[r for r in population if program=='all' or r['program']==program]
        for bucket in ['all',*sorted({r['bucket'] for r in rows if r['bucket']!='all'})]:
            query={'view_id':'suite-view-74e07524f6d0','program':program,'dimension':dimension,'bucket':bucket}
            expected=rows if bucket=='all' else [r for r in rows if r['bucket']==bucket]
            result,raw=api('/api/business-report',query)
            assert result['rows']==expected and result['quality']==quality
            assert result['quality_scope']=='whole_source_all_six_segments_not_filtered_by_aggregate_controls'
            assert result['contract']['amounts_are_current_exposure'] is False and result['fixed_horizon_default_target_qualified'] is False
            assert 'cik' not in result['filters'] and 'accession' not in result['filters']
            scope_number+=1;path=out/('sba-'+str(scope_number).zfill(3)+'.json');path.write_bytes(raw);exports[path.name]=sha256(path)
            sba_scopes.append({'program':program,'dimension':dimension,'bucket':bucket,'rows':len(expected),'records':sum(r['records'] for r in expected),'export':path.name})
assert sha256(ledger)==before and all(sha256(ROOT/p)==h for p,h in graph.items())
write_new(out/'receipt.json',{'status':'PASS','sec_scopes':checks,'sba_scopes':sba_scopes,
    'sec_statement_fields_checked':sum(c['fields'] for c in checks),'sec_ratios_checked':sum(c['ratios'] for c in checks),
    'sba_scope_count':scope_number,'private_exports_sha256':exports,'inputs_sha256':graph,
    'method_sha256':sha256(Path(__file__)),'runtime_methods_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'src/credit_atlas/server.py',ROOT/'src/credit_atlas/sec_views.py',ROOT/'src/credit_atlas/suite_snapshot.py']},
    'ledger_sha256_unchanged':before,'grain_note':'SEC issuer filing facts and SBA program/status source records stay in separate reports; no company-name join, lender PD, current EAD or authenticated owner claim.'})
print(out)
print('SEC exports',len(checks),'SBA exports',scope_number)
