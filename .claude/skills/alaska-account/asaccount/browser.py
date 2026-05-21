"""Browser session lifecycle.

Prefers Patchright (an undetected Playwright fork) because alaskaair.com blocks
vanilla Playwright at the Akamai challenge; falls back to plain Playwright if
Patchright isn't installed (so the package still imports/tests without it).

Uses a *persistent* context (a real on-disk user-data dir) rather than a
storage_state json: it keeps cookies + local storage between runs, which both
survives 2FA better and looks less automated.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Iterator

from .config import Settings


def _import_playwright():
    """Return (sync_playwright, engine_name), preferring patchright."""
    try:
        from patchright.sync_api import sync_playwright  # type: ignore
        return sync_playwright, "patchright"
    except ImportError:
        from playwright.sync_api import sync_playwright  # type: ignore
        print(
            "WARNING: patchright not installed; falling back to vanilla Playwright. "
            "Alaska's bot challenge is likely to block this. Install with "
            "`pip install patchright && patchright install chromium`.",
            file=sys.stderr,
        )
        return sync_playwright, "playwright"


class Session:
    """Wraps a persistent browser context pointed at the user's Alaska profile."""

    def __init__(self, settings: Settings, context, engine: str):
        self.settings = settings
        self.context = context
        self.engine = engine
        self.page = context.pages[0] if context.pages else context.new_page()
        self.page.set_default_timeout(settings.timeout_ms)


@contextmanager
def open_session(settings: Settings) -> Iterator[Session]:
    sync_playwright, engine = _import_playwright()
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    ctx_kwargs: dict = {
        "user_data_dir": str(settings.profile_dir),
        "headless": settings.headless,
        "ignore_https_errors": settings.insecure_tls,
        # Patchright recommends letting the real window size through.
        "no_viewport": True,
    }
    if settings.channel:
        ctx_kwargs["channel"] = settings.channel
    if settings.user_agent:
        ctx_kwargs["user_agent"] = settings.user_agent

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(**ctx_kwargs)
        session = Session(settings, context, engine)
        try:
            yield session
        finally:
            context.close()


def has_saved_state(settings: Settings) -> bool:
    """A persisted login exists if the profile dir has cookie storage in it."""
    cookies = settings.profile_dir / "Default" / "Cookies"
    return cookies.exists() or any(settings.profile_dir.glob("**/Cookies"))
