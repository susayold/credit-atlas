import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('competing-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);checks=[];errors=[]
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    source=page.request.get(BASE+'/api/snapshot?run='+CASE,timeout=120000).json()
    rows=source['snapshot']['vintage_evidence']['rows']
    page.on('pageerror',lambda e:errors.append(str(e)))
    for segment in ['all','relief','non_relief','unknown']:
        for horizon in [6,12,24]:
            page.goto(f'{BASE}/?run={CASE}&view=vintage&segment={segment}&basis=count&horizon={horizon}&transition_year=all')
            expected=[r for r in rows if r['segment']==segment];selected=next((r for r in expected if r['observation_age']==horizon),None)
            if selected is None:
                expect(page.locator('#content')).to_contain_text('Segment không có verified cohort horizons.')
                assert page.get_by_role('img',name='Competing incidence at 6, 12 and 24 months',exact=True).count()==0
            else:
                expect(page.locator('#content')).to_contain_text('không phải monthly prediction curve')
                expect(page.get_by_role('img',name='Competing incidence at 6, 12 and 24 months',exact=True)).to_be_visible()
                values=page.locator('#content .metric-value')
                probability=page.evaluate('(v)=>v===null?"Unavailable":(v*100).toFixed(3)+"%"',selected['cif_d3'])
                expect(values.nth(0)).to_have_text(probability)
                expect(values.nth(1)).to_have_text(format(selected['observed_d3_count'],','))
                expect(values.nth(2)).to_have_text(format(selected['observed_prepayment_count'],','))
                support=page.locator('section.card').filter(has=page.get_by_role('heading',name='Risk set & uncertainty',exact=True))
                expect(support).to_contain_text(format(selected['eligible_loans'],','))
                expect(support).to_contain_text(format(selected['excluded_loans'],','))
                table=page.locator('section.card').filter(has=page.get_by_role('heading',name='Horizon evidence ledger',exact=True))
                assert table.locator('tbody tr').count()==3
                for i,row in enumerate(expected):
                    cells=table.locator('tbody tr').nth(i).locator('td').all_text_contents()
                    assert cells[:4]==[str(row['observation_age'])+'m',format(row['eligible_loans'],','),format(row['at_risk'],','),format(row['observed_d3_count'],',')]
            with page.expect_download() as d:page.locator('#export-report').click()
            file=out/(segment+'-'+str(horizon)+'.json');d.value.save_as(file);r=json.loads(file.read_text())
            exported=next(t for t in r['report']['tables'] if t['table_id']=='vintage_competing_risk')
            assert exported['rows']==[v for v in rows if v['segment']==segment and v['observation_age']==horizon]
            assert 'horizon' in exported['filters_applied']
            assert r['target']['horizon_months']==12 and r['target']['censored_means']=='unavailable_not_negative'
            checks.append({'segment':segment,'horizon':horizon,'supported':selected is not None,'status':'PASS'})
            if segment=='all' and horizon==12:page.screenshot(path=str(out/'all-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(out/'unavailable-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.reload();expect(page.locator('#content')).to_contain_text('Segment không có verified cohort horizons.')
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P2.07','scopes':checks,'mobile':True,'unavailable_reload':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','scopes':len(checks)}))
