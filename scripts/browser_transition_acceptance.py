"""Current P2.05 matrix/detail/scoped-export browser acceptance on actual data."""
import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('transition-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);checks=[];errors=[]
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    response=page.request.get(BASE+'/api/period-transitions?run='+CASE,timeout=120000)
    assert response.ok;source=response.json()
    scopes=[('all','all','count'),('relief','2012','count'),('non_relief','2025','balance'),('unknown','2012','count'),('all','2020','balance'),('all','1990','count')]
    for index,(segment,year,basis) in enumerate(scopes):
        url=f'{BASE}/?run={CASE}&view=transitions&segment={segment}&basis={basis}&horizon=6&transition_year={year}&from=2020-01&to=2020-02'
        page.goto(url)
        expect(page.locator('#transition-year')).to_have_value(year)
        matrix=page.locator('section.card').filter(has=page.get_by_role('heading',name='Adjacent transition matrix',exact=True))
        expected=[r for r in (source['lifetime_rows'] if year=='all' else source['rows']) if r['segment']==segment and (year=='all' or r['reporting_year']==int(year))]
        if expected:
            row=max(expected,key=lambda r:r['pairs']);button=matrix.get_by_title(row['origin']+' → '+row['destination'],exact=True)
            expect(button).to_be_visible();button.click();detail=matrix.locator('.matrix-detail')
            expect(detail).to_contain_text('Pairs: '+format(row['pairs'],','))
            expect(detail).to_contain_text('Distinct loans: '+format(row['distinct_loans'],','))
            expect(detail).to_contain_text('Origin denominator: '+format(row['origin_pairs'],',')+' pairs')
            expect(detail).to_contain_text('Missing-balance pairs: '+format(row['missing_balance_pairs'],','))
            probability=row['count_probability'] if basis=='count' else row['balance_probability']
            text=page.evaluate('(v)=>v===null?"Unavailable":(v*100).toFixed(2)+"%"',probability)
            expect(button).to_have_text(text)
        else:
            expect(matrix).to_contain_text('Không có adjacent pairs cho segment/năm này.')
            assert matrix.locator('td.matrix-cell').count()==0
        export=page.locator('#export-report');expect(export).to_be_enabled()
        with page.expect_download() as d:export.click()
        file=out/f'scope-{index}.json';d.value.save_as(file);r=json.loads(file.read_text())
        projection=r['supplemental_evidence']['period_transitions']
        wanted=[r for r in source['rows'] if r['segment']==segment and (year=='all' or r['reporting_year']==int(year))]
        assert projection['rows']==wanted and projection['lifetime_rows']==[r for r in source['lifetime_rows'] if r['segment']==segment]
        assert projection['filter_context']=={'segment':segment,'transition_year':year}
        assert 'lifetime_rows retain' in projection['scope_note'] and r['filter_context']['basis']==basis
        checks.append({'segment':segment,'year':year,'basis':basis,'export_year_cells':len(wanted),'status':'PASS'})
        if index in {0,2,5}:matrix.screenshot(path=str(out/f'matrix-{index}.png'))
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'empty-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    # Selected year/segment/basis must survive reload, including absent years.
    page.reload();expect(page.locator('#transition-year')).to_have_value('1990')
    expect(page.locator('#content')).to_contain_text('Không có adjacent pairs cho segment/năm này.')
    assert page.request.get(BASE+'/api/period-transitions?run='+CASE,headers={'Origin':'https://evil.example'}).status==403
    assert page.request.get(BASE+'/api/report?run='+CASE+'&transition_year=2020-01').status==400
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P2.05','scopes':checks,'additional_checks':['mobile','absent-year reload','cross-origin rejection','invalid year rejected'],'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','scopes':len(checks)}))
