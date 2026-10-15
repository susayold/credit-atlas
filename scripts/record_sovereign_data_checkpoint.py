"""Record bounded source/API evidence without promoting completion states."""
import collections,json
from pathlib import Path
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json'
doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit=json.loads((root/'artifacts/private/sovereign-default-audit-e696243f6f06/receipt.json').read_text(encoding='utf8'))
assert audit['status']=='PASS' and audit['values_checked']==350032
row=next(r for r in doc['requirements'] if r['id']=='P4.09')
evidence={'checkpoint':'sovereign-source-api-20261011','document':'docs/SOVEREIGN_DEFAULT_DATA_VI.md',
          'audit':'artifacts/private/sovereign-default-audit-e696243f6f06/receipt.json',
          'tests':'artifacts/private/sovereign-country-http-tests-20261011.xml',
          'scope':'Two official editions, 21877 entity-year rows, 16 selected metrics, independent full value/source audit and bounded private API',
          'remaining':'Country UI/browser/review integration, source conflicts, historical availability and qualified macro stress linkage'}
entries=row.setdefault('partial_evidence',[])
if not any(e.get('checkpoint')==evidence['checkpoint'] for e in entries):entries.append(evidence)
browser='artifacts/private/sovereign-default-qa-260a5c59a3ce/receipt.json'
regression='artifacts/private/country-browser-qa-6d510975f388/receipt.json'
for receipt in [browser,regression]:assert json.loads((root/receipt).read_text(encoding='utf8'))['status']=='PASS'
ui_evidence={'checkpoint':'sovereign-ui-20261011','document':'docs/SOVEREIGN_DEFAULT_DATA_VI.md',
             'browser':browser,'country_regression':regression,
             'scope':'Country tabs, six filters/URL, source conflicts/provisional values, distinct yearly/revision deltas, timeline/components/search/paging, scoped export, mobile and outage/late response guards',
             'remaining':'Sovereign review capture, source conflicts, historical availability and qualified macro stress linkage'}
if not any(e.get('checkpoint')==ui_evidence['checkpoint'] for e in entries):entries.append(ui_evidence)
archive_audit='artifacts/private/sovereign-default-audit-d922ba86fe99/receipt.json'
archive_browser='artifacts/private/sovereign-archive-qa-31dd2cab89d8/receipt.json'
archive_regression='artifacts/private/sovereign-default-qa-665a94fd3732/receipt.json'
for receipt in [archive_audit,archive_browser,archive_regression]:assert json.loads((root/receipt).read_text(encoding='utf8'))['status']=='PASS'
assert json.loads((root/archive_audit).read_text())['values_checked']==680304
archive_evidence={'checkpoint':'sovereign-archive-20261011','document':'docs/SOVEREIGN_ARCHIVE_EDITIONS_VI.md',
                  'audit':archive_audit,'browser':archive_browser,'regression':archive_regression,
                  'tests':'artifacts/private/sovereign-archive-country-tests-20261011-fixed.xml',
                  'scope':'Four official editions,42519rows,680304positions,explicit2024TOTAL alias,2023IADB schema absence,raw source markers,68retained count conflicts and edition-specific UI/export',
                  'remaining':'Original publication-byte availability, source conflicts, macro stress linkage, PD/LGD qualification and sovereign review capture'}
for entry in entries:
    if entry.get('checkpoint')=='sovereign-archive-20231011-to-20261011':entry['checkpoint']=archive_evidence['checkpoint']
if not any(e.get('checkpoint')==archive_evidence['checkpoint'] for e in entries):entries.append(archive_evidence)
assert not row['full_completion_proven']
assert collections.Counter(r['checkpoint_status'] for r in doc['requirements'])==before
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('P4.09 partial evidence recorded; 50 capability states unchanged')
