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
2. **Capture the seat map.** Two ways in:
   - **By flight number** (preferred):
     `python -m efalert find-flight --airline AS --flight 797 [--date 2026-05-26] [--from SEA --to LAX] --name flight`
     Resolves the route (Alaska supported automatically; for others pass
     `--from`/`--to`), drives EF's seat-map form, dedups cabins, and writes
     `out/flight_<cabin>.{png,json}` for each cabin found (`D`/`F` = First,
     `C`/`J` = Business, `W` = Premium Economy, `Y` = Economy).
   - **By URL** (when you already have the EF seat-map link):
     `python -m efalert seatmap --url "<URL>" --name flight`
   Read `out/flight*.png` (view it) and `out/flight*.json` (every seat: label,
   `available`, `state`, `position` = window/aisle/middle, plus a bounding box).
3. **Show the user a picker.** Run
   `python -m efalert picker --name flight_<cabin> --out out/<cabin>_picker.png`
   for each cabin captured. The output is a cropped, upscaled snapshot of the
   website's own seat layout with every available seat filled blue and labeled
   in white — the closest chat-native equivalent of EF's clickable seat map.
   `SendUserFile` the image(s).
4. **Collect the selection.** Either ask the user to reply with the seat labels
   they want, or use `AskUserQuestion` with `multiSelect: true` if a short list
   of curated options helps (use `efalert candidates --name flight` to get the
   top picks per position). Free-text reply is usually faster when the picker
   is already on screen.
5. **Preview and confirm.** `python -m efalert preview --seats 6C,7C,… --name flight`
   then show `out/preview.png` to the user and get explicit approval.
6. **Create the alert.** Dry-run first (default), review, then submit:
   `python -m efalert create-alert --url "<URL>" --name "My alert" --seats 6C,7C,… [--test-email]`
   Add `--confirm` to actually submit. Use the URL from
   `find-flight`'s output for the cabin the chosen seats belong to.

## Commands

| Command | Purpose |
|---------|---------|
| `login [--force]` | Authenticate, cache session |
| `find-flight --airline X --flight N [--date YYYY-MM-DD] [--from/--to] [--name N] [--no-capture]` | Resolve a flight to seat-map URL(s) and capture each cabin |
| `seatmap --url U [--name N]` | Screenshot + legend + structured seats |
| `candidates --name N [--cabin C] [--top K]` | Top available seats per position, shaped for an `AskUserQuestion` UI |
| `picker --name N [--out P]` | Cropped, labeled seat map showing every available seat — the chat-native picker |
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

## Future work

- `find-flight` route lookup is implemented for Alaska Airlines (AS) only.
  Other carriers require `--from`/`--to`. Add carrier-specific scrapers to
  `efalert/find_flight.py::lookup_route` as needed.
- A `--pnr ABC123` mode to pull route + date from a booking reference would
  remove the last manual step.
