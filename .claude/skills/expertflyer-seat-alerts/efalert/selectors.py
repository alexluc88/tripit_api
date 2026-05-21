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

# --- Seat map page (VERIFIED against AS331 SEA-ABQ) -------------------------
# Each seat is <button data-seat-id="6A" aria-label="Seat 6A, occupied" ...>.
# The extractor reads the label from data-seat-id and the state from the text
# after the comma in aria-label. If data-seat-id is absent (other markup), it
# falls back to a generic label-regex scan. Tune with dump-dom output.
SEATMAP = {
    # Primary, exact seat selector. Seats render async, so we wait on this.
    "seat_cell": "button[data-seat-id]",
    "seat_id_attr": "data-seat-id",
    # Legend panel (best-effort; the extractor also derives a legend from the
    # distinct seat states it actually observed, which is more reliable).
    "legend_root": '[class*="legend" i], [aria-label*="legend" i]',
}

# Tokens (checked against a seat's state + aria-label, lowercased). Unavailable
# wins ties, so unknown states default to "not bookable" (safe for alerts).
SEAT_AVAILABLE_TOKENS = ["available", "open", "free", "vacant", "selectable", "empty"]
SEAT_UNAVAILABLE_TOKENS = [
    "unavailable", "occupied", "taken", "blocked", "reserved", "sold", "no-seat",
]

# --- Seat alert (VERIFIED) --------------------------------------------------
# The "Create Seat Alert" panel is embedded on the seat-map page. Seats are
# selected by clicking their data-seat-id buttons; see alert.py.
ALERT = {
    "name": "#alertName",
    "submit": 'button[type="submit"]:has-text("Create Alert")',
    "limit_banner": 'text=/Alert Limit Reached/i',
}
