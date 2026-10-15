"""Record complete publisher-file census; preserve all qualification gates."""
import collections,json
from pathlib import Path
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit='artifacts/private/lendingclub-full-audit-13dc84314050/receipt.json';a=json.loads((root/audit).read_text(encoding='utf8'))
assert a['status']=='PASS' and not a['issues'] and a['ledger_unchanged']
assert [(c['rows'],c['missing_columns_checked'],c['month_category_cells_checked']) for c in a['checks']]==[(2260701,151,630),(27648741,9,200)]
profile='artifacts/private/lendingclub-full-profile-f4168e8d746c/profile.json';p=json.loads((root/profile).read_text(encoding='utf8'))
assert p['ledger_unchanged'] and not p['model_training_performed'] and not p['source_approval_rate_qualified'] and not p['fixed_horizon_target_qualified']
entry={'checkpoint':'lendingclub-full-publisher-source-20261012','document':'docs/LENDINGCLUB_FULL_SOURCE_VI.md','audit':audit,'profile':profile,
    'source':'data/private/retail/lendingclub-full-source-3954d375d972/acquisition-complete.json',
    'scope':'Public publisher version3,GZIPsize/CRC,2260701accepted/27648741rejected rows,160column missingness,830monthly category cells,active/late/terminal states and separate funded/application grains;publisher helper code captured not executed',
    'remaining':'API/UI,snapshot/feature availability,original issuer fidelity/rights,application decision dates,comparable eligible populations,event horizon/maturity,borrower grouping and intended-use/OOT qualification'}
for identifier in ['P1.02','P1.05']:
    row=next(r for r in doc['requirements'] if r['id']==identifier);entries=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(dict(entry))
    assert not row['full_completion_proven']
assert before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
doc['as_of']='2026-10-12';path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Full accepted/rejected source census recorded;50states unchanged')
