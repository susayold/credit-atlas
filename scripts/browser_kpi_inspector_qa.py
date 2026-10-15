import json,csv,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('kpi-inspector-qa-'+uuid.uuid4().hex[:12]);out.mkdir();checks=[];errors=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1500,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8770/?view=monitor');expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
 with page.expect_download() as dl:page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
 dl.value.save_as(out/'monitor.json');report=json.loads((out/'monitor.json').read_text());a=report['kpi_analysis'];assert sum(len(r['metrics']) for r in a.values())==88
 from credit_atlas.kpi_workbook import validate_report
 validate_report({k:report[k] for k in ['schema_version','read_at','filters','kpi_analysis']});checks.append('Export/review metric schema remains compatible with KPI workbook validator')
 for domain,title in [('P1','Retail'),('P2','Mortgage'),('P3','Business'),('P4','Portfolio'),('P5','Structured')]:
  page.locator('.kpi-analysis-nav').get_by_role('button',name=domain+' · '+title,exact=True).click();expect(page.locator('.kpi-analysis-body')).to_have_attribute('data-analysis-domain',domain)
  assert page.locator('#kpi-analysis-metrics tbody tr').count()==len(a[domain]['metrics'])
  search=page.get_by_label('Tìm KPI '+domain,exact=True);search.fill('NOT_A_METRIC');assert page.locator('.kpi-metric-catalog tbody tr').count()==0;search.fill('')
  page.get_by_label('Trạng thái KPI '+domain,exact=True).select_option('missing');assert page.locator('.kpi-metric-catalog tbody tr').count()==sum(m['value'] is None for m in a[domain]['metrics']);page.get_by_label('Trạng thái KPI '+domain,exact=True).select_option('all')
  choose=page.get_by_label('Bảng dữ liệu '+domain,exact=True);assert choose.locator('option').count()==len(a[domain]['tables']);choose.select_option(str(len(a[domain]['tables'])-1));t=a[domain]['tables'][-1]
  assert page.locator('.kpi-data-explorer tbody tr').count()==min(25,len(t['rows']))
  with page.expect_download() as dl:page.get_by_role('button',name='Tải bảng đang lọc CSV',exact=True).click()
  target=out/(domain+'.csv');dl.value.save_as(target)
  with target.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.reader(f))
  assert rows[0]==t['columns'] and len(rows)-1==len(t['rows'])
  ds=page.get_by_label('Tìm dữ liệu '+domain,exact=True);ds.fill('NOT_A_DATA_ROW');assert page.locator('.kpi-data-explorer tbody tr').count()==0;ds.fill('')
  checks.append(domain+': all KPI counts, missing/search, table selector, pagination bound and full CSV row parity')
 page.locator('.kpi-analysis-nav').get_by_role('button',name='P3 · Business',exact=True).click();page.get_by_label('KPI chi tiết P3',exact=True).select_option(label='AAPL · Current ratio')
 detail=page.locator('.kpi-metric-detail');m=next(m for m in a['P3']['metrics'] if m['name']=='AAPL · Current ratio');m={**m,**a['P3']['metric_details'][m['name']]};assert len(m['inputs'])==2 and float(m['inputs'][0]['value_exact'])/float(m['inputs'][1]['value_exact'])==m['value'];assert m['inputs'][0]['value_exact'] in detail.inner_text();assert m['source_result_exact'] in detail.inner_text()
 detail.screenshot(path=str(out/'issuer-inputs-desktop.png'));checks.append('SEC source-ratio inputs/exact result parity in selected dossier')
 page.locator('.kpi-analysis-nav').get_by_role('button',name='P2 · Mortgage',exact=True).click();page.get_by_label('KPI chi tiết P2',exact=True).select_option(label='D3 share — selected basis');m=next(m for m in a['P2']['metrics'] if m['name']=='D3 share — selected basis');m={**m,**a['P2']['metric_details'][m['name']]};assert float(m['inputs'][0]['value_exact'])/float(m['inputs'][1]['value_exact'])==m['value']
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1');page.locator('.kpi-metric-detail').screenshot(path=str(out/'mortgage-inputs-mobile.png'));checks.append('Mortgage numerator/denominator ratio parity; mobile no page overflow')
 assert errors==[];assert before==sha256(ledger);checks.append('No page errors; frozen holdout ledger unchanged');b.close()
receipt={'checks':checks,'status':'PASS','ledger_unchanged':True};(out/'qa.json').write_text(json.dumps(receipt,indent=2));print(out);print(json.dumps(receipt))
