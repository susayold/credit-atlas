from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page();errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8770/?view=retail&workspace_tab=lendingclub&view_id=suite-view-74e07524f6d0')
    page.wait_for_timeout(5000)
    print('errors',errors);print(page.locator('body').inner_text()[-4200:]);b.close()
