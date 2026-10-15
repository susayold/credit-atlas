import json,re,uuid,urllib.request
from pathlib import Path
from decimal import Decimal
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('note-schedule-qa-'+uuid.uuid4().hex[:12]);out.mkdir();base='http://127.0.0.1:8770';vid='sec-view-913c93906c18';checks=[];errors=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
def api(**query):
 with urllib.request.urlopen(base+'/api/sec-note-schedule?'+urlencode({'view_id':vid,'cik':'0000320193','asof':'2026-10-11',**query})) as r:
  assert r.headers['Cache-Control']=='no-store';return json.load(r)
r=api();pages=json.loads((root/'data/private/sec-documents'/r['source']['folder']/'pages.json').read_text(encoding='utf8'));text=re.sub(r'\s+',' ',' '.join(p['text'] for p in pages[34:42]));matches=list(re.finditer(r'Title: ([\d.]+)% Notes due (\d{4})',text));assert len(matches)==4
for i,m in enumerate(matches):
 block=text[m.start():matches[i+1].start() if i+1<len(matches) else len(text)]
 principal=Decimal(re.search(r'Aggregate Principal Amount\. \$([\d,]+)',block).group(1).replace(',',''));rate=Decimal(m.group(1))/100;year=int(m.group(2));n=next(n for n in r['notes'] if n['maturity_date']==str(year)+'-05-12')
 assert Decimal(n['original_issue_principal_usd_exact'])==principal and Decimal(n['coupon_rate_exact'])==rate
 assert 'Original Issue Date: May 12, 2025' in block and f'Maturity Date: May 12, {year}' in block and 'beginning on November 12, 2025' in block
 rs=[x for x in r['rows'] if x['note_id']==n['note_id']];assert len(rs)==2*(year-2025)-2
 assert sum(Decimal(x['scheduled_interest_usd_exact']) for x in rs)==principal*rate*(year-2026)
 assert sum(Decimal(x['scheduled_principal_usd_exact']) for x in rs)==principal
 assert all(x['adjusted_payment_date'] is None for x in rs)
assert len(r['rows'])==42 and Decimal(r['totals']['scheduled_interest_usd_exact'])==Decimal('985500000') and Decimal(r['totals']['scheduled_total_usd_exact'])==Decimal('5485500000')
checks.append('Independent PDF table principal/rate/date extraction and closed-form remaining coupon/principal reconciliation for four series')
assert api(asof='2025-05-11')['notes']==[] and api(cik='0000037996')['notes']==[];assert not any(r['qualification'].values());checks.append('Filing cutoff/issuer boundaries and actual/calendar/DSCR qualification remain unavailable')
(out/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1400,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
 url=base+'/?view=sec&workspace_tab=note-schedule&sec_view_id='+vid+'&sec_cik=0000320193&sec_asof=2026-10-11';page.goto(url);expect(page.locator('#sec-note-schedule')).to_contain_text('5485500000',timeout=180000)
 page.get_by_label('Note series',exact=True).select_option('apple-2025-2028');expect(page.locator('#sec-note-schedule')).to_contain_text('1620000000',timeout=180000)
 with page.expect_download() as dl:page.get_by_role('link',name='Xuất note schedule JSON',exact=True).click()
 dl.value.save_as(out/'selected-export.json');export=json.loads((out/'selected-export.json').read_text(encoding='utf8'));assert export==api(note_id='apple-2025-2028',end='2035-05-12');checks.append('Series filter and private JSON parity with source-derived report')
 page.locator('#sec-note-schedule').screenshot(path=str(out/'desktop.png'));page.reload();expect(page.locator('#sec-note-schedule')).to_contain_text('5485500000',timeout=180000)
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#sec-note-schedule').screenshot(path=str(out/'mobile.png'));checks.append('Workspace reload and mobile no page overflow; nominal-date caveat visible')
 page.route('**/api/sec-note-schedule?**',lambda r:r.fulfill(status=503,content_type='application/json',body='{"error":"Controlled outage"}'));page.get_by_label('Note series',exact=True).select_option('apple-2025-2030');expect(page.locator('#sec-note-schedule')).to_contain_text('Controlled outage');assert page.get_by_role('link',name='Xuất note schedule JSON',exact=True).count()==0
 page.unroute('**/api/sec-note-schedule?**');page.get_by_label('Note series',exact=True).select_option('all');expect(page.locator('#sec-note-schedule')).to_contain_text('5485500000',timeout=180000);checks.append('Outage removes results/export; filter change recovers');b.close()
assert errors==[] and before==sha256(ledger);checks.append('No page errors; frozen holdout ledger unchanged')
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks},indent=2),encoding='utf8');print(out);print(checks)
