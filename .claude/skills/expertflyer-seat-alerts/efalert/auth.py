"""ExpertFlyer login through the Auth0 Lock widget (email/password)."""
from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PWTimeout

from . import selectors
from .browser import Session


def is_authenticated(page: Page, settings) -> bool:
    """Best-effort check: load the app root and look for logged-in markers."""
    page.goto(settings.base_url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    if "/auth/login" in page.url or "auth.expertflyer.com" in page.url:
        return False
    for marker in selectors.AUTHED_MARKERS:
        try:
            if page.locator(marker).first.is_visible(timeout=1000):
                return True
        except PWTimeout:
            continue
    # No explicit marker, but we weren't bounced to login: treat as authed.
    return True


def login(session: Session, force: bool = False) -> bool:
    """Log in and persist the session. Returns True on success.

    With saved cookies and force=False, verifies the existing session instead of
    re-entering credentials. When the account requires MFA or a social provider,
    run with EF_HEADLESS=false and complete the challenge manually before the
    timeout; the resulting cookies are then saved.
    """
    settings = session.settings
    page = session.page

    if not force and session.has_saved_state() and is_authenticated(page, settings):
        return True

    settings.require_credentials()
    page.goto(settings.login_url(), wait_until="domcontentloaded")
    # The app redirects to the Auth0 tenant; wait for the Lock form to render.
    page.wait_for_selector(selectors.LOGIN["email"], timeout=settings.timeout_ms)
    page.fill(selectors.LOGIN["email"], settings.email)
    page.fill(selectors.LOGIN["password"], settings.password)
    page.click(selectors.LOGIN["submit"])

    # Success = Auth0 hands control back to www.expertflyer.com (the callback).
    try:
        page.wait_for_url(f"{settings.base_url}/**", timeout=settings.timeout_ms)
    except PWTimeout:
        # MFA / consent screens can stall here; in headed mode give the user time.
        if not settings.headless:
            page.wait_for_url(f"{settings.base_url}/**", timeout=180_000)
        else:
            raise SystemExit(
                "Login did not complete. If your account uses MFA or Google "
                "sign-in, re-run with EF_HEADLESS=false and finish manually."
            )

    page.wait_for_timeout(1500)
    if not is_authenticated(page, settings):
        raise SystemExit("Login appeared to fail (still not authenticated).")
    session.save_state()
    return True
