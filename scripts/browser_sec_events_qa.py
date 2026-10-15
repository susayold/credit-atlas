import json,uuid,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('sec-events-qa-'+uuid.uuid4().hex[:12]);out.mkdir();base='http://127.0.0.1:8770';vid='sec-view-913c93906c18';checks=[];errors=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
def api(q):
 from urllib.parse import urlencode
 with urllib.request.urlopen(base+'/api/sec-events?'+urlencode({'view_id':vid,**q})) as r:
  assert 'no-store' in r.headers['Cache-Control'];return json.load(r)
source=root/'data/private/sec/sec-source-2dd5a9f2962a';receipt=json.loads((source/'acquisition-complete.json').read_text());counts={}
for cik in ['0000320193','0000789019','0000037996','0001467858']:
 q={'cik':cik,'asof':'2026-10-11','from':'2020-01-01','limit':'25'};r=api(q);raw={}
 for f in receipt['files']:
  if f['cik']!=cik or f['kind'] not in {'submissions','history'}:continue
  p=json.loads((source/f['file']).read_text());c=p['filings']['recent'] if f['kind']=='submissions' else p
  for i,acc in enumerate(c['accessionNumber']):raw[acc]=(c,i)
 expected={acc for acc,(c,i) in raw.items() if c['form'][i] in ['8-K','8-K/A','10-K','10-K/A','10-Q','10-Q/A'] and '2020-01-01'<=c['filingDate'][i]<='2026-10-11'}
 assert r['summary']['matched_unique_filings']==len(expected)
 for x in r['rows']:
  c,i=raw[x['accession']];assert x['items_raw']==c.get('items',[None]*len(c['form']))[i] and x['filing_date']==c['filingDate'][i] and x['primary_document']==c['primaryDocument'][i]
 p=api({**q,'offset':'25'});assert r['summary']==p['summary'] and not {x['accession'] for x in r['rows']} & {x['accession'] for x in p['rows']}
 counts[cik]=len(expected);checks.append(cik+': independent raw filing count/metadata, stable summary and disjoint pages')
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1400,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
 url=base+'/?view=sec&workspace_tab=events&sec_view_id='+vid+'&sec_cik=0000037996&sec_asof=2026-10-11&sec_event_from=2020-01-01'
 page.goto(url);expect(page.locator('#sec-events tbody tr')).to_have_count(25,timeout=180000)
 page.get_by_role('button',name='Trang sau',exact=True).click();expect(page.locator('#sec-events')).to_contain_text('Trang 2',timeout=180000)
 page.get_by_label('Filing item code',exact=True).select_option('2.03');expect(page.locator('#sec-events')).to_contain_text('15 dòng',timeout=180000)
 with page.expect_download() as dl:page.get_by_role('link',name='Xuất filing JSON',exact=True).click()
 dl.value.save_as(out/'filtered.json');export=json.loads((out/'filtered.json').read_text());assert export['filters']['item']=='2.03' and len(export['rows'])==15 and export['source_id']=='sec-source-2dd5a9f2962a';assert not any(export['qualification'].values());checks.append('UI pagination/item filter and source-bound private JSON export')
 page.locator('#sec-events').screenshot(path=str(out/'events-desktop.png'));page.reload();expect(page.get_by_label('Filing item code',exact=True)).to_have_value('2.03',timeout=180000);expect(page.locator('#sec-events tbody tr')).to_have_count(15,timeout=180000)
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#sec-events').screenshot(path=str(out/'events-mobile.png'));checks.append('URL reload filters and mobile no page overflow')
 page.route('**/api/sec-events?**',lambda r:r.fulfill(status=503,content_type='application/json',body='{"error":"Controlled outage"}'));page.get_by_label('Filing item code',exact=True).select_option('1.01');expect(page.locator('#sec-events')).to_contain_text('Controlled outage');assert page.get_by_role('link',name='Xuất filing JSON',exact=True).count()==0;page.unroute('**/api/sec-events?**');page.get_by_label('Filing item code',exact=True).select_option('2.03');expect(page.locator('#sec-events tbody tr')).to_have_count(15,timeout=180000);checks.append('Outage clears stale results/export; filter change recovers');b.close()
assert errors==[] and before==sha256(ledger);checks.append('No browser errors; frozen holdout ledger unchanged');r={'status':'PASS','counts':counts,'checks':checks};(out/'receipt.json').write_text(json.dumps(r,indent=2));print(out);print(json.dumps(r))
