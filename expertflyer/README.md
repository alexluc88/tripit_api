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
| Login (Auth0 email/password) | **Verified** against the live site | `input[name=email]`, `input[name=password]`, `button[name=submit]` |
| Seat-map extraction | Best-effort | Markup-agnostic: finds seat-labelled cells by geometry. Tune via `dump-dom`. |
| Seat-alert form | Best-effort | Field selectors in `efalert/selectors.py` need confirming on a real account. |

ExpertFlyer's seat-map and alert pages are behind a paid login that wasn't available
during development, so those selectors are isolated in `efalert/selectors.py` and can
be confirmed quickly with the `dump-dom` command (below).

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

# 4) Create the alert. Defaults to a DRY RUN (fills + screenshots, no submit).
python -m efalert create-alert --url "https://www.expertflyer.com/...alert..." \
    --airline UA --flight 837 --date 2026-06-01 --cabin Business --seats 12A,12C
# Add --confirm to actually submit.
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
