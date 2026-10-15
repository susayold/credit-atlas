import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import expect,sync_playwright
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('source-run-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
manifest=json.loads((ROOT/f'artifacts/private/{CASE}/case-complete.json').read_text())
snapshot=json.loads((ROOT/f'artifacts/private/{CASE}/snapshot.json').read_text())
errors=[];checks=[];expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    runs=page.request.get(BASE+'/api/runs',timeout=120000).json()['runs']
    run=next(r for r in runs if r['case_id']==CASE)
    for key,expected in [('completed_at',manifest['completed_at']),('source_years',[2012]),('source_release',47),('loans',50000),('loan_months',4510559),('model_status','not_qualified')]:assert run[key]==expected
    evidence=page.request.get(BASE+'/api/evidence?run='+CASE).json()
    for key in ['pipeline_run','engine_commit','raw_sha256','target_version','completed_at']:assert evidence[key]==manifest[key]
    expected_artifacts=[{'artifact':Path(i['path']).parent.name+'/'+Path(i['path']).name,'sha256':i['sha256']} for i in manifest['verified_inputs']]
    assert evidence['artifacts']==expected_artifacts
    for segment in ['all','relief','non_relief','unknown']:
        page.goto(BASE+f'/?run={CASE}&view=sources&segment={segment}&from=2020-01&to=2020-03&basis=count&horizon=12')
        box=page.locator('#mortgage-provenance');expect(box).to_be_visible()
        assert page.locator('#run-select').input_value()==CASE
        expect(box).to_contain_text('2012-01 → 2026-03')
        expect(box).to_contain_text('not the whole mortgage market')
        expect(box).to_contain_text('Publisher publication date')
        expect(box).to_contain_text('Unavailable')
        with page.expect_download() as d:page.locator('#export-report').click()
        file=out/(segment+'-report.json');d.value.save_as(file);r=json.loads(file.read_text())
        assert r['case_id']==CASE and r['lineage']['pipeline_run']==manifest['pipeline_run']
        assert r['lineage']['case_receipt_sha256']==sha256(ROOT/f'artifacts/private/{CASE}/case-complete.json')
        assert r['lineage']['source_output_sha256']==manifest['outputs_sha256']
        assert r['report']['evidence_class']=='derived_observed_sample'
        assert r['report']['metric_registry']['active_loans']['limitation']=='Observed annual sample; not the Freddie Mac universe.'
        assert r['target']['source_claim']=='retrospective_latest_release_not_strict_historical_PIT'
        assert r['public_release_approved'] is False
        checks.append({'segment':segment,'source_scope_and_lineage_export':'PASS'})
    page.goto(BASE+f'/?run={CASE}&view=evidence')
    lineage=page.locator('section.card').filter(has=page.get_by_role('heading',name='Frozen run lineage',exact=True))
    expect(lineage).to_be_visible()
    for value in [CASE,manifest['pipeline_run'],manifest['engine_commit'][:12],manifest['target_version'],manifest['raw_sha256']]:expect(lineage).to_contain_text(value)
    hashes=page.locator('section.card').filter(has=page.get_by_role('heading',name='Verified input artifact digests',exact=True))
    expect(hashes).to_be_visible()
    expect(hashes.locator('tbody tr')).to_have_count(len(expected_artifacts))
    assert [row.locator('td').all_text_contents() for row in hashes.locator('tbody tr').all()]==[[r['artifact'],r['sha256']] for r in expected_artifacts]
    lineage.screenshot(path=str(out/'lineage.png'))
    page.goto(BASE+f'/?run={CASE}&view=models')
    expect(page.get_by_role('heading',name='Actual research model: chưa qualified',exact=True)).to_be_visible()
    support=page.locator('section.card').filter(has=page.get_by_role('heading',name='Temporal partition support',exact=True))
    expected=[[role,format(s['positive'],','),format(s['negative'],','),'Observed support only' if s['positive'] and s['negative'] else 'Missing support'] for role,s in snapshot['model_readiness']['support'].items()]
    assert [row.locator('td').all_text_contents() for row in support.locator('tbody tr').all()]==expected
    expect(page.locator('#content')).to_contain_text('Missing vintages: '+', '.join(map(str,snapshot['model_readiness']['missing_years'])))
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    support.screenshot(path=str(out/'readiness-mobile.png'))
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P2.01','scopes':checks,'run_catalog_parity':True,'evidence_artifacts_checked':len(expected_artifacts),'readiness_partition_checks':len(expected),'mobile':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','scopes':len(checks)}))
