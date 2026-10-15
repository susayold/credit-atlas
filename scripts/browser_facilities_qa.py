import json,uuid,urllib.request
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('facilities-qa-'+uuid.uuid4().hex[:12]);out.mkdir();base='http://127.0.0.1:8770';vid='sec-view-913c93906c18';checks=[];errors=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
def api(cutoff,cik='0000037996'):
    with urllib.request.urlopen(base+'/api/sec-facilities?'+urlencode({'view_id':vid,'cik':cik,'asof':cutoff})) as r:
        assert r.headers['Cache-Control']=='no-store';return json.load(r)
old=api('2026-04-14');new=api('2026-04-15');late=api('2026-10-11')
assert old['summary']['disclosed_commitment_total_usd_exact']==new['summary']['disclosed_commitment_total_usd_exact']=='21000000000'
assert [r for r in old['rows'] if r['facility_id']=='delayed_draw'][0]['availability_end_date']=='2026-07-28'
assert [r for r in new['rows'] if r['facility_id']=='delayed_draw'][0]['availability_end_date']=='2026-12-31'
assert api('2025-04-16')['rows']==[] and api('2026-10-11','0000320193')['rows']==[]
assert late['covenant']['headroom_usd_exact'] is None and not any(late['qualification'].values())
(out/'report.json').write_text(json.dumps(late,ensure_ascii=False,indent=2),encoding='utf8');checks.append('API date-bound amendment selection, issuer scope, exact commitments and unavailable debt-service/headroom')
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1400,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
    url=base+'/?view=sec&workspace_tab=facilities&sec_view_id='+vid+'&sec_cik=0000037996&sec_asof=2026-10-11'
    page.goto(url);expect(page.locator('#sec-facilities tbody tr')).to_have_count(5,timeout=180000)
    expect(page.locator('#sec-facilities')).to_contain_text('2026-12-31');expect(page.locator('#sec-facilities')).to_contain_text('21000000000')
    with page.expect_download() as dl:page.get_by_role('link',name='Xuất facility JSON',exact=True).click()
    dl.value.save_as(out/'export.json');export=json.loads((out/'export.json').read_text(encoding='utf8'));assert export==late
    page.locator('#sec-facilities').screenshot(path=str(out/'desktop.png'));checks.append('App selected versions and private JSON match verified API report')
    page.reload();expect(page.locator('#sec-facilities tbody tr')).to_have_count(5,timeout=180000)
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#sec-facilities').screenshot(path=str(out/'mobile.png'));checks.append('Deep-link reload and mobile no page overflow')
    page.route('**/api/sec-facilities?**',lambda r:r.fulfill(status=503,content_type='application/json',body='{"error":"Controlled outage"}'));page.reload();expect(page.locator('#sec-facilities')).to_contain_text('Controlled outage',timeout=180000);assert page.get_by_role('link',name='Xuất facility JSON',exact=True).count()==0
    page.unroute('**/api/sec-facilities?**');page.reload();expect(page.locator('#sec-facilities tbody tr')).to_have_count(5,timeout=180000);checks.append('API outage clears results/export and reload recovers');b.close()
assert errors==[] and before==sha256(ledger);checks.append('No browser errors; frozen holdout ledger unchanged')
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks},indent=2),encoding='utf8');print(out);print(checks)
