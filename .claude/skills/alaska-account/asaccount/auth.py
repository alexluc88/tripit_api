"""Alaska login, including the email one-time-code (2FA) handoff.

The agent can't read the user's email, so when Alaska challenges for a code we:
  * print "2FA REQUIRED" on stderr (a caller can watch for it),
  * poll the 2FA file for the digits, and/or
  * (in headed mode) just wait for the user to type it in the visible window.
"""
from __future__ import annotations

import sys
import time

from .browser import Session, has_saved_state
from . import selectors


def _try_visible(page, selector: str, timeout: int = 1500) -> bool:
    try:
        return page.locator(selector).first.is_visible(timeout=timeout)
    except Exception:
        return False


def on_challenge(page) -> bool:
    return any(_try_visible(page, m, 800) for m in selectors.CHALLENGE_MARKERS)


def is_authenticated(session: Session) -> bool:
    page = session.page
    settings = session.settings
    page.goto(settings.overview_url(), wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    if "/login" in page.url or "signin" in page.url.lower():
        return False
    for marker in selectors.AUTHED_MARKERS:
        if _try_visible(page, marker, 1000):
            return True
    # Not bounced to login and the overview rendered: treat as authed.
    return "/account" in page.url


def _read_2fa_code(settings) -> str | None:
    f = settings.two_fa_file
    if f.exists():
        code = f.read_text().strip()
        if code:
            return "".join(ch for ch in code if ch.isdigit())
    return None


def _await_2fa_code(settings) -> str | None:
    """Block (up to two_fa_wait_ms) for a code to land in the 2FA file."""
    print("2FA REQUIRED", file=sys.stderr, flush=True)
    print(
        f"Alaska sent a one-time code. Write it to {settings.two_fa_file} "
        f"(or run headed with AS_HEADLESS=false and type it in the window).",
        file=sys.stderr,
        flush=True,
    )
    settings.two_fa_file.unlink(missing_ok=True)
    deadline = time.monotonic() + settings.two_fa_wait_ms / 1000
    while time.monotonic() < deadline:
        code = _read_2fa_code(settings)
        if code:
            settings.two_fa_file.unlink(missing_ok=True)
            return code
        time.sleep(2)
    return None


def _fill_2fa(page, settings, code: str) -> None:
    single = page.locator(selectors.TWO_FA["code_single"]).first
    if single.count() and single.is_visible():
        single.fill(code)
    else:
        boxes = page.locator(selectors.TWO_FA["code_digits"])
        n = boxes.count()
        if n >= len(code):
            for i, digit in enumerate(code):
                boxes.nth(i).fill(digit)
        else:
            page.keyboard.type(code)
    page.click(selectors.TWO_FA["submit"])


def _handle_2fa(session: Session) -> None:
    page = session.page
    settings = session.settings
    if not _try_visible(page, selectors.TWO_FA["prompt"], 4000):
        return  # no 2FA challenge presented
    if settings.headless:
        code = _await_2fa_code(settings)
        if not code:
            raise SystemExit(
                "2FA code was not provided in time. Re-run after writing the code "
                f"to {settings.two_fa_file}, or use AS_HEADLESS=false."
            )
        _fill_2fa(page, settings, code)
    else:
        # Headed: let the user complete the challenge in the visible browser.
        print("Complete the emailed-code prompt in the browser window…",
              file=sys.stderr, flush=True)
    # Best-effort settle; is_authenticated() is the source of truth, so a missed
    # redirect here shouldn't abort the login.
    try:
        page.wait_for_url(f"{settings.base_url}/account/**",
                          timeout=settings.two_fa_wait_ms)
    except Exception:
        pass


def login(session: Session, force: bool = False) -> bool:
    """Log in and persist the session (in the profile dir). Returns True on success."""
    settings = session.settings
    page = session.page

    if not force and has_saved_state(settings) and is_authenticated(session):
        return True

    settings.require_credentials()
    page.goto(settings.login_url(), wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    if on_challenge(page):
        print("Bot challenge detected; waiting for it to clear…", file=sys.stderr)
        page.wait_for_timeout(6000)

    page.wait_for_selector(selectors.LOGIN["username"], timeout=settings.timeout_ms)
    page.fill(selectors.LOGIN["username"], settings.username)
    page.fill(selectors.LOGIN["password"], settings.password)
    page.click(selectors.LOGIN["submit"])
    page.wait_for_timeout(3000)

    _handle_2fa(session)

    page.wait_for_timeout(1500)
    if not is_authenticated(session):
        raise SystemExit(
            "Login appeared to fail (still not authenticated). If a bot challenge "
            "is blocking, re-run with AS_HEADLESS=false and AS_BROWSER_CHANNEL=chrome."
        )
    return True
