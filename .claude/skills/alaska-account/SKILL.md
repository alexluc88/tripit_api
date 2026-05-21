---
name: alaska-account
description: >-
  Read Alaska Airlines / Atmos Rewards (formerly Mileage Plan) account data via
  browser automation: miles balance, elite status, Wallet balance + stored
  credits/certificates, and recent account activity. Use when the user wants to
  check their Alaska points/miles, Wallet/credits, or status from alaskaair.com.
---

# Alaska / Atmos Rewards account reader

Drives alaskaair.com with **Patchright** (an undetected Playwright fork) to read
the signed-in account pages and emit JSON. It is **read-only** — it never books,
redeems, or changes anything. The bundled `asaccount` CLI provides the
primitives; YOU act as the orchestrator: run a command, read the JSON, and relay
the numbers to the user.

> Why Patchright: alaskaair.com sits behind an Akamai-style "Client Challenge"
> that blocks vanilla Playwright. Patchright clears it far more reliably,
> especially headed (`AS_HEADLESS=false`) with a real Chrome channel.

## One-time setup

Run from this skill's directory:

```bash
bash setup.sh        # creates .venv, installs asaccount + Patchright Chromium
```

Credentials (your own alaskaair.com login):

```bash
export AS_USERNAME="you@example.com"
export AS_PASSWORD="…"          # or put both in a .env file (gitignored)
```

Then activate the venv before running commands:

```bash
. .venv/bin/activate
```

> In a TLS-intercepting sandbox (e.g. Claude Code on the web), also
> `export AS_INSECURE_TLS=true`. On a normal machine leave it unset, and prefer
> `AS_HEADLESS=false AS_BROWSER_CHANNEL=chrome` for the most reliable login.

## 2FA (emailed one-time code)

Alaska emails a one-time code on a new device/profile. The agent can't read your
email, so the first login needs the code from you:

- **Headed (recommended first run):** `AS_HEADLESS=false python -m asaccount login`
  and type the code in the visible window.
- **Headless / unattended:** run `login`; when it prints `2FA REQUIRED` on
  stderr, write the digits to the 2FA file and it continues:
  `echo 123456 > /tmp/as-2fa-code.txt`

The session is cached in the persistent profile dir (`.as-profile/`), so later
runs usually skip both the challenge and 2FA until the cookies expire.

## Workflow

1. **Login** (caches the session):
   `python -m asaccount login`
2. **Read what you need** (each prints JSON to stdout):
   - `python -m asaccount balance`  → `{ "miles", "elite_status" }`
   - `python -m asaccount wallet`   → `{ "wallet_balance", "items": [...] }`
   - `python -m asaccount activity --limit 20`
   - `python -m asaccount account`  → all three at once
3. Relay the numbers to the user. If a field comes back `null`, the selector is
   probably stale — see Tuning.

## Commands

| Command | Purpose |
|---------|---------|
| `login [--force]` | Authenticate, cache the session profile |
| `balance` | Miles balance + elite status |
| `wallet` | Wallet balance + stored credits/certificates |
| `activity [--limit N]` | Recent account activity rows |
| `account [--limit N]` | balance + wallet + activity together |
| `dump-dom --url U [--name N]` | Save HTML/screenshot/elements for tuning selectors |

## IMPORTANT — safety & scope

- Use only the user's **own** Alaska credentials. This automates a login to the
  user's own account; it may run against Alaska's Terms of Service, so keep it to
  personal, read-only use and stop if the user objects.
- Never write credentials into committed files. `.env`, `.as-profile/`, `out/`
  are gitignored. The persistent profile holds live session cookies — treat it
  like a password.
- This skill does not book, redeem, or modify anything. There is no `--confirm`
  destructive path by design.

## Tuning

The account pages are behind login + a bot challenge, so the selectors in
`asaccount/selectors.py` are **best-effort, NEEDS-VERIFICATION** guesses. The
scrapers fall back to scanning page text (so `balance` often resolves anyway),
but if a field is `null`:

1. `python -m asaccount dump-dom --url "https://www.alaskaair.com/account/overview" --name overview`
2. Open `out/overview.png` and `out/overview.elements.json`, find the real
   markup, and fix the matching entry in `selectors.py`.
3. Run `pytest` for the offline parser tests.

Routes can also drift (Mileage Plan → Atmos Rewards). Override without code edits
via `AS_LOGIN_PATH` / `AS_OVERVIEW_PATH` / `AS_WALLET_PATH` / `AS_ACTIVITY_PATH`.
