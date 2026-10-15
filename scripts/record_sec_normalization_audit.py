"""Record full corpus numerical evidence;do not promote runtime acceptance."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from credit_atlas.workspace import read_json, sha256

root=Path.cwd();audit=root/'artifacts/private/sec-normalization-acceptance-e466059ee35f/receipt.json'
tests=root/'artifacts/private/sec-normalization-acceptance-tests.xml';receipt=read_json(audit)
assert receipt['status']=='PASS' and receipt['annual_field_states_checked']==536 and receipt['fact_entries']==105441
assert receipt['method_sha256']==sha256(root/'scripts/audit_sec_normalization_acceptance.py')
assert all(sha256(root/p)==digest for p,digest in receipt['inputs_sha256'].items())
suite=ET.parse(tests).getroot().find('testsuite');assert suite.attrib['tests']=='33' and suite.attrib['failures']==suite.attrib['errors']=='0'
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
before=[(r['id'],r['checkpoint_status'],r['full_completion_proven'],r['required_inputs'],r['required_outputs'],r['acceptance']) for r in data['requirements']]
r=next(r for r in data['requirements'] if r['id']=='P3.02')
entry={'checkpoint':'sec-normalization-whole-source-independent-audit-20261014',
       'document':'docs/P3_SEC_NORMALIZATION_AUDIT_VI.md','audit':str(audit.relative_to(root)),'tests':str(tests.relative_to(root)),
       'scope':'Independent raw JSON/Decimal full105441facts13374filings and occurrences,definitions/quality,67annual statements536fields;468supported48missing20ambiguous;batch512 exact parity,not sampling;33testsPASS;source/canonical/code unchanged',
       'remaining':'67statement actual API/browser/export acceptance;initial runtime503 not yet diagnosed;historical publication availability and corporate scoring qualification remain open',
       'full_completion_proven':False,'evidence_sha256':{str(f.relative_to(root)):sha256(f) for f in [audit,tests]}}
evidence=r.setdefault('partial_evidence',[])
if not any(e['checkpoint']==entry['checkpoint'] for e in evidence):evidence.append(entry)
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven'],r['required_inputs'],r['required_outputs'],r['acceptance']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Recorded independent audit;accepted count unchanged:',sum(r['full_completion_proven'] for r in data['requirements']))
