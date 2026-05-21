# alaska-booking — initial setup tooling

Local tooling for the one-time traveler scrape described in `SKILL.md`
("Initial setup: scraping traveler accounts").

## Why you run this locally, not in a Claude Code web sandbox

The scrape reads your **signed-in** alaskaair.com pages. Logging in needs your
password, and a real airline site will throw 2FA and a CAPTCHA at a datacenter
IP. That login is interactive **by design** — Claude never handles your
credentials. So the login + first scrape happen on **your own machine**; after
that, future bookings just read `travelers/<name>.yaml`.

## Setup

```bash
cd .claude/skills/alaska-booking
npm install
npx playwright install chromium
```

## 1. One-time login per traveler

```bash
node save_session.js alex
```

A real browser opens. Log in by hand (password, CAPTCHA, 2FA), land on your
account dashboard, then press Enter in the terminal. Saves
`storage-state-alex.json` (live auth cookies — **gitignored, keep private**).

## 2. Scrape the profile

```bash
node scrape_alaska_account.js alex          # add --show to watch / re-auth
```

Writes `travelers/alex.yaml` with: name, DOB, Mileage Plan number + tier, KTN,
Global Entry / Redress, seat preference, saved travelers, Companion Fare status,
and saved cards as **brand + last-4 only**.

### First run is a tuning pass

The page URLs and selectors in `scrape_alaska_account.js` are **best-effort** —
they were written without access to a live signed-in DOM. Every run also dumps a
screenshot + raw HTML per page into `out/`, and prints the fields it could not
find. Open the `out/*.html` files, fix the entries in the `PAGES` and
`SELECTORS` maps at the top of the script, and re-run until `_meta.needs_review`
in the YAML is empty.

## Sensitive data — do NOT put these here

Passport numbers and full card numbers are intentionally never scraped or
written to `travelers/*.yaml`. Keep them in a separate encrypted file or a
password manager. Never paste them into chat.

## What's gitignored

`storage-state-*.json`, `travelers/*.yaml`, `out/`, `secrets/`, `*.enc`, `.env`,
`node_modules/`. Only the scripts, this README, and `package.json` are committed.
