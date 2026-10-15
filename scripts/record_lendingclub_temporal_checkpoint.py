"""Record temporal source evidence while keeping horizon/cutoff gates open."""
import collections,json
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit='artifacts/private/lendingclub-temporal-audit-eb737547b85a/receipt.json';browser='artifacts/private/lendingclub-full-source-qa-2ac428dd27c2/receipt.json';tests='artifacts/private/lendingclub-temporal-http-tests-20261012.xml'
a=json.loads((root/audit).read_text(encoding='utf8'));b=json.loads((root/browser).read_text(encoding='utf8'))
assert a['status']==b['status']=='PASS' and a['cohort_groups_checked']==1024 and a['cohort_metrics_checked']==5120 and a['date_profiles_checked']==4
assert a['ledger_unchanged'] and b['ledger_unchanged'] and not b['browser_errors']
suite=ET.parse(root/tests).getroot().find('testsuite');assert suite.attrib['tests']=='34' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
entry={'checkpoint':'lendingclub-temporal-evidence-20261012','document':'docs/LENDINGCLUB_TEMPORAL_READINESS_VI.md','audit':audit,'browser':browser,'tests':tests,
    'scope':'Four source date roles/min/max,1024cohort/term groups5120metrics,payment-span/chronology counts,source-scoped privateAPI/UI/export and rejected-not-applicable handling',
    'remaining':'Certified observation cutoff,event/exits/censoring history,application-time features,borrower identity,mature support and intended-use/entity-safe OOT protocol;payment span not maturity proof'}
row=next(r for r in doc['requirements'] if r['id']=='P1.02');entries=row.setdefault('partial_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
assert not row['full_completion_proven'] and before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
doc['as_of']='2026-10-12';path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Temporal evidence recorded;50states unchanged')
