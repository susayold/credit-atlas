import json,uuid,urllib.request,re
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('note-rules-qa-'+uuid.uuid4().hex[:12]);out.mkdir();base='http://127.0.0.1:8770';vid='sec-view-913c93906c18';checks=[];errors=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
def api(**q):
 with urllib.request.urlopen(base+'/api/sec-note-rules?'+urlencode({'view_id':vid,'cik':'0000320193','asof':'2026-10-11',**q})) as r:
  assert r.headers['Cache-Control']=='no-store';return json.load(r)
r=api();s=r['source'];folder=root/'data/private/sec-documents'/s['folder'];feed=json.loads((folder/'issuer-feed.json').read_text(encoding='utf8'));item=next(x for x in feed['GetEdgarFilingListResult'] if x['FilingId']==s['issuer_filing_id']);assert item['StockSymbol']=='0000320193' and item['FilingDate']=='11/01/2024 00:00:00' and any(d['Url']==s['url'] and d['DocumentType']=='CONVPDF' for d in item['DocumentList']);assert sha256(folder/s['file'])==s['pdf_sha256']
pages=json.loads((folder/'pages.json').read_text(encoding='utf8'));assert len(r['rules'])==5
for x in r['rules']:assert x['page_text']==re.sub(r'\s+',' ',pages[x['pdf_page']-1]['text']) and all(a in x['page_text'] for a in x['anchors'])
assert {x['pdf_page'] for x in r['rules']}=={38,40,45,46,72} and not any(r['qualification'].values());checks.append('Issuer-feed PDF linkage/hash, five raw page/section evidence records and no inferred payment calendar')
assert api(asof='2024-10-31')['source'] is None and api(cik='0000037996')['rules']==[];checks.append('Publication cutoff and unsupported issuer keep source unavailable')
(out/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1400,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)));url=base+'/?view=sec&workspace_tab=note-rules&sec_view_id='+vid+'&sec_cik=0000320193&sec_asof=2026-10-11';page.goto(url);expect(page.locator('#sec-note-rules tbody tr')).to_have_count(5,timeout=180000)
 with page.expect_download() as dl:page.get_by_role('link',name='Xuất note rules JSON',exact=True).click()
 dl.value.save_as(out/'export.json');assert json.loads((out/'export.json').read_text(encoding='utf8'))==r;page.locator('#sec-note-rules').screenshot(path=str(out/'desktop.png'));checks.append('App rules and private JSON match verified acquired source report')
 page.reload();expect(page.locator('#sec-note-rules tbody tr')).to_have_count(5,timeout=180000);page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#sec-note-rules').screenshot(path=str(out/'mobile.png'));checks.append('Deep-link reload and mobile no page overflow')
 page.route('**/api/sec-note-rules?**',lambda r:r.fulfill(status=503,content_type='application/json',body='{"error":"Controlled outage"}'));page.reload();expect(page.locator('#sec-note-rules')).to_contain_text('Controlled outage',timeout=180000);assert page.get_by_role('link',name='Xuất note rules JSON',exact=True).count()==0;page.unroute('**/api/sec-note-rules?**');page.reload();expect(page.locator('#sec-note-rules tbody tr')).to_have_count(5,timeout=180000);checks.append('Outage clears stale source/export and reload recovers');b.close()
assert errors==[] and before==sha256(ledger);checks.append('No browser errors; frozen holdout ledger unchanged');(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks},indent=2),encoding='utf8');print(out);print(checks)
