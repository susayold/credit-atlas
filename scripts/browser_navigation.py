"""Drive the current grouped navigation and task tabs through visible UI."""
from playwright.sync_api import expect


def navigate_workspace(page, view):
    navigation = page.locator('#navigation')
    if not navigation.is_visible():
        page.get_by_role('button', name='Mở menu workspace').click()
    link = page.locator('[data-view="' + view + '"]')
    group = link.locator('xpath=ancestor::details[1]')
    if group.count() and group.get_attribute('open') is None:
        group.locator('summary').click()
    link.click()


def select_task(page, label):
    tab = page.get_by_role('tab', name=label, exact=True)
    tab.click()
    expect(tab).to_have_attribute('aria-selected', 'true')
