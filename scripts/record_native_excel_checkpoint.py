"""Persist verified native Excel evidence without promoting full completion."""
import json
from pathlib import Path

root=Path.cwd()
folder='artifacts/private/native-excel-qa-6f5a5c654e50'
baseline=json.loads((root/folder/'receipt.json').read_text(encoding='utf-8-sig'))
cases=json.loads((root/folder/'perturbation-receipt.json').read_text(encoding='utf-8-sig'))
ui='artifacts/private/sec-workbook-qa-72ba3961cedf/receipt.json'
assert baseline['status']=='PASS' and baseline['cells_compared']==9264
assert baseline['formula_cells_compared']==746 and baseline['originals_unchanged']
assert cases['status']=='PASS' and len(cases['cases'])==18 and cases['failed_checks']==0
assert sum(len(c['reads']) for c in cases['cases'])==59
assert json.loads((root/ui).read_text())['status']=='PASS'
ledger=root/'docs/COMPLETION_REQUIREMENTS_50.json'
d=json.loads(ledger.read_text(encoding='utf8'))
for item in d['requirements']:
    if item['id'] not in {'P3.03','P3.08','P3.10','P4.01','P4.10'}:continue
    evidence=item.setdefault('partial_delivery_evidence',[])
    if not any(e.get('native_baseline')==folder+'/receipt.json' for e in evidence):
        evidence.append({'as_of':'2026-10-11','scope':'Six saved workbook native baselines and18representative memory-input cases; SEC blank-to-zero fixed; not full capability qualification',
                         'native_baseline':folder+'/receipt.json','native_cases':folder+'/perturbation-receipt.json',
                         'browser':ui,'backend':'artifacts/private/sec-native-fix-tests-20261011.xml','full_completion_proven':False})
ledger.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
generator=root/'scripts/build_progress_audit.py';s=generator.read_text(encoding='utf8')
replacements={
 'B4–B6 chưa kiểm tra chạy/recalculate trong Microsoft Excel native.':'B4–B6 đã kiểm tra native baseline sáu workbook và18ca input đại diện; SEC blank-to-zero đã sửa. Chưa full native/production qualification.',
 'Actuals browser-derived; native Excel chưa test':'Actuals browser-derived; native baseline/KPI representative cases PASS, full qualification còn mở',
 'Native Excel chưa test; qualification giữ nguyên':'Native baseline/SEC missing-zero-prior cases PASS sau sửa source guard; full qualification còn mở',
 'Principal buckets chưa full debt-service; native Excel chưa test':'Principal buckets chưa full debt-service; native baseline/zero-missing cases PASS',
 'licensing hay native Excel execution.':'licensing hay toàn bộ native Excel qualification.',
 'Authenticated reviewer, native Excel verification và end-to-end reproduction/handoff.':'Authenticated reviewer, mở rộng native Excel qualification và end-to-end reproduction/handoff.'}
for old,new in replacements.items():
    assert old in s or new in s,old
    s=s.replace(old,new)
marker="'## 6. Evidence kiểm tra trên đĩa','',"
checkpoint="Native Excel checkpoint: six workbooks9264cells/746formula cells baseline PASS;18representative input cases/59checks PASS. SEC missing-numerator blank-to-zero bug fixed in new exports; UI3groups/backend7PASS. Original source files and frozen holdout ledger unchanged. Native visual/full-feature qualification remains open. See NATIVE_EXCEL_VALIDATION_VI.md."
if checkpoint not in s:
    assert marker in s
    s=s.replace(marker,repr(checkpoint)+", '', "+marker)
generator.write_text(s,encoding='utf8')
for name in ['PLAN_KPI_ANALYTICS_NEXT_VI.md','FIVE_WORKSPACES_STATUS.md']:
    p=root/'docs'/name;text=p.read_text(encoding='utf8')
    text=text.replace('native Excel execution chưa kiểm tra','native Excel baseline/representative cases PASS; full qualification còn mở')
    text=text.replace('native Excel chưa kiểm tra','native Excel baseline/representative cases PASS; full qualification còn mở')
    text=text.replace('native Microsoft Excel recalculation chưa kiểm tra','native Microsoft Excel baseline/representative cases PASS; full qualification còn mở')
    if checkpoint not in text:
        first,rest=text.split('\n',1);text=first+'\n\n'+checkpoint+'\n'+rest
    p.write_text(text,encoding='utf8')
print('Native Excel evidence recorded; full completion flags unchanged')
