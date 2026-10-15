import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
audit=json.loads((ROOT/'artifacts/private/lifecycle-acceptance-4fcd4a1ac79a/receipt.json').read_text());assert audit['status']=='PASS'
out=ROOT/'artifacts/private'/('lifecycle-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];checks=[]
names={'FIRST_OBSERVED_D3':'First observed D3','ONE_MONTH_CURE':'One-month cure','SUSTAINED_CURE_CONFIRMED':'Sustained cure confirmed','REDEFAULT_AFTER_SUSTAINED_CURE':'Redefault after sustained cure'}
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+f'/?run={CASE}&view=lifecycle&segment=all&basis=count&horizon=12&transition_year=all')
    left=page.locator('.loan-layout > .card').first;right=page.locator('.loan-layout > .card').last
    expect(left).to_be_visible();left.locator('select').select_option('all')
    search=page.get_by_label('Private loan-key prefix',exact=True)
    for probe in audit['timeline_checks']:
        token=probe['loan_key'];search.fill(token);left.get_by_role('button',name='Tìm',exact=True).click()
        expect(right.locator('.card-heading')).to_contain_text(token)
        r=page.request.get(BASE+f'/api/timeline?run={CASE}&loan_key={token}').json()
        expect(right.get_by_role('img',name='Private loan observed current principal',exact=True)).to_be_visible()
        expect(right.locator('tbody tr')).to_have_count(len(r['months']))
        expect(right.locator('.timeline-event')).to_have_count(len(r['events']))
        for i,event in enumerate(r['events']):
            expect(right.locator('.timeline-event').nth(i)).to_contain_text(event['confirmation_month'][:7])
            expect(right.locator('.timeline-event').nth(i)).to_contain_text(names[event['event_type']])
        expect(right).to_contain_text('no model prediction or treatment effect')
        checks.append({'loan_key':token,'months':len(r['months']),'events':len(r['events']),'status':'PASS'})
    right.screenshot(path=str(out/'timeline.png'))
    # A failed/empty search must not leave a previous loan displayed as current.
    missing='0'*24
    assert page.request.get(BASE+f'/api/loans?run={CASE}&q={missing}').json()['total_matching']==0
    search.fill(missing);left.get_by_role('button',name='Tìm',exact=True).click()
    expect(left).to_contain_text('Không có loan phù hợp.')
    try:
        expect(right).to_contain_text('Không có loan phù hợp.')
    except Exception:
        page.screenshot(path=str(out/'stale-failure.png'),full_page=True)
        (out/'failed.json').write_text(json.dumps({'status':'FAIL','reason':'Empty search leaves previous timeline displayed','completed_timeline_checks':len(checks)},indent=2),encoding='utf-8')
        raise
    assert right.locator('tbody tr').count()==0
    # Deliver two real list responses out of order; the old response must stay discarded.
    first=audit['timeline_checks'][0]['loan_key']
    old_result=page.request.get(BASE+f'/api/loans?run={CASE}&segment=all&outcome=all&q={first}&limit=20').json()
    empty_result=page.request.get(BASE+f'/api/loans?run={CASE}&segment=all&outcome=all&q={missing}&limit=20').json()
    pending=[];page.route('**/api/loans?*',lambda route:pending.append(route))
    search.fill(first);left.get_by_role('button',name='Tìm',exact=True).click()
    assert right.locator('tbody tr').count()==0 and page.evaluate('state.loanKey')==''
    search.fill(missing);left.get_by_role('button',name='Tìm',exact=True).click()
    for _ in range(100):
        if len(pending)==2:break
        page.wait_for_timeout(50)
    assert len(pending)==2
    pending[1].fulfill(status=200,content_type='application/json',body=json.dumps(empty_result))
    expect(right).to_contain_text('Không có loan phù hợp.')
    pending[0].fulfill(status=200,content_type='application/json',body=json.dumps(old_result))
    page.wait_for_timeout(150)
    assert right.locator('tbody tr').count()==0 and page.evaluate('state.loanKey')==''
    page.unroute('**/api/loans?*')
    page.route('**/api/timeline?*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA timeline unavailable"}'))
    search.fill(first);left.get_by_role('button',name='Tìm',exact=True).click()
    expect(right).to_contain_text('QA timeline unavailable')
    assert right.locator('tbody tr').count()==0 and page.evaluate('state.loanKey')==''
    page.unroute('**/api/timeline?*')
    search.fill(first);left.get_by_role('button',name='Tìm',exact=True).click()
    expect(right.locator('.card-heading')).to_contain_text(first)
    bad=page.request.get(BASE+f'/api/loans?run={CASE}&q=ab').json()['error']
    search.fill('ab');left.get_by_role('button',name='Tìm',exact=True).click()
    expect(right).to_contain_text(bad)
    assert right.locator('tbody tr').count()==0 and page.evaluate('state.loanKey')==''
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'empty-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P2.04','timeline_checks':checks,'empty_search_clears':True,'pending_context_clears':True,'late_list_response_discarded':True,'timeline_outage_clears':True,'invalid_search_clears':True,'mobile':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','timeline_cases':len(checks)}))
