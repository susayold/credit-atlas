"""Add publisher acquisition/profile evidence without promoting target readiness."""
import collections,json
from pathlib import Path
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit='artifacts/private/lendingclub-audit-4c9405321ec9/receipt.json';a=json.loads((root/audit).read_text(encoding='utf8'))
assert a['status']=='PASS' and a['rows']==1055054 and a['missingness_columns_checked']==90 and a['numeric_checks']==88 and a['ledger_unchanged']
profile='artifacts/private/lendingclub-profile-28db23b7bd0a/profile.json';p=json.loads((root/profile).read_text(encoding='utf8'))
assert not p['model_training_performed'] and not any(p['field_readiness'].values())
entry={'checkpoint':'lendingclub-published-source-20261012','document':'docs/LENDINGCLUB_SOURCE_PROFILE_VI.md',
    'audit':audit,'profile':profile,'source':'data/private/retail/lendingclub-source-2a2766348144/acquisition-complete.json',
    'scope':'Public API/publisher hash396562202bytes;1055054rows/90columns/94954860positions,90missingness/11numeric profiles,105monthly status cells,terminal label encoding and joint/individual coverage',
    'remaining':'API/UI,dictionary/preprocessing provenance,application availability,full booked/reject population,event horizon/maturity and intended-use/OOT qualification'}
for identifier in ['P1.02','P1.05']:
    row=next(r for r in doc['requirements'] if r['id']==identifier);entries=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(dict(entry))
    assert not row['full_completion_proven']
assert before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('LendingClub source evidence recorded;50capability states unchanged')
