"""Real memo create/revise/export; retain QA records archived."""
import json
import uuid
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,sha256


def run(base_url='http://127.0.0.1:8770'):
    root=app_root();out=root/'artifacts/private'/('corporate-memo-qa-'+uuid.uuid4().hex[:12]);out.mkdir();checks=[];errors=[];ids=[]
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1050},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
        for cik,ticker in [('0000320193','AAPL'),('0001467858','GM')]:
            page.goto(base_url+'/?view=sec&sec_view_id=sec-view-b92d9914f1dc&sec_cik='+cik+'&sec_asof=2026-10-10&workspace_tab=memo&sec_interest_concept=InterestExpense&sec_debt_scope=debt_and_capital_lease')
            expect(page.get_by_role('button',name='Tạo corporate memo',exact=True)).to_be_visible(timeout=180000)
            page.get_by_role('button',name='Tạo corporate memo',exact=True).click();form=page.locator('.corporate-memo-form')
            form.get_by_label('Memo Title',exact=True).fill('QA '+out.name+' '+ticker);form.get_by_label('Memo Owner',exact=True).fill('QA automated analyst')
            form.get_by_label('Memo Business summary',exact=True).fill('QA financial evidence capture.');form.get_by_label('Memo Conclusion',exact=True).fill('QA test only; no business recommendation.');form.get_by_label('Memo Next validation action',exact=True).fill('Compare exact source snapshot and revisions')
            with page.expect_response(lambda r:r.url.endswith('/api/corporate-memos') and r.request.method=='POST',timeout=180000) as response:form.get_by_role('button',name='Lưu corporate memo',exact=True).click()
            assert response.value.status==201,response.value.text();record=response.value.json();ids.append(record['id']);capture=record['capture']
            assert capture['resolved_scope']['cik']==cik and capture['evidence']['selected_filing']['filters']['accession']==capture['resolved_scope']['accession']
            assert capture['evidence']['annual_trend']['filters']['asof']==capture['resolved_scope']['filing_date'] and not any(capture['qualification'].values())
            assert capture['evidence']['interest_coverage']['filters']['interest_concept']=='InterestExpense'
            assert capture['evidence']['interest_coverage']['filters']['asof']==capture['resolved_scope']['filing_date']
            assert capture['resolved_scope']['interest_concept']=='InterestExpense'
            assert capture['resolved_scope']['debt_scope']=='debt_and_capital_lease'
            assert capture['evidence']['debt_maturities']['filters']['accession']==capture['resolved_scope']['accession']
            assert capture['evidence']['debt_maturities']['filters']['asof']==capture['resolved_scope']['filing_date']
            assert capture['evidence']['debt_maturities']['filters']['debt_scope']=='debt_and_capital_lease'
            card=page.locator('.corporate-memo-record[data-memo-id="'+record['id']+'"]');expect(card).to_be_visible(timeout=180000)
            card.get_by_role('button',name='Sửa corporate memo',exact=True).click();form.get_by_label('Memo Conclusion',exact=True).fill('QA archived after verified revision check');form.get_by_label('Memo Status',exact=True).select_option('archived')
            with page.expect_response(lambda r:r.url.endswith('/api/corporate-memos') and r.request.method=='POST',timeout=180000) as response:form.get_by_role('button',name='Lưu corporate memo',exact=True).click()
            revised=response.value.json();assert revised['revision']==2 and revised['capture']==capture
            expect(form).not_to_be_visible(timeout=180000);expect(card).to_contain_text('revision 2',timeout=180000)
            card.get_by_text('Lịch sử & captured evidence',exact=True).click();expect(card.locator('table').first.locator('tbody tr')).to_have_count(2,timeout=180000)
            with page.expect_download() as pending:card.get_by_role('link',name='Xuất corporate memo JSON',exact=True).click()
            pending.value.save_as(out/(ticker+'.json'));report=json.loads((out/(ticker+'.json')).read_text(encoding='utf-8'));assert len(report['history'])==2 and report['memo']['capture']==capture
            checks.append(ticker+' real UI create/update, immutable server-derived capture, selected-filing anchored trend, revision history/private download')
        page.reload();expect(page.locator('.corporate-memo-record[data-memo-id="'+ids[-1]+'"]')).to_be_visible(timeout=180000)
        page.locator('#corporate-memos').screenshot(path=str(out/'memo-desktop.png'))
        page.set_viewport_size({'width':390,'height':844});card=page.locator('.corporate-memo-record[data-memo-id="'+ids[-1]+'"]');card.get_by_role('button',name='Sửa corporate memo',exact=True).click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(out/'memo-mobile.png'));page.get_by_role('button',name='Hủy memo',exact=True).click()
        checks.append('Persisted issuer-scoped reload and mobile memo form with no horizontal page overflow')
        browser.close()
    assert not errors,errors;assert sha256(ledger)==before
    checks.append('No browser exceptions and frozen holdout access ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'archived_qa_ids':ids,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    result={'status':'PASS','checks':len(checks),'receipt':str(out/'receipt.json')}
    print(json.dumps(result))
    return result


if __name__=='__main__':run()
