"""Live smoke test for the VERIFIED login selectors. Skipped unless EF_LIVE_TESTS=1.

This needs network access and a Playwright browser, but no ExpertFlyer account:
it only loads the public Auth0 login page and checks the fields still exist.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("EF_LIVE_TESTS") != "1",
    reason="set EF_LIVE_TESTS=1 to run live network tests",
)


def test_login_page_has_expected_fields():
    from playwright.sync_api import sync_playwright

    from efalert import selectors
    from efalert.config import Settings

    s = Settings()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=s.user_agent, ignore_https_errors=s.insecure_tls
        )
        page = ctx.new_page()
        page.goto(s.login_url(), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(selectors.LOGIN["email"], timeout=30000)
        assert page.locator(selectors.LOGIN["email"]).count() >= 1
        assert page.locator(selectors.LOGIN["password"]).count() >= 1
        assert page.locator(selectors.LOGIN["submit"]).count() >= 1
        browser.close()
