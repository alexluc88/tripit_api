"""All DOM selectors in one place, so tuning against the live site is a one-file job.

VERIFIED selectors were confirmed against the real ExpertFlyer pages.
NEEDS-VERIFICATION selectors are best-effort: ExpertFlyer's authenticated pages
(seat map, seat alert form) are behind a paywall and could not be inspected
without an account. Run `efalert dump-dom <url>` while logged in to capture the
real markup, then adjust the values below.
"""

# --- Auth0 Lock login page (VERIFIED) ---------------------------------------
# Auth0 prefixes element ids per-render (e.g. "1-email"), so target by name.
LOGIN = {
    "email": 'input[name="email"]',
    "password": 'input[name="password"]',
    "submit": 'button[name="submit"]',
    "google": 'text=/sign in with google/i',
}

# Heuristic markers that mean "we are logged in" once redirected back to the app.
AUTHED_MARKERS = [
    'a[href*="logout"]',
    'text=/log ?out/i',
    'text=/my account/i',
]

# --- Seat map page (NEEDS VERIFICATION) -------------------------------------
# The seat-map extractor (seatmap.py) is geometry-based and mostly selector-free:
# it scans for elements whose visible label looks like a seat (e.g. "12A") and
# reads availability from class/aria/title text. These selectors only narrow the
# search root and identify the legend; tune them with dump-dom output.
SEATMAP = {
    # Container the seat grid lives in. Falls back to <body> if not found.
    "map_root": '[class*="seatmap" i], [class*="seat-map" i], [data-testid*="seatmap" i]',
    # Individual seat cells. The extractor also auto-detects by label regex.
    "seat_cell": '[class*="seat" i]',
    # Legend rows explaining what each colour/symbol means.
    "legend_root": '[class*="legend" i], [aria-label*="legend" i]',
    "legend_item": '[class*="legend" i] li, [class*="legend" i] [class*="item" i]',
}

# Tokens (checked against a seat element's class/aria/title, lowercased) that
# indicate the seat is bookable. Order matters: "unavailable"/"occupied" win.
SEAT_AVAILABLE_TOKENS = ["available", "open", "free", "vacant", "selectable", "empty"]
SEAT_UNAVAILABLE_TOKENS = [
    "unavailable", "occupied", "taken", "blocked", "reserved", "sold", "disabled", "no-seat",
]

# --- Seat alert form (NEEDS VERIFICATION) -----------------------------------
ALERT = {
    "airline": 'input[name*="airline" i], input[placeholder*="airline" i]',
    "flight": 'input[name*="flight" i], input[placeholder*="flight" i]',
    "date": 'input[name*="date" i], input[type="date"]',
    "from": 'input[name*="origin" i], input[name*="from" i], input[placeholder*="from" i]',
    "to": 'input[name*="destination" i], input[name*="to" i], input[placeholder*="to" i]',
    "cabin": 'select[name*="cabin" i], select[name*="class" i]',
    "seats": 'input[name*="seat" i], textarea[name*="seat" i]',
    "submit": 'button[type="submit"], button:has-text("Create"), button:has-text("Add Alert")',
}
