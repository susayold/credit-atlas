import json,re
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('portfolio-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);checks=[];errors=[];profile_checks=0;chart_points=0
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    source=page.request.get(BASE+'/api/snapshot?run='+CASE,timeout=120000).json();profile=source['snapshot']['portfolio_profile']
    scopes=[('all','count','2012-01','2012-03'),('all','balance','2026-01','2026-03'),('relief','count','2012-01','2012-03'),('non_relief','balance','',''),('unknown','count','',''),('all','count','1990-01','1990-12')]
    for index,(segment,basis,start,end) in enumerate(scopes):
        page.goto(f'{BASE}/?run={CASE}&view=portfolio&segment={segment}&basis={basis}&horizon=12&transition_year=all&from={start}&to={end}')
        expect(page.locator('#month-from')).to_have_value(start)
        monthly=source['snapshot']['monthly'] if segment=='all' else source['monthly_by_segment'].get(segment,[])
        monthly=[r for r in monthly if (not start or r['period'][:7]>=start) and (not end or r['period'][:7]<=end)]
        def display(value,kind):
            return page.evaluate('(p)=>p.v===null?"Unavailable":p.kind==="money"?new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}).format(p.v):p.kind==="percent"?(p.v*100).toFixed(2)+"%":new Intl.NumberFormat("en-US").format(p.v)',{'v':value,'kind':kind})
        metrics=page.locator('#content .metric-value')
        last=monthly[-1] if monthly else None
        for i,(field,kind) in enumerate([('active_loans','number'),('observed_active_upb','money'),('d3_count_share' if basis=='count' else 'd3_balance_share','percent'),('unknown_active_loans','number')]):
            expect(metrics.nth(i)).to_have_text(display(last[field] if last else None,kind))
        for label,field,percentage in [('Observed active monthly stock','active_loans' if basis=='count' else 'observed_active_upb',False),('Observed D3 share','d3_count_share' if basis=='count' else 'd3_balance_share',True)]:
            chart=page.get_by_role('img',name=label,exact=True)
            values=[r[field] for r in monthly if r[field] is not None]
            if not values:assert chart.count()==0;continue
            expect(chart).to_be_visible();d=chart.locator('path').get_attribute('d')
            coordinates=[tuple(float(v) for v in text.strip().split(',')) for text in re.findall(r'[ML]([^ML]+)',d)]
            expected=[];maximum=max(max(values),.001 if percentage else 1)*1.13
            for i,r in enumerate(monthly):
                if r[field] is not None:expected.append((49+i/max(1,len(monthly)-1)*618,200-r[field]/maximum*185))
            assert len(coordinates)==len(expected)
            for got,wanted in zip(coordinates,expected):assert max(abs(a-b) for a,b in zip(got,wanted))<1e-8
            chart_points+=len(expected)
        anatomy=page.locator('section.card').filter(has=page.get_by_role('heading',name='Origination profile',exact=True))
        for dimension in profile['dimensions']:
            anatomy.locator('select').select_option(dimension)
            expected=[r for r in profile['rows'] if r['dimension']==dimension and (segment=='all' or r['segment']==segment)]
            assert anatomy.locator('tbody tr').count()==len(expected)
            for i,r in enumerate(expected):
                cells=anatomy.locator('tbody tr').nth(i).locator('td').all_text_contents()
                assert cells[1:]==[r['bucket'],display(r['loans'],'number'),display(r['opening_upb'],'money'),display(r['count_share'] if basis=='count' else r['balance_share'],'percent')]
                profile_checks+=1
        stock=page.locator('section.card').filter(has=page.get_by_role('heading',name='Monthly stock ledger',exact=True))
        expect(stock.locator('thead th').last).to_have_text('D3 count share' if basis=='count' else 'D3 UPB share')
        assert stock.locator('tbody tr').count()==len(monthly[-12:])
        for i,r in enumerate(monthly[-12:]):
            cells=stock.locator('tbody tr').nth(i).locator('td').all_text_contents()
            assert cells==[r['period'][:7],display(r['active_loans'],'number'),display(r['state_usable_active_loans'],'number'),display(r['d3_active_loans'],'number'),display(r['unknown_active_loans'],'number'),display(r['observed_active_upb'],'money'),display(r['d3_count_share'] if basis=='count' else r['d3_balance_share'],'percent')]
        with page.expect_download() as download:page.locator('#export-report').click()
        file=out/f'scope-{index}.json';download.value.save_as(file);report=json.loads(file.read_text())
        table=next(t for t in report['report']['tables'] if t['table_id']=='portfolio_monthly');assert table['rows']==monthly
        assert table['filters_applied']==['segment','reporting_month_range']
        checks.append({'segment':segment,'basis':basis,'from':start,'to':end,'monthly_rows':len(monthly),'status':'PASS'})
        if index==1:page.screenshot(path=str(out/'balance-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'empty-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.reload();expect(page.locator('#month-from')).to_have_value('1990-01');expect(metrics.first).to_have_text('Unavailable')
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P2.03','scopes':checks,'profile_bucket_checks':profile_checks,'chart_point_checks':chart_points,'mobile':True,'empty_range_reload':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','scopes':len(checks),'profile_bucket_checks':profile_checks,'chart_points':chart_points}))
