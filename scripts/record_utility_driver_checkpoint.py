"""Record exact DSCR analysis evidence, retaining every original scope gate."""
import argparse,collections,json,re
from pathlib import Path
from xml.etree import ElementTree as ET
parser=argparse.ArgumentParser();parser.add_argument('--browser',required=True);args=parser.parse_args()
if not re.fullmatch(r'utility-debt-qa-[0-9a-f]{12}',args.browser):raise ValueError('Invalid browser receipt ID')
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit='artifacts/private/utility-driver-audit-ee7e5ec9275b/receipt.json'
browser='artifacts/private/'+args.browser+'/receipt.json'
tests='artifacts/private/utility-driver-http-tests-20261011-final.xml'
a=json.loads((root/audit).read_text(encoding='utf8'));b=json.loads((root/browser).read_text(encoding='utf8'))
assert a['status']==b['status']=='PASS' and a['supported_bridges']==32 and a['missing_prior_scopes']==8
assert a['ledger_unchanged'] and b['ledger_unchanged']
suite=ET.parse(root/tests).getroot().find('testsuite')
assert suite.attrib['tests']=='46' and suite.attrib['errors']=='0' and suite.attrib['failures']=='0'
entry={'checkpoint':'utility-dscr-driver-20261011','document':'docs/UTILITY_DSCR_DRIVERS_VI.md',
    'audit':audit,'browser':browser,'tests':tests,
    'scope':'32exact adjacent-year DSCR accounting bridges,8unavailable priors,revenue/O&M/source-residual/debt-service effects,counterfactual/input evidence,privateAPI/export and five-year reported DSCR chart',
    'remaining':'Causal/economic drivers,qualified historical legal scope/headroom/compliance and actual corporate/mortgage debt-service inputs'}
for identifier in ['P3.03','P3.08']:
    row=next(r for r in doc['requirements'] if r['id']==identifier);entries=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(dict(entry))
    assert not row['full_completion_proven']
assert before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('DSCR driver evidence recorded;50 capability states unchanged')
