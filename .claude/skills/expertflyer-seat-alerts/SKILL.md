---
name: expertflyer-seat-alerts
description: >-
  Create, preview, and manage ExpertFlyer seat alerts via browser automation.
  Use when the user wants to set up or delete a seat alert, view a flight's seat
  map / seat availability, or be notified when specific seats (e.g. an aisle,
  window, or premium-cabin seat) open up on a flight on expertflyer.com.
---

# ExpertFlyer seat alerts

Drives expertflyer.com with Playwright to read a flight's seat map and create
seat alerts. The bundled `efalert` CLI provides the primitives; YOU act as the
orchestrator: look at the seat-map screenshot, turn the user's plain-English
request into specific seats, show a preview, and only then create the alert.

## One-time setup

Run from this skill's directory:

```bash
bash setup.sh        # creates .venv, installs efalert + Playwright Chromium
```

Credentials (email/password Auth0 logins only — NOT Google sign-in, and MFA
accounts must do the first login headed):

```bash
export EF_EMAIL="you@example.com"
export EF_PASSWORD="…"          # or put both in a .env file (gitignored)
```

Then activate the venv before running commands:

```bash
. .venv/bin/activate
```

> In a TLS-intercepting sandbox (e.g. Claude Code on the web), also
> `export EF_INSECURE_TLS=true`. On a normal machine leave it unset.

## Workflow

1. **Login** (caches a session cookie):
   `python -m efalert login`
2. **Capture the seat map.** Ask the user for the seat-map URL (open the flight
   on expertflyer.com and copy the URL), then:
   `python -m efalert seatmap --url "<URL>" --name flight`
   Read `out/flight.png` (view it) and `out/flight.json` (every seat: label,
   `available`, `state`, `position` = window/aisle/middle, plus a bounding box).
3. **Interpret the request.** Map the user's words ("aisle seat near the front",
   "any premium aisle") to concrete seat labels using `out/flight.json`. Seat
   *type* (premium/exit) is only visible on AVAILABLE seats; for occupied seats
   infer the cabin from row ranges and confirm with the user.
4. **Preview and confirm.** `python -m efalert preview --seats 6C,7C,… --name flight`
   then show `out/preview.png` to the user and get explicit approval.
5. **Create the alert.** Dry-run first (default), review, then submit:
   `python -m efalert create-alert --url "<URL>" --name "My alert" --seats 6C,7C,… [--test-email]`
   Add `--confirm` to actually submit.

## Commands

| Command | Purpose |
|---------|---------|
| `login [--force]` | Authenticate, cache session |
| `seatmap --url U [--name N]` | Screenshot + legend + structured seats |
| `preview --seats … [--name N] [--out P]` | Highlight chosen seats on the map |
| `create-alert --url U --name NAME --seats … [--test-email] [--confirm]` | Fill (and with `--confirm`, submit) a seat alert |
| `delete-alert [--url U] [--confirm]` | Remove an existing alert (frees a plan slot) |
| `dump-dom --url U [--name N]` | Save HTML/screenshot/elements for tuning selectors |

## IMPORTANT — safety

- `create-alert --confirm` and `delete-alert --confirm` **change the user's real
  account** and `--test-email` **sends a real email**. Always run the dry-run /
  preview first and get explicit user confirmation before passing `--confirm`.
- Deleting an alert is **irreversible**. The Free plan allows only **1 active
  alert**; if the limit is reached, `create-alert` reports it. Offer to delete an
  existing alert only with the user's explicit go-ahead, and confirm exactly
  which one.
- The native "Any Aisle/Window/Exit" alert options are paid features; on the
  Free plan select specific seats instead.
- Never write credentials into committed files. `.efstate.json`, `out/`, `.env`
  are gitignored.

## Tuning

If ExpertFlyer changes its markup, all selectors live in
`efalert/selectors.py`. Use `dump-dom` on the relevant page to capture the real
HTML/elements, then adjust. Run `pytest` for the offline unit tests.
