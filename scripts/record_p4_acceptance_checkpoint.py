import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
checkpoint=('P4 acceptance checkpoint 11/10/2026: fixed exact XLSX significant-digit validation '
    'and allowlisted Excel POST error messages. Backend62PASS; independent import66checks/bridge500checksPASS; '
    'browser5groupsPASS including source/bucket→draft, exports, invalid numeric rejection, valid EXAMPLE intake/mobile. '
    'Full scope/ownership/native Excel/governance qualification remains open. See P4_ACCEPTANCE_AUDIT_VI.md.')
paths={'backend':'artifacts/private/p4-intake-movement-tests-20261011.xml',
    'import_audit':'artifacts/private/exposure-audit-42ac59e74266/audit-complete.json',
    'movement_audit':'artifacts/private/exposure-movement-audit-5bc7404496f3/audit-complete.json',
    'browser':'artifacts/private/p4-acceptance-qa-435791cbf240/receipt.json'}
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf8'))
for row in data['requirements']:
    if row['id'] in ('P4.01','P4.02','P4.06'):
        entries=row.setdefault('partial_delivery_evidence',[])
        if not any(e.get('browser')==paths['browser'] for e in entries):
            entries.append({'as_of':'2026-10-11','scope':checkpoint,'acceptance_subscope':row['acceptance'],
                **paths,'full_completion_proven':False})
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=root/'scripts/build_progress_audit.py';s=path.read_text(encoding='utf8')
if 'p4-acceptance-qa-435791cbf240' not in s:
    s=s.replace('receipts=[',"receipts=[('p4-acceptance-qa-435791cbf240','P4 intake/precision/concentration/review draft/private exports/mobile'),",1)
if checkpoint not in s:s=s.replace("'## 6. Evidence kiểm tra trên đĩa'",repr(checkpoint)+", '', '## 6. Evidence kiểm tra trên đĩa'",1)
path.write_text(s,encoding='utf8')
for name in ('FIVE_WORKSPACES_STATUS.md','PLAN_KPI_ANALYTICS_NEXT_VI.md'):
    path=root/'docs'/name;s=path.read_text(encoding='utf8')
    if checkpoint not in s:
        first,rest=s.split('\n',1);path.write_text(first+'\n\n'+checkpoint+'\n\n'+rest,encoding='utf8')
print('P4 subscope evidence recorded; original requirements/full scope preserved')
