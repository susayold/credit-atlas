import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.fannie_samples import report
root=Path(__file__).resolve().parents[1]
tests='artifacts/private/fannie-samples-http-tests-20261012-final.xml'
s=ET.parse(root/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==27 and int(s.attrib['errors'])==0 and int(s.attrib['failures'])==0
audit='artifacts/private/fannie-public-audit-b518c8fa1c6a/receipt.json'
a=json.loads((root/audit).read_text());assert a['status']=='PASS' and a['source_positions_checked']==96749 and a['field_missingness_checked']==173 and a['ledger_unchanged']
browser='artifacts/private/fannie-samples-qa-a19e7e45fbf4/receipt.json'
b=json.loads((root/browser).read_text());assert b['status']=='PASS' and len(b['checks'])==4 and b['ledger_unchanged'] and not b['page_errors']
r=report(root,{});assert r['summary']['added_freddie_annual_vintages']==0 and all(not g for g in r['gates'].values())
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before=[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
entry={'checkpoint':'fannie-public-samples-20261012','document':'docs/FANNIE_PUBLIC_SAMPLES_VI.md','tests':tests,'audit':audit,'browser':browser,'scope':'Official public SF8loans/757monthly rows108positions,MF4loans/241monthly rows62fields and17annual DSCR rows;7source files,historical/current schema caution,private API/UI/export and173field quality checks','remaining':'Full authorized dataset/schema/representative multi-vintage support,horizon maturity and entity-safe OOT protocol;sample provides no additional Freddie vintage or qualified PD12 model','full_completion_proven':False}
for requirement in data['requirements']:
    if requirement['id'] in {'P2.01','P2.02','P2.08'}:
        entries=requirement.setdefault('partial_evidence',[])
        if not any(x.get('checkpoint')==entry['checkpoint'] for x in entries):entries.append(dict(entry))
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checkpoint':entry['checkpoint'],'capability_states_unchanged':True,'full_completion_proven':False}))
