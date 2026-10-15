import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import expect,sync_playwright
from credit_atlas.workspace import sha256

ROOT=Path.cwd();VIEW='suite-view-74e07524f6d0';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('retail-validation-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];checks=[];chart_points=0;expect.set_options(timeout=120000)
saved=json.loads((ROOT/f'artifacts/private/{VIEW}/snapshot.json').read_text());r=saved['retail']
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/?view=retail&workspace_tab=validation&view_id='+VIEW)
    box=page.locator('#retail-validation-reliability');expect(box).to_be_visible()
    assert box.locator('select').input_value()=='boosting/raw'
    development=page.locator('section.card').filter(has=page.get_by_role('heading',name='Development validation',exact=True))
    expected=[[v['model'],v['variant'],f"{v['roc_auc']:.4f}",f"{v['average_precision']:.4f}",f"{v['brier_score']:.6f}",f"{v['log_loss']:.6f}"] for v in r['validation']]
    assert [row.locator('td').all_text_contents() for row in development.locator('tbody tr').all()]==expected
    for variant in r['validation']:
        name=variant['model']+'/'+variant['variant'];box.locator('select').select_option(name)
        bins=variant['reliability_bins'];expected=[]
        for b in bins:
            display=lambda v:'Unavailable' if v is None else f'{v*100:.2f}%'
            expected.append([f"{b['lower']:.1f}–{b['upper']:.1f}",format(b['loans'],','),format(b['events'],','),display(b['mean_probability']),display(b['observed_rate'])])
        assert [row.locator('td').all_text_contents() for row in box.locator('tbody tr').all()]==expected
        chart=box.locator('svg');assert chart.get_attribute('aria-label').startswith('Saved validation calibration')
        usable=[b for b in bins if b['mean_probability'] is not None and b['observed_rate'] is not None]
        points=chart.locator('circle.calibration-point').all();assert len(points)==len(usable)
        for point,b in zip(points,usable):
            assert abs(float(point.get_attribute('cx'))-(42+b['mean_probability']*336))<1e-9
            assert abs(float(point.get_attribute('cy'))-(238-b['observed_rate']*196))<1e-9
            chart_points+=1
        checks.append({'variant':name,'bins':10,'known_chart_points':len(points),'status':'PASS'})
    uncertainty=page.locator('section.card').filter(has=page.get_by_role('heading',name='Paired validation uncertainty',exact=True))
    expected=[[p['reference']+' → '+p['candidate'],metric]+[f"{m[k]:.6f}" for k in ['point','lower','upper']] for p in r['paired_improvements'] for metric,m in p['metrics'].items()]
    assert [row.locator('td').all_text_contents() for row in uncertainty.locator('tbody tr').all()]==expected
    box.locator('select').select_option('boosting/raw');box.screenshot(path=str(out/'desktop.png'))
    with page.expect_download() as d:page.locator('#export-report').click()
    file=out/'suite-export.json';d.value.save_as(file);exported=json.loads(file.read_text());assert exported['retail']['validation']==r['validation'] and exported['retail']['paired_improvements']==r['paired_improvements']
    page.reload();expect(page.locator('#retail-validation-reliability')).to_be_visible()
    page.get_by_role('tab',name='Tổng quan',exact=True).click();chart=page.locator('#retail-calibration-chart svg');expect(chart).to_be_visible();assert chart.get_attribute('aria-label').startswith('Saved final-test calibration')
    assert chart.locator('circle.calibration-point').count()==sum(b['mean_probability'] is not None and b['observed_rate'] is not None for b in r['holdout']['reliability_bins'])
    page.get_by_role('tab',name='Validation',exact=True).click();expect(page.locator('#retail-validation-reliability')).to_be_visible()
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#retail-validation-reliability').screenshot(path=str(out/'mobile.png'))
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','variants':checks,'validation_metric_rows':6,'paired_metric_rows':20,'reliability_bin_rows':60,'chart_point_checks':chart_points,'export_parity':True,'final_chart_population_label_preserved':True,'reload_and_tab_navigation':True,'mobile':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','variants':6,'chart_points':chart_points}))
