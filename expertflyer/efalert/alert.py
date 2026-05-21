"""Create / delete an ExpertFlyer Seat Alert.

Seat alerts are created on the seat-map page (not a separate form). You reveal
the "Create Seat Alert" panel ("Set Alert"), click the seats to watch
(`button[data-seat-id]`, occupied seats included — that's the point), type a
name into `#alertName`, optionally tick "Send Test Email" (`#sendTestEmail-0`),
then click "Create Alert".

Plan limits apply (Free = 1 active alert): when reached, the submit button is
disabled and an "Alert Limit Reached" banner shows; this is detected and
reported. Deleting an existing alert frees the slot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout

from .browser import Session

ALERT_NAME_SEL = "#alertName"
SEND_TEST_EMAIL_SEL = "#sendTestEmail-0"
CREATE_BTN_SEL = 'button[type="submit"]:has-text("Create Alert")'
REVEAL_SEL = ('button:has-text("Set Alert"), button:has-text("Create Seat Alert"), '
              'button:has-text("Seat Alert")')
COOKIE_ACCEPT_SEL = "#onetrust-accept-btn-handler"
DELETE_BTN_SEL = 'button[title="Delete Alert"]'
LIMIT_TEXT_SEL = ('text=/Alert Limit Reached/i, text=/Max alerts reached/i, '
                  'text=/0 out of .* free active alerts/i')


@dataclass
class AlertRequest:
    name: str
    seats: list[str] = field(default_factory=list)
    send_test_email: bool = False


def _dismiss_cookies(page) -> None:
    try:
        btn = page.locator(COOKIE_ACCEPT_SEL).first
        if btn.count() and btn.is_visible(timeout=2000):
            btn.click()
            page.wait_for_timeout(400)
    except PWTimeout:
        pass


def _reveal_form(page) -> None:
    name = page.locator(ALERT_NAME_SEL).first
    if name.count() and name.is_visible():
        return
    try:
        btn = page.locator(REVEAL_SEL).first
        if btn.count():
            btn.click()
            page.wait_for_timeout(800)
    except PWTimeout:
        pass


def _select_seats(page, seats: list[str]) -> dict[str, bool]:
    selected: dict[str, bool] = {}
    for label in seats:
        sid = label.strip().upper()
        loc = page.locator(f'button[data-seat-id="{sid}"]').first
        try:
            if not loc.count():
                selected[sid] = False
                continue
            loc.scroll_into_view_if_needed(timeout=3000)
            loc.click(timeout=3000)
            page.wait_for_timeout(60)
            selected[sid] = loc.get_attribute("aria-pressed") == "true"
        except PWTimeout:
            selected[sid] = False
    return selected


def _limit_reached(page) -> bool:
    try:
        return page.locator(LIMIT_TEXT_SEL).first.is_visible(timeout=1500)
    except PWTimeout:
        return False


def create_alert(
    session: Session,
    seatmap_url: str,
    req: AlertRequest,
    out_dir: Path,
    dry_run: bool = True,
) -> dict:
    """Select seats, name the alert, optionally tick test-email, then submit."""
    page = session.page
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(seatmap_url, wait_until="networkidle")
    _dismiss_cookies(page)
    try:
        page.wait_for_selector("button[data-seat-id]", timeout=session.settings.timeout_ms)
    except PWTimeout:
        page.wait_for_timeout(2500)

    _reveal_form(page)
    selected = _select_seats(page, req.seats)

    name_filled = False
    try:
        if page.locator(ALERT_NAME_SEL).count():
            page.fill(ALERT_NAME_SEL, req.name)
            name_filled = True
    except PWTimeout:
        pass

    test_email_checked = False
    if req.send_test_email:
        try:
            box = page.locator(SEND_TEST_EMAIL_SEL).first
            if box.count():
                box.check()
                test_email_checked = box.is_checked()
        except PWTimeout:
            pass

    limit_reached = _limit_reached(page)
    submit = page.locator(CREATE_BTN_SEL).first
    submit_enabled = bool(submit.count()) and submit.is_enabled()

    base = {
        "selected_seats": selected,
        "selected_count": sum(1 for v in selected.values() if v),
        "name_filled": name_filled,
        "test_email_checked": test_email_checked,
        "limit_reached": limit_reached,
        "submit_enabled": submit_enabled,
    }

    if dry_run:
        shot = out_dir / "alert_dryrun.png"
        page.screenshot(path=str(shot), full_page=True)
        return base | {"submitted": False, "screenshot": str(shot),
                       "note": "dry-run: form prepared, not submitted"}

    if limit_reached or not submit_enabled:
        shot = out_dir / "alert_blocked.png"
        page.screenshot(path=str(shot), full_page=True)
        return base | {"submitted": False, "screenshot": str(shot),
                       "note": "blocked: limit reached or submit disabled"}

    submit.click()
    page.wait_for_timeout(2500)
    shot = out_dir / "alert_submitted.png"
    page.screenshot(path=str(shot), full_page=True)
    return base | {"submitted": True, "screenshot": str(shot), "url": page.url}


def delete_alert(session: Session, alerts_url: str, out_dir: Path,
                 confirm: bool = False) -> dict:
    """Delete an existing alert from the saved-alerts page.

    With confirm=False, only locates the delete control and screenshots (safe).
    With confirm=True, clicks Delete and accepts any confirmation dialog.
    """
    page = session.page
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(alerts_url, wait_until="networkidle")
    _dismiss_cookies(page)
    page.wait_for_timeout(1500)

    btn = page.locator(DELETE_BTN_SEL).first
    found = bool(btn.count())
    if not confirm or not found:
        shot = out_dir / "delete_preview.png"
        page.screenshot(path=str(shot), full_page=True)
        return {"deleted": False, "delete_button_found": found, "screenshot": str(shot),
                "note": "preview only" if found else "no Delete Alert button found"}

    # Accept a possible native confirm() dialog.
    page.on("dialog", lambda d: d.accept())
    btn.click()
    page.wait_for_timeout(800)
    # Or a custom modal with a confirm button.
    for sel in ('button:has-text("Delete")', 'button:has-text("Confirm")',
                'button:has-text("Yes")'):
        try:
            c = page.locator(sel).first
            if c.count() and c.is_visible(timeout=1000):
                c.click()
                break
        except PWTimeout:
            continue
    page.wait_for_timeout(2000)
    shot = out_dir / "delete_done.png"
    page.screenshot(path=str(shot), full_page=True)
    return {"deleted": True, "screenshot": str(shot), "url": page.url}
