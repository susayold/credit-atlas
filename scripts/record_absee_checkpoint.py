"""Record acquired mirror scope without upgrading requirement completion."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
checkpoint=('ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files '
    'pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. '
    'Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. '
    'Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. '
    'Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. '
    'See ABS_EE_MIRROR_COVERAGE_VI.md.')
path=root/'docs/COMPLETION_REQUIREMENTS_50.json'
data=json.loads(path.read_text(encoding='utf8'))
evidence={'as_of':'2026-10-11','scope':checkpoint,
    'source':'data/private/structured/absee-mirror-f97dcd09916d/acquisition-complete.json',
    'profile':'artifacts/private/absee-profile-63397e5ebbc6/profile.json',
    'source_audit':'artifacts/private/absee-profile-audit-00668467a11d/receipt.json',
    'browser':'artifacts/private/absee-profile-qa-eee5f9a1c959/receipt.json','full_completion_proven':False}
for row in data['requirements']:
    if row['id'] in ('P5.02','P5.03','P5.10'):
        entries=row.setdefault('partial_delivery_evidence',[])
        if not any(e.get('source')==evidence['source'] for e in entries):entries.append(evidence)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=root/'scripts/build_progress_audit.py';text=path.read_text(encoding='utf8')
if 'absee-profile-qa-eee5f9a1c959' not in text:
    text=text.replace('receipts=[',"receipts=[('absee-profile-qa-eee5f9a1c959','Quarantined ABS-EE coverage UI/API/JSON/mobile/outage/ledger'),('absee-profile-audit-00668467a11d','Independent localParquet488219rows/651missingness/99money sums; not XML fidelity'),",1)
if checkpoint not in text:
    text=text.replace("'## 6. Evidence kiểm tra trên đĩa'",repr(checkpoint)+", '', '## 6. Evidence kiểm tra trên đĩa'",1)
path.write_text(text,encoding='utf8')
for name in ('FIVE_WORKSPACES_STATUS.md','PLAN_KPI_ANALYTICS_NEXT_VI.md','STRUCTURED_ABS_SOURCE_WORKFLOW.md'):
    path=root/'docs'/name;text=path.read_text(encoding='utf8')
    if checkpoint not in text:
        first,rest=text.split('\n',1);path.write_text(first+'\n\n'+checkpoint+'\n\n'+rest,encoding='utf8')
print('Recorded partial evidence; capability status counts unchanged')
