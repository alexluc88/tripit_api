"""Create an ExpertFlyer Seat Alert.

VERIFIED flow: seat alerts are created on the seat-map page itself, not a
separate form. You click the seats to watch (`button[data-seat-id]`), type a
name into `#alertName`, and click the "Create Alert" submit button. You can
select occupied/blocked seats — that's the point of an alert (notify when they
free up).

Plan limits apply: the Free plan allows 1 active alert. When the limit is
reached the submit button is disabled and an "Alert Limit Reached" banner shows;
this is detected and reported instead of silently failing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout

from .browser import Session

ALERT_NAME_SEL = "#alertName"
CREATE_BTN_SEL = 'button[type="submit"]:has-text("Create Alert")'
# The seat-alert form is collapsed until this control is clicked.
REVEAL_SEL = 'button:has-text("Set Alert"), button:has-text("Seat Alert"), button:has-text("Create Seat Alert")'
# Several phrases indicate the plan's active-alert limit is reached.
LIMIT_TEXT_SEL = ('text=/Alert Limit Reached/i, text=/Max alerts reached/i, '
                  'text=/0 out of .* free active alerts/i')


@dataclass
class AlertRequest:
    name: str
    seats: list[str] = field(default_factory=list)  # seat labels to watch, e.g. ["6C","7C"]


def _select_seats(page, seats: list[str]) -> dict[str, bool]:
    selected: dict[str, bool] = {}
    for label in seats:
        loc = page.locator(f'button[data-seat-id="{label.strip().upper()}"]')
        try:
            if loc.count():
                loc.first.click()
                selected[label.upper()] = True
            else:
                selected[label.upper()] = False
        except PWTimeout:
            selected[label.upper()] = False
    return selected


def _reveal_form(page) -> None:
    """The Create Seat Alert form is collapsed by default; click to expand it."""
    if page.locator(ALERT_NAME_SEL).count() and page.locator(ALERT_NAME_SEL).first.is_visible():
        return
    try:
        btn = page.locator(REVEAL_SEL).first
        if btn.count():
            btn.click()
            page.wait_for_timeout(800)
    except PWTimeout:
        pass


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
    """Select seats on the seat map, name the alert, and (unless dry_run) submit."""
    page = session.page
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(seatmap_url, wait_until="networkidle")
    try:
        page.wait_for_selector('button[data-seat-id]', timeout=session.settings.timeout_ms)
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

    limit_reached = _limit_reached(page)
    submit = page.locator(CREATE_BTN_SEL).first
    submit_enabled = bool(submit.count()) and submit.is_enabled()

    base = {
        "selected_seats": selected,
        "name_filled": name_filled,
        "limit_reached": limit_reached,
        "submit_enabled": submit_enabled,
    }

    if limit_reached or not submit_enabled:
        shot = out_dir / "alert_blocked.png"
        page.screenshot(path=str(shot), full_page=True)
        return base | {
            "submitted": False, "screenshot": str(shot),
            "note": ("Alert limit reached for this plan — delete an existing alert "
                     "or upgrade. Submit button is disabled."
                     if limit_reached else "Submit button is disabled (check seats/name)."),
        }

    if dry_run:
        shot = out_dir / "alert_dryrun.png"
        page.screenshot(path=str(shot), full_page=True)
        return base | {"submitted": False, "screenshot": str(shot),
                       "note": "dry-run: seats selected and name filled, not submitted"}

    submit.click()
    page.wait_for_timeout(2500)
    shot = out_dir / "alert_submitted.png"
    page.screenshot(path=str(shot), full_page=True)
    return base | {"submitted": True, "screenshot": str(shot), "url": page.url}
