"""Create an ExpertFlyer Seat Alert by filling and submitting the alert form.

NEEDS VERIFICATION: the authenticated alert form could not be inspected without
an account. Selectors live in selectors.ALERT; use `dump-dom` on the real alert
page to confirm field names, then adjust. `--dry-run` fills everything and
screenshots without submitting, so the flow can be validated safely first.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout

from . import selectors
from .browser import Session


@dataclass
class AlertRequest:
    airline: str
    flight: str
    date: str            # YYYY-MM-DD
    origin: str = ""
    destination: str = ""
    cabin: str = ""
    seats: list[str] | None = None  # specific seats, e.g. ["12A", "12C"]


def _fill_if_present(page, selector: str, value: str) -> bool:
    if not value:
        return False
    loc = page.locator(selector).first
    try:
        if loc.count() and loc.is_visible(timeout=2000):
            loc.fill(value)
            return True
    except PWTimeout:
        return False
    return False


def create_alert(
    session: Session,
    url: str,
    req: AlertRequest,
    out_dir: Path,
    dry_run: bool = True,
) -> dict:
    """Open the alert form, fill it, and (unless dry_run) submit."""
    page = session.page
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(1500)

    filled = {
        "airline": _fill_if_present(page, selectors.ALERT["airline"], req.airline),
        "flight": _fill_if_present(page, selectors.ALERT["flight"], req.flight),
        "date": _fill_if_present(page, selectors.ALERT["date"], req.date),
        "origin": _fill_if_present(page, selectors.ALERT["from"], req.origin),
        "destination": _fill_if_present(page, selectors.ALERT["to"], req.destination),
        "seats": _fill_if_present(
            page, selectors.ALERT["seats"], ",".join(req.seats or [])
        ),
    }
    if req.cabin:
        try:
            page.select_option(selectors.ALERT["cabin"], label=req.cabin)
            filled["cabin"] = True
        except Exception:
            filled["cabin"] = False

    shot = out_dir / ("alert_dryrun.png" if dry_run else "alert_submitted.png")

    if dry_run:
        page.screenshot(path=str(shot), full_page=True)
        return {"submitted": False, "filled": filled, "screenshot": str(shot),
                "note": "dry-run: form filled but not submitted"}

    page.click(selectors.ALERT["submit"])
    page.wait_for_timeout(2500)
    page.screenshot(path=str(shot), full_page=True)
    return {"submitted": True, "filled": filled, "screenshot": str(shot), "url": page.url}
