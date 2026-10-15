import argparse,json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
parser=argparse.ArgumentParser();parser.add_argument('audit_receipt',type=Path);args=parser.parse_args()
AUDIT=args.audit_receipt
out=ROOT/'artifacts/private'/('cure-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
evidence=json.loads(AUDIT.read_text());assert evidence['status']=='PASS'
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);checks=[];errors=[]
names={'FIRST_OBSERVED_D3':'First observed D3','ONE_MONTH_CURE':'One-month cure','SUSTAINED_CURE_CONFIRMED':'Sustained cure confirmed','REDEFAULT_AFTER_SUSTAINED_CURE':'Redefault after sustained cure'}
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    source=page.request.get(BASE+'/api/episode-followup?run='+CASE,timeout=120000).json()
    for segment in ['all','relief','non_relief','unknown']:
        page.goto(f'{BASE}/?run={CASE}&view=transitions&segment={segment}&basis=count&horizon=24&transition_year=1990&from=2020-01&to=2020-02')
        card=page.locator('section.card').filter(has=page.get_by_role('heading',name='Episode follow-up support',exact=True))
        expect(card).to_be_visible();expect(page.locator('#content')).to_contain_text('Terminal CURRENT không trở thành cure.')
        episode=page.locator('section.card').filter(has=page.get_by_role('heading',name='Forward-only episode events',exact=True))
        counts={}
        for row in source['rows']:
            if row['segment']==segment and row['horizon_months']==6:
                label=names[row['event_type']];counts[label]=counts.get(label,0)+row['events']
        assert episode.locator('tbody tr').count()==len(counts)
        for row in episode.locator('tbody tr').all():
            cells=row.locator('td').all_text_contents();assert cells[1]==format(counts[cells[0]],',')
        for horizon in [6,12]:
            card.locator('select').select_option(str(horizon))
            selected=[r for r in source['rows'] if r['segment']==segment and r['horizon_months']==horizon]
            actual=card.locator('tbody tr').all_text_contents()
            expected=[[names[r['event_type']],r['followup_status'],format(r['events'],','),format(r['distinct_loans'],',')] for r in selected]
            assert len(actual)==len(expected)
            for i,row in enumerate(expected):assert card.locator('tbody tr').nth(i).locator('td').all_text_contents()==row
            checks.append({'segment':segment,'horizon':horizon,'groups':len(selected),'status':'PASS'})
        with page.expect_download() as d:page.locator('#export-report').click()
        file=out/(segment+'-report.json');d.value.save_as(file);r=json.loads(file.read_text())
        follow=r['supplemental_evidence']['episode_followup']
        assert follow['rows']==[r for r in source['rows'] if r['segment']==segment]
        assert follow['filters_applied']==['segment'] and follow['filter_context']=={'segment':segment,'horizons_months':[6,12]}
        if segment=='all':card.screenshot(path=str(out/'followup-desktop.png'))
    timeline_types=[]
    page.goto(BASE+f'/?run={CASE}&view=lifecycle&segment=all&basis=count&horizon=12&transition_year=all')
    left=page.locator('.loan-layout > .card').first;right=page.locator('.loan-layout > .card').last
    expect(left).to_be_visible();left.locator('select').select_option('all')
    for item in evidence['timeline_checks']:
        token=item['loan_key'];page.get_by_label('Private loan-key prefix',exact=True).fill(token)
        left.get_by_role('button',name='Tìm',exact=True).click();expect(right.locator('.card-heading')).to_contain_text(token)
        t=page.request.get(BASE+f'/api/timeline?run={CASE}&loan_key={token}').json()
        expect(right.locator('.timeline-event')).to_have_count(len(t['events']))
        for i,event in enumerate(t['events']):
            row=right.locator('.timeline-event').nth(i)
            expect(row.locator('time')).to_have_text(event['confirmation_month'][:7])
            expect(row.locator('strong')).to_have_text(names[event['event_type']])
        timeline_types.append(item['event_type'])
    right.screenshot(path=str(out/'timeline-desktop.png'))
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'timeline-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert page.request.get(BASE+'/api/timeline?run='+CASE+'&loan_key=not-a-token').status==400
    assert page.request.get(BASE+'/api/episode-followup?run='+CASE,headers={'Origin':'https://evil.example'}).status==403
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P2.06','followup_scopes':checks,'timeline_event_types':timeline_types,'export_segment_scopes':4,'mobile':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','followup_scopes':len(checks),'timeline_types':len(timeline_types)}))
