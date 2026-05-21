# efalert — ExpertFlyer seat-alert automation

Browser-driven (Playwright) automation that logs into [ExpertFlyer](https://www.expertflyer.com/),
captures a flight's **seat map**, lets you choose seats in **plain English**, shows a
**preview image** of the chosen seats, and then creates a **Seat Alert**.

The CLI exposes small primitives. The natural-language step happens in the calling
agent/conversation (e.g. Claude): it reads the seat-map screenshot + `seats.json`,
maps "aisle seat near the front in business" to concrete seat labels, previews them,
and on your confirmation creates the alert.

```
seatmap ──► (you describe what you want) ──► preview ──► you confirm ──► create-alert
```

## Status of selectors

| Part | Status | Notes |
|------|--------|-------|
| Login (Auth0 email/password) | **Verified** live | `input[name=email]`, `input[name=password]`, `button[name=submit]` |
| Seat-map extraction | **Verified** live (AS331 SEA-ABQ) | Seats are `button[data-seat-id]`; state from `aria-label` ("Seat 6A, occupied"). 163 seats parsed, states + window/aisle/middle correct. |
| Preview rendering | **Verified** live | Highlights align pixel-accurately on the real screenshot. |
| Seat-alert creation | **Verified** live (created an active alert) | Embedded on the seat-map page. Click "Seat Alert" to enter alert mode (this enables the seats), tap seats, fill `#alertName`, optionally tick `#sendTestEmail-0`, click "Create Alert". The panel renders mobile/desktop/print copies, so the code targets the `:visible` one. |
| Seat-alert deletion | **Verified** live | `button[title="Delete Alert"]` on the saved-alerts page (loads async, so the code waits for it). |

### Plan limits matter

Seat alerts count against your ExpertFlyer plan's active-alert limit (Free = **1**).
When the limit is reached, the "Create Alert" button is disabled and an
"Alert Limit Reached" banner appears; `create-alert` detects this and reports it
instead of silently failing. To add a new alert you must delete an existing one
(`/alerts?type=SEAT_MAP&status=ACTIVE`) or upgrade.

> Only **email/password** Auth0 logins can be automated. "Sign in with Google"
> cannot (Google blocks automated logins). MFA accounts: run with `EF_HEADLESS=false`
> and complete the challenge manually once; the session cookie is then cached.

## Install

```bash
cd expertflyer
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env   # then edit EF_EMAIL / EF_PASSWORD
```

## Usage

```bash
# 1) Log in once (caches cookies in .efstate.json)
python -m efalert login

# 2) Capture a seat map. Copy the seat-map URL from ExpertFlyer.
python -m efalert seatmap --url "https://www.expertflyer.com/..." 
#    -> out/seatmap.png  (screenshot)
#    -> out/seatmap.json (legend + every seat: label, available, window/aisle/middle, bbox)

# 3) Preview the seats you want highlighted on the map
python -m efalert preview --seats 12A,12C
#    -> out/preview.png

# 4) Create the alert from the seat-map page. Defaults to a DRY RUN
#    (selects seats + names the alert + screenshots, but does NOT submit).
python -m efalert create-alert --url "https://www.expertflyer.com/air/seat-map/results?..." \
    --name "Aisle seats AS331" --seats 6C,7C,8C
# Add --confirm to actually submit (subject to your plan's alert limit).
```

### Tuning the authenticated-page selectors

```bash
python -m efalert dump-dom --url "https://www.expertflyer.com/...seatmap..." --name seatmap_dump
# Inspect out/seatmap_dump.{html,png,elements.json}, then edit efalert/selectors.py
```

## Configuration

All via env vars / `.env` (see `.env.example`): `EF_EMAIL`, `EF_PASSWORD`,
`EF_HEADLESS`, `EF_INSECURE_TLS` (only behind a TLS-intercepting proxy),
`EF_STATE_FILE`, `EF_OUT_DIR`, `EF_TIMEOUT_MS`.

## Tests

```bash
pytest                 # offline unit tests (seat logic, preview rendering, CLI)
EF_LIVE_TESTS=1 pytest # also checks the live login page still has the expected fields
```
