"""Actual UI/API persistence audit; QA records retained archived, no user records deleted."""
import json
import uuid
import urllib.request
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,sha256


def run():
    root=app_root();out=root/'artifacts/private'/('monitor-review-qa-'+uuid.uuid4().hex[:12]);out.mkdir();checks=[];errors=[];base='http://127.0.0.1:8770'
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);saved=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1500,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/?view=monitor');expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        for d,name in [('P1','Retail'),('P2','Mortgage'),('P3','Business'),('P4','Portfolio'),('P5','Structured')]:
            page.locator('.kpi-analysis-nav').get_by_role('button',name=d+' · '+name,exact=True).click();page.get_by_role('button',name='Tạo KPI review',exact=True).click();dialog=page.get_by_role('dialog',name='KPI analyst review')
            title='QA '+out.name+' '+d;dialog.get_by_label('Tiêu đề KPI review',exact=True).fill(title);dialog.get_by_label('Owner KPI review',exact=True).fill('QA automated analyst')
            dialog.get_by_label('Nhận định KPI',exact=True).fill('QA persistence check; research snapshot only.');dialog.get_by_label('Giả thuyết KPI',exact=True).fill('Test hypothesis, not business cause');dialog.get_by_label('Bước kiểm chứng KPI',exact=True).fill('Compare stored capture against UI snapshot')
            with page.expect_response(lambda r:r.url.endswith('/api/monitor-reviews') and r.request.method=='POST',timeout=180000) as response:dialog.get_by_role('button',name='Lưu KPI review',exact=True).click()
            res=response.value;assert res.status==201,res.text();record=res.json();saved.append(record['id']);expect(dialog).not_to_be_visible(timeout=180000)
            assert record['domain']==d and record['revision']==1 and record['capture']['snapshot']['domain']==d and record['capture']['source_capture']
            original=record['capture'];card=page.locator('.monitor-review-record[data-review-id="'+record['id']+'"]');expect(card).to_be_visible(timeout=180000)
            card.get_by_role('button',name='Sửa KPI review',exact=True).click();dialog.get_by_label('Nhận định KPI',exact=True).fill('QA archived after successful revision check');dialog.get_by_label('Trạng thái KPI review',exact=True).select_option('archived')
            with page.expect_response(lambda r:r.url.endswith('/api/monitor-reviews') and r.request.method=='POST',timeout=180000) as response:dialog.get_by_role('button',name='Lưu KPI review',exact=True).click()
            revised=response.value.json();assert revised['revision']==2 and revised['capture']==original;expect(dialog).not_to_be_visible(timeout=180000)
            report=json.load(urllib.request.urlopen(base+'/api/monitor-review?id='+record['id']));assert len(report['history'])==2 and report['history'][0]['status']=='draft' and report['review']['status']=='archived'
            (out/(d+'-review.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');checks.append(d+' real UI create/update, verified source captures, immutable KPI snapshot and revision history')
        page.reload();expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        page.locator('.monitor-analyst-reviews summary').click();card=page.locator('.monitor-review-record[data-review-id="'+saved[-1]+'"]');expect(card).to_be_visible(timeout=180000)
        with page.expect_download() as pending:card.get_by_role('link',name='Xuất KPI review JSON',exact=True).click()
        pending.value.save_as(out/'review-export.json');report=json.loads((out/'review-export.json').read_text());assert report['review']['id']==saved[-1] and len(report['history'])==2
        checks.append('Persisted review reload and private export preserve captured evidence/history')
        page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='Tạo KPI review',exact=True).click();dialog=page.get_by_role('dialog',name='KPI analyst review');assert dialog.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1');page.screenshot(path=str(out/'review-mobile.png'));dialog.get_by_role('button',name='Đóng KPI review',exact=True).click();browser.close()
    assert not errors,errors;assert before==sha256(ledger);checks.append('Mobile dialog, no browser exceptions and frozen holdout ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'archived_qa_ids':saved,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':'PASS','checks':len(checks),'receipt':str(out/'receipt.json')}))


if __name__=='__main__':run()
