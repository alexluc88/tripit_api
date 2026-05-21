"""Playwright session lifecycle: launch, restore/save cookies, hand back a Page."""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .config import Settings


class Session:
    """Wraps a Playwright browser context with persisted ExpertFlyer auth state."""

    def __init__(self, settings: Settings, browser: Browser, context: BrowserContext):
        self.settings = settings
        self._browser = browser
        self.context = context
        self.page: Page = context.new_page()
        self.page.set_default_timeout(settings.timeout_ms)

    def save_state(self) -> None:
        self.settings.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.context.storage_state(path=str(self.settings.state_file))

    def has_saved_state(self) -> bool:
        f = self.settings.state_file
        if not f.exists():
            return False
        try:
            data = json.loads(f.read_text())
            return bool(data.get("cookies"))
        except (json.JSONDecodeError, OSError):
            return False


@contextmanager
def open_session(settings: Settings, use_saved_state: bool = True) -> Iterator[Session]:
    """Open a browser session, restoring saved auth cookies when present."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.headless)
        ctx_kwargs: dict = {
            "user_agent": settings.user_agent,
            "ignore_https_errors": settings.insecure_tls,
            "viewport": {"width": 1440, "height": 1000},
        }
        if use_saved_state and settings.state_file.exists():
            ctx_kwargs["storage_state"] = str(settings.state_file)
        context = browser.new_context(**ctx_kwargs)
        session = Session(settings, browser, context)
        try:
            yield session
        finally:
            context.close()
            browser.close()
