"""Resolve a flight by airline+number to one or more seat-map URLs.

Two stages: (1) find origin/destination — either supplied by the caller or
looked up from the airline's status page; (2) drive ExpertFlyer's `/air/seat-map`
form to a results URL and probe each cabin class. The form only returns one
cabin per submission, so we mutate the `cabinClass` query parameter to capture
the rest in a single browser session.

Route lookup is intentionally narrow: Alaska Airlines only. Other airlines fall
back to a clear error pointing the caller at `--from`/`--to`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as DateType

from playwright.sync_api import TimeoutError as PWTimeoutError

from .browser import Session

# Typed into the EF airline autocomplete. The dropdown shows "Name (CODE)" and
# we click the option whose text contains "(CODE)", so the typed prefix only
# needs to narrow the list — exact spelling isn't critical.
AIRLINE_NAMES: dict[str, str] = {
    "AS": "Alaska",
    "AA": "American",
    "UA": "United",
    "DL": "Delta",
    "B6": "JetBlue",
    "WN": "Southwest",
    "F9": "Frontier",
    "NK": "Spirit",
    "HA": "Hawaiian",
    "AC": "Air Canada",
    "BA": "British Airways",
    "LH": "Lufthansa",
}

# Cabin codes EF accepts in the cabinClass query parameter. F/D = First,
# C/I/J/Z = Business, W = Premium Economy, Y/M/B = Economy. We probe a small
# representative set rather than every fare bucket.
PROBE_CABINS = ("F", "D", "C", "J", "W", "Y")


@dataclass
class Route:
    origin: str
    destination: str


def lookup_route(session: Session, airline: str, flight: str, when: DateType) -> Route:
    """Look up origin/destination for a flight on a given date.

    Currently supports Alaska Airlines only. For other carriers, raises
    ValueError so the caller can ask for `--from`/`--to` explicitly.
    """
    if airline.upper() == "AS":
        return _lookup_alaska(session, flight, when)
    raise ValueError(
        f"Route lookup not implemented for {airline.upper()}; "
        "pass --from <IATA> --to <IATA> explicitly."
    )


def _lookup_alaska(session: Session, flight: str, when: DateType) -> Route:
    url = f"https://www.alaskaair.com/status/{flight}/{when.isoformat()}"
    page = session.context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_selector("text=/Scheduled/i", timeout=10000)
        except PWTimeoutError:
            pass
        text = page.inner_text("body")
    finally:
        page.close()
    paren_codes = re.findall(r"\(([A-Z]{3})\)", text)
    if len(paren_codes) >= 2:
        return Route(origin=paren_codes[0], destination=paren_codes[1])
    raise RuntimeError(
        f"Could not parse route for AS{flight} on {when.isoformat()} from {url}. "
        "Pass --from/--to explicitly."
    )


def find_seatmap_urls(
    session: Session,
    *,
    origin: str,
    destination: str,
    airline: str,
    flight: str,
    when: DateType,
) -> dict[str, str]:
    """Drive /air/seat-map to the flight; return {cabin_code: seatmap_url}."""
    page = session.page
    page.goto("https://www.expertflyer.com/air/seat-map", wait_until="networkidle")
    page.wait_for_timeout(1200)

    autos = page.locator("input[id^='autocomplete-']")
    autos.nth(0).fill(origin)
    page.wait_for_timeout(600)
    page.get_by_role("option").first.click()

    autos.nth(1).fill(destination)
    page.wait_for_timeout(600)
    page.get_by_role("option").first.click()

    page.fill("#departDate", when.strftime("%m/%d/%y"))

    name = AIRLINE_NAMES.get(airline.upper(), airline.upper())
    autos.nth(2).fill(name)
    page.wait_for_timeout(800)
    code_marker = f"({airline.upper()})"
    try:
        page.get_by_role("option").filter(has_text=code_marker).first.click(timeout=3000)
    except Exception:
        page.get_by_role("option").first.click()

    page.fill("#flightNumber", flight)
    page.wait_for_timeout(300)

    for label in ("First", "Business", "Premium Economy", "Economy"):
        try:
            page.get_by_label(label, exact=True).check(timeout=1000)
        except Exception:
            pass

    page.get_by_role("button", name="Search", exact=True).first.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)

    primary = page.url
    if "/seat-map/results" not in primary:
        raise RuntimeError(
            "Seat-map search did not produce a results URL — the flight may not "
            "exist on that date, or the route may be wrong."
        )
    primary_cabin = _cabin_from_url(primary) or "?"
    urls = {primary_cabin: primary}
    # Fingerprint the primary cabin so we can skip alternate codes that map to
    # the same physical cabin (e.g. AS exposes its First cabin under both D and F).
    seen: set[str] = {_seat_fingerprint(page)}

    for cabin in PROBE_CABINS:
        if cabin == primary_cabin:
            continue
        alt = _swap_cabin(primary, cabin)
        page.goto(alt, wait_until="networkidle")
        try:
            page.wait_for_selector("button[data-seat-id]", timeout=4000)
        except PWTimeoutError:
            continue
        fp = _seat_fingerprint(page)
        if fp in seen:
            continue
        seen.add(fp)
        urls[cabin] = alt
    return urls


def _seat_fingerprint(page) -> str:
    """A stable hash of the seat labels currently rendered, for cabin dedup."""
    labels = page.eval_on_selector_all(
        "button[data-seat-id]",
        "els => els.map(e => e.getAttribute('data-seat-id')).sort().join(',')",
    )
    return labels or ""


def _cabin_from_url(url: str) -> str | None:
    m = re.search(r"[?&]cabinClass=([A-Z])", url)
    return m.group(1) if m else None


def _swap_cabin(url: str, cabin: str) -> str:
    if "cabinClass=" in url:
        return re.sub(r"cabinClass=[^&]*", f"cabinClass={cabin}", url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}cabinClass={cabin}"
