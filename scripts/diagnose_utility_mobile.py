from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True)
    pg=b.new_page(viewport={'width':390,'height':844})
    pg.goto('http://127.0.0.1:8770/?view=sec&workspace_tab=utility-debt&sec_view_id=sec-view-913c93906c18')
    pg.locator('#utility-debt-summary').wait_for(timeout=120000)
    pg.locator('#utility-debt-evidence summary').click()
    print(pg.evaluate('''[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,id:e.id,cls:String(e.className),right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width})).slice(-20)'''))
    pg.screenshot(path='artifacts/private/utility-debt-mobile-diagnostic.png')
    b.close()
