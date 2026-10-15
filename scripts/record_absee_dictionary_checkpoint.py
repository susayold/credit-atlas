"""Record acquired definition evidence without closing source/model gates."""
import json
from pathlib import Path
root=Path.cwd()
source='data/private/structured/schedule-al-1b72bcb43754/acquisition-complete.json'
audit='artifacts/private/absee-dictionary-audit-ff545e6098b9/receipt.json'
browser='artifacts/private/absee-dictionary-qa-ef7efae33197/receipt.json'
regression='artifacts/private/absee-profile-qa-efd98c82ee7c/receipt.json'
read=lambda p:json.loads((root/p).read_text(encoding='utf-8-sig'))
assert read(source)['status']=='OFFICIAL_CFR_DEFINITIONS_ACQUIRED'
assert read(audit)['status']=='PASS' and read(audit)['fields_checked']==62
assert read(browser)['status']=='PASS' and len(read(browser)['checks'])==5
assert read(regression)['status']=='PASS'
p=root/'docs/COMPLETION_REQUIREMENTS_50.json';d=read('docs/COMPLETION_REQUIREMENTS_50.json')
for item in d['requirements']:
    if item['id'] not in {'P5.02','P5.03','P5.10'}:continue
    entries=item.setdefault('partial_delivery_evidence',[])
    if not any(x.get('definition_source')==source for x in entries):
        entries.append({'as_of':'2026-10-11','scope':'Official2025CFR definitions,62proposed mirror-field correspondences,source coverage and app/export; no XSD/XML-fidelity/model qualification',
                        'definition_source':source,'audit':audit,'browser':browser,'regression':regression,
                        'backend':'artifacts/private/absee-dictionary-tests-20261011.xml','full_completion_proven':False})
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
checkpoint='ABS-EE definition checkpoint: acquired official GovInfo2025CFR PDF/XML2files403351bytes. P5 field dictionary covers62observed mirror columns with proposed Item3correspondence,coverage and private export. Independent62PDF/XML definitions/coverage PASS,backend8PASS,browser5groups/coverage regression4groupsPASS. SEC specification ZIPHTTP403; XSD/original-filing XML/EX103/current-rule/labels/fidelity/model gates remain false. Counts unchanged. See ABS_EE_FIELD_DEFINITIONS_VI.md.'
p=root/'scripts/build_progress_audit.py';s=p.read_text(encoding='utf8')
marker="'## 6. Evidence kiểm tra trên đĩa','',"
if checkpoint not in s:
    assert marker in s;s=s.replace(marker,repr(checkpoint)+", '', "+marker);p.write_text(s,encoding='utf8')
for name in ['PLAN_KPI_ANALYTICS_NEXT_VI.md','FIVE_WORKSPACES_STATUS.md','ABS_EE_MIRROR_COVERAGE_VI.md']:
    p=root/'docs'/name;text=p.read_text(encoding='utf8')
    if checkpoint not in text:
        title,rest=text.split('\n',1);p.write_text(title+'\n\n'+checkpoint+'\n'+rest,encoding='utf8')
print('Definition source/app evidence recorded; capability completion flags unchanged')
