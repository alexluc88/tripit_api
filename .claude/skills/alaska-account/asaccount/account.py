"""Read-only scrapers for the Alaska account portal: miles + status, Wallet, and
recent activity. Each tries the centralized selectors first, then falls back to
scanning visible page text via the pure helpers in parse.py."""
from __future__ import annotations

from .browser import Session
from . import parse, selectors


def _first_text(page, selector: str) -> str | None:
    try:
        loc = page.locator(selector).first
        if loc.count() and loc.is_visible():
            return (loc.inner_text() or "").strip()
    except Exception:
        pass
    return None


def _body_text(page) -> str:
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def get_balance(session: Session) -> dict:
    """Miles balance + elite tier from the account overview page."""
    page = session.page
    settings = session.settings
    page.goto(settings.overview_url(), wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    miles = parse.parse_int(_first_text(page, selectors.BALANCE["miles"]))
    status = _first_text(page, selectors.BALANCE["status"])

    body = _body_text(page)
    if miles is None:
        miles = parse.find_miles(body)
    status = parse.find_status(status) or parse.find_status(body)

    return {"miles": miles, "elite_status": status, "url": page.url}


def get_wallet(session: Session) -> dict:
    """Wallet cash-like balance + the list of stored credits/certificates."""
    page = session.page
    settings = session.settings
    page.goto(settings.wallet_url(), wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    balance = parse.parse_money(_first_text(page, selectors.WALLET["balance"]))
    items: list[dict] = []
    try:
        rows = page.locator(selectors.WALLET["items"])
        for i in range(min(rows.count(), 50)):
            text = (rows.nth(i).inner_text() or "").strip()
            if not text:
                continue
            items.append({"text": " ".join(text.split()),
                          "amount": parse.parse_money(text)})
    except Exception:
        pass

    if balance is None:
        balance = parse.parse_money(_body_text(page))

    return {"wallet_balance": balance, "items": items, "url": page.url}


def get_activity(session: Session, limit: int = 20) -> dict:
    """Recent earn/redeem rows from the activity page (best-effort row text)."""
    page = session.page
    settings = session.settings
    page.goto(settings.activity_url(), wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    transactions: list[dict] = []
    try:
        rows = page.locator(selectors.ACTIVITY["rows"])
        for i in range(min(rows.count(), limit)):
            text = (rows.nth(i).inner_text() or "").strip()
            if not text:
                continue
            transactions.append({"text": " ".join(text.split()),
                                 "miles": parse.parse_int(text)})
    except Exception:
        pass

    return {"transactions": transactions, "count": len(transactions), "url": page.url}
