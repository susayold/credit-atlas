"""Verify the Toyota 2024-B validation card in the local ABS-EE app."""
import json
import uuid
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

from credit_atlas.workspace import contained

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8785"


def main():
    out = contained(ROOT, "artifacts/private/toyota-2024b-validation-ui-qa-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    errors = []
    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE + "/?view=abs&workspace_tab=absee-profile", wait_until="networkidle")
        card = page.locator("#absee-toyota-2024b-validation")
        expect(card).to_contain_text("1,518,106", timeout=180000)
        expect(card).to_contain_text("29 / 29")
        expect(card).to_contain_text("1 / 29 exact")
        checks.append("2024-B summary metrics and certificate results render")
        details = card.locator("details").first
        details.locator("summary").click()
        expect(details).to_contain_text("2024-04-30")
        expect(details).to_contain_text("2026-08-31")
        page.screenshot(path=str(out / "desktop.png"), full_page=True)
        checks.append("All monthly certificate deltas expand")
        page.set_viewport_size({"width": 390, "height": 844})
        if page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
            raise AssertionError("Mobile view has horizontal overflow")
        page.screenshot(path=str(out / "mobile.png"), full_page=True)
        checks.append("Mobile layout has no horizontal overflow")
        with urlopen(BASE + "/api/absee-profile") as response:
            result = json.load(response)
            if response.status != 200 or response.headers.get("Cache-Control") != "no-store":
                raise AssertionError("API status or cache policy changed")
        if result["official_toyota_2024b_validation"]["issuer_independent_validation"] is not False:
            raise AssertionError("Issuer independence limitation missing")
        checks.append("API pins source audit and marks same-issuer validation")
        if errors:
            raise AssertionError(errors)
        checks.append("No browser JavaScript errors")
        browser.close()
    (out / "receipt.json").write_text(json.dumps({"status": "PASS", "checks": checks,
        "periods": 29, "rows": 1518106}, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()


