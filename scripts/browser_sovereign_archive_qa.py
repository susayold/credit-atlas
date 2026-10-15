"""Older source editions: schema drift, markers, country universes and export."""
import json,uuid
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('sovereign-archive-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';checks=[];errors=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/?view=country&workspace_tab=sovereign&sovereign_edition=2024&sovereign_year=2022&sovereign_to=2023')
    expect(page.locator('#sovereign-summary')).to_contain_text('530095.9300')
    expect(page.locator('#sovereign-summary')).to_contain_text('-24140.6193')
    expect(page.locator('#sovereign-summary')).to_contain_text('Edition 2024 so với 2023')
    expect(page.locator('#sovereign-source-checks')).to_contain_text('DEBT_TOTAL_2023')
    expect(page.locator('#sovereign-source-checks')).to_contain_text('uninterpreted nonnumeric markers')
    expect(page.locator('#sovereign-evidence')).to_contain_text('header DEBT_TOTAL_2023')
    with page.expect_download() as dl:page.locator('#export-report').click()
    dl.value.save_as(out/'edition2024-world2022.json')
    r=json.loads((out/'edition2024-world2022.json').read_text())
    with urlopen(base+'/api/sovereign-defaults?edition=2024&entity=WORLD&year=2022&metric=TOTAL&from=2010&to=2023') as response:assert r==json.load(response)
    assert len(r['sources'])==12 and r['archive_source_id']=='sovereign-archive-source-e0310b79a4da'
    assert not r['historical_publication_vintages_complete']
    checks.append('2024 source-specific TOTAL alias, 2022 revision and scoped12-source export/API parity')
    page.get_by_label('Sovereign entity',exact=True).select_option('AFG')
    page.get_by_label('Sovereign metric',exact=True).select_option('OTHER_OFFICIAL_CREDITORS')
    page.get_by_label('Sovereign year',exact=True).fill('1981')
    page.get_by_label('Sovereign from',exact=True).fill('1960')
    page.get_by_role('button',name='Phân tích sovereign default',exact=True).click()
    expect(page.locator('#sovereign-summary .metric-value').first).to_have_text('Unavailable')
    expect(page.locator('#sovereign-source-checks')).to_contain_text('Selected source marker: "****" · source_unavailable · L151')
    with page.expect_download() as dl:page.locator('#export-report').click()
    dl.value.save_as(out/'marker.json')
    marker=json.loads((out/'marker.json').read_text())
    assert marker['actual_exact'] is None and marker['selected_source_marker']['raw']=='****'
    checks.append('Source-star marker retained with raw text/status/cell; unavailable never becomes zero')
    page.get_by_label('Sovereign edition',exact=True).select_option('2023')
    page.get_by_label('Sovereign entity',exact=True).select_option('WORLD')
    page.get_by_label('Sovereign year',exact=True).fill('2022')
    page.get_by_label('Sovereign metric',exact=True).select_option('IADB')
    page.get_by_role('button',name='Phân tích sovereign default',exact=True).click()
    expect(page.locator('#sovereign-summary .metric-value').first).to_have_text('Unavailable')
    expect(page.locator('#context-note')).to_contain_text('157 country entities + World')
    expect(page.locator('#sovereign-source-checks')).to_contain_text('Selected metric absent')
    expect(page.locator('#sovereign-summary')).to_contain_text('29 August 2023')
    expect(page.locator('#sovereign-evidence')).to_contain_text('No column · header Absent')
    assert page.get_by_label('Sovereign to',exact=True).input_value()=='2022'
    with page.expect_download() as dl:page.locator('#export-report').click()
    dl.value.save_as(out/'absent-iadb.json')
    absent=json.loads((out/'absent-iadb.json').read_text())
    assert not absent['metric_column_present'] and absent['component_residual_exact'] is None
    assert all(row['value_exact'] is None for row in absent['peers'])
    page.reload();expect(page.get_by_label('Sovereign edition',exact=True)).to_have_value('2023')
    expect(page.locator('#sovereign-source-checks')).to_contain_text('Selected metric absent')
    checks.append('2023 schema absence/date/157countries/year bounds preserved in UI/export and URL reload')
    page.get_by_label('Sovereign edition',exact=True).select_option('2024')
    page.get_by_label('Sovereign entity',exact=True).select_option('CHN')
    page.get_by_label('Sovereign edition',exact=True).select_option('2023')
    expect(page.get_by_label('Sovereign entity',exact=True)).to_have_value('WORLD')
    assert page.get_by_label('Sovereign entity',exact=True).locator('option[value="CHN"]').count()==0
    page.get_by_label('Sovereign metric',exact=True).select_option('TOTAL')
    page.get_by_role('button',name='Phân tích sovereign default',exact=True).click()
    expect(page.locator('#sovereign-summary')).to_contain_text('554236.5493')
    page.get_by_label('Sovereign year',exact=True).fill('2021')
    page.get_by_role('button',name='Phân tích sovereign default',exact=True).click()
    expect(page.locator('#sovereign-source-checks')).to_contain_text('Source mismatch')
    expect(page.locator('#sovereign-source-checks')).to_contain_text('99 / 215')
    checks.append('Edition-specific entity options refreshed; legacy count conflict stays visible')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#sovereign-controls').screenshot(path=str(out/'mobile-controls.png'))
    page.set_viewport_size({'width':1450,'height':1000})
    page.locator('#sovereign-source-checks').screenshot(path=str(out/'desktop-source-checks.png'))
    checks.append('Archive source warnings/mobile controls render without page overflow')
    assert not errors,errors
    assert sha256(ledger)==before
    browser.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'browser_errors':errors,'ledger_unchanged':True},indent=2),encoding='utf8')
print(out);print('PASS',len(checks))
