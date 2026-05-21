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

# The seat-map page renders mobile + desktop + print copies of the alert panel,
# so several elements share each id; always act on the :visible one.
ALERT_NAME_SEL = "#alertName:visible"
SEND_TEST_EMAIL_SEL = "#sendTestEmail-0:visible"
CREATE_BTN_SEL = 'button[type="submit"]:has-text("Create Alert"):visible'
# Clicking "Seat Alert" enters alert mode: it reveals the form AND flips each
# seat's aria-disabled to false so the seats become selectable.
REVEAL_NAME = "Seat Alert"
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


def _first_visible(loc):
    for i in range(loc.count()):
        el = loc.nth(i)
        try:
            if el.is_visible():
                return el
        except PWTimeout:
            continue
    return None


def _reveal_form(page) -> None:
    """Click the visible "Seat Alert" button to enter alert-creation mode."""
    if page.locator(ALERT_NAME_SEL).count():
        return  # already revealed
    btn = _first_visible(page.get_by_role("button", name=REVEAL_NAME))
    if btn:
        try:
            btn.click()
            page.wait_for_timeout(1000)
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
    # domcontentloaded + explicit wait is more reliable than networkidle here
    # (the SPA's analytics keep the network busy).
    page.goto(seatmap_url, wait_until="domcontentloaded")
    _dismiss_cookies(page)
    try:
        page.wait_for_selector("button[data-seat-id]", timeout=session.settings.timeout_ms)
    except PWTimeout:
        page.wait_for_timeout(2500)

    _reveal_form(page)
    selected = _select_seats(page, req.seats)

    name_filled = False
    name = _first_visible(page.locator("#alertName"))
    if name:
        try:
            name.fill(req.name)
            name_filled = True
        except PWTimeout:
            pass

    test_email_checked = False
    if req.send_test_email:
        box = _first_visible(page.locator("#sendTestEmail-0"))
        if box:
            try:
                box.check()
                test_email_checked = box.is_checked()
            except PWTimeout:
                pass

    limit_reached = _limit_reached(page)
    submit = _first_visible(page.locator('button[type="submit"]:has-text("Create Alert")'))
    submit_enabled = bool(submit) and submit.is_enabled()

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
    page.goto(alerts_url, wait_until="domcontentloaded")
    _dismiss_cookies(page)
    page.wait_for_timeout(2000)

    btn = _first_visible(page.locator(DELETE_BTN_SEL)) or page.locator(DELETE_BTN_SEL).first
    found = bool(page.locator(DELETE_BTN_SEL).count())
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
