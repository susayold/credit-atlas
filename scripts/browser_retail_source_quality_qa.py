import json, uuid
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import sha256

root = Path.cwd()
out = root / 'artifacts/private' / ('retail-source-quality-qa-' + uuid.uuid4().hex[:12])
out.mkdir()
ledger = root / 'artifacts/private/retail-holdout-access.sqlite'
before = sha256(ledger)
checks = []; errors = []
endpoint = 'http://127.0.0.1:8770/api/retail-source-quality?view_id=suite-view-74e07524f6d0'
with urlopen(endpoint) as response:
    profile = json.load(response)
    assert response.headers['Cache-Control'] == 'no-store'
assert profile['feature_cells'] == 690000 and profile['missing_feature_cells'] == 0
checks.append('Verified acquisition aggregate API: 30000 clients, 23 predictors, 690000 cells')

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1500,'height':1000}, accept_downloads=True)
    page.on('pageerror', lambda e: errors.append(str(e)))
    url = 'http://127.0.0.1:8770/?view=monitor&monitor_analysis=P1'
    page.goto(url)
    download = page.get_by_role('button', name='Xuất monitor JSON', exact=True)
    expect(download).to_be_enabled(timeout=180000)
    with page.expect_download() as dl: download.click()
    dl.value.save_as(out / 'monitor.json')
    exported = json.loads((out / 'monitor.json').read_text())
    quality = exported['kpi_analysis']['P1']['data_quality']
    missing = next(m for m in quality['metrics'] if m['name']=='Raw feature missingness')
    assert missing['value'] == 0 and '690000' in missing['formula']
    assert exported['data']['P1']['source_quality'] == profile
    assert len(quality['tables'][0]['rows']) == 23
    assert sum(len(r['metrics']) for r in exported['kpi_analysis'].values()) == 88
    assert sum(len(r['data_quality']['metrics']) for r in exported['kpi_analysis'].values()) == 22
    expect(page.locator('.kpi-data-quality')).to_contain_text('690000')
    page.locator('.kpi-data-quality').screenshot(path=str(out / 'desktop.png'))
    checks.append('UI/JSON source parity, 23 field rows, 88 business KPI and 22 controls preserved')
    with page.expect_download(timeout=180000) as dl:
        page.get_by_role('button', name='Xuất KPI Excel', exact=True).click()
    dl.value.save_as(out / 'kpi.xlsx')
    import zipfile
    import xml.etree.ElementTree as ET
    ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(out / 'kpi.xlsx') as z:
        shared = ET.fromstring(z.read('xl/sharedStrings.xml')) if 'xl/sharedStrings.xml' in z.namelist() else None
        strings = [''.join(x.itertext()) for x in shared] if shared is not None else []
        rows = ET.fromstring(z.read('xl/worksheets/sheet2.xml')).findall('.//s:row',ns)
        def cell_value(c):
            v = c.find('s:v',ns)
            if c.get('t') == 's': return strings[int(v.text)]
            if c.get('t') == 'inlineStr': return ''.join(c.find('s:is',ns).itertext())
            return v.text if v is not None else None
        matches = [{c.get('r').rstrip('0123456789'):cell_value(c) for c in r} for r in rows]
        actual = [r for r in matches if r.get('C')=='Raw feature missingness']
        assert len(actual)==1 and actual[0]['E']=='0' and '690000' in actual[0]['L']
        assert actual[0]['N']==quality['scope']
    checks.append('Excel download succeeds with new source capture; zero missingness retained')
    page.reload(); expect(download).to_be_enabled(timeout=180000)
    expect(page.locator('.kpi-data-quality')).to_contain_text('690000')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.locator('.kpi-data-quality').screenshot(path=str(out / 'mobile.png'))
    checks.append('Reload and mobile layout preserve source-backed quality')
    page.route('**/api/retail-source-quality?*', lambda route: route.fulfill(status=503,content_type='application/json',body='{"error":"QA unavailable"}'))
    page.reload(); expect(download).to_be_enabled(timeout=180000)
    with page.expect_download() as dl: download.click()
    dl.value.save_as(out / 'outage.json')
    outage = json.loads((out / 'outage.json').read_text())
    assert next(m for m in outage['kpi_analysis']['P1']['data_quality']['metrics'] if m['name']=='Raw feature missingness')['value'] is None
    assert outage['data']['P1']['source_quality'] is None
    assert not any(r['kind']=='source_quality' for r in outage['kpi_analysis']['P1']['review_snapshot']['evidence_refs'])
    checks.append('Unavailable API retains null, preserves other domains, excludes unavailable source reference')
    assert not errors and before == sha256(ledger)
    checks.append('No browser errors; frozen holdout access ledger unchanged')
    browser.close()
receipt = {'status':'PASS','checks':checks,'source_profile_receipt_sha256':profile['profile_receipt_sha256'],'ledger_unchanged':True}
(out / 'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(out); print(json.dumps(receipt))
