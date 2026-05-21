---
name: tripit
description: >-
  Read and edit a user's TripIt travel data via the TripIt API. Use when the
  user wants to see their upcoming or past trips, flight/hotel/car reservation
  details, frequent-flyer / rewards point balances (TripIt Pro), or their TripIt
  profile — or to create or delete a trip/reservation on their TripIt account.
---

# TripIt

A small OAuth-signed client (`tripit` CLI) over the [TripIt API](https://tripit.github.io/api/doc/v1/).
Reads return JSON; YOU act as the orchestrator — pull the data, then summarize or
answer the user's question. Writes change the user's real account and default to a
dry run.

## One-time setup

Run from this skill's directory:

```bash
bash setup.sh        # creates .venv and installs tripitcli
```

Credentials — register an app at https://www.tripit.com/developer for an API
Key + Secret (the "Pull Data" card shows API Key = consumer key, API Secret =
consumer secret):

```bash
export TRIPIT_API_KEY="…"
export TRIPIT_API_SECRET="…"     # or put both in a .env file (gitignored)
. .venv/bin/activate
```

> In a TLS-intercepting sandbox (e.g. Claude Code on the web), also
> `export TRIPIT_INSECURE_TLS=true`. On a normal machine leave it unset.

## Authorize (three-legged OAuth, once)

```bash
python -m tripitcli login              # prints an authorize_url
# open authorize_url in a browser, click Authorize, then:
python -m tripitcli login --complete   # caches the access token
```

The access token is written to the gitignored `.tripit_state.json`. Because cloud
containers are ephemeral, persist it by exporting the `access_token` /
`access_token_secret` it prints as `TRIPIT_TOKEN` and `TRIPIT_TOKEN_SECRET`.

## Workflow

1. **Read** the data the user asked about (`trips`, `trip --id`, `points`,
   `profile`, …). Output is JSON on stdout.
2. **Interpret** it and answer in plain language; cite trip names, dates,
   confirmation numbers, point balances, etc.
3. **For edits**, build the request, show the user the **dry run** output, get
   explicit approval, then re-run with `--confirm`.

## Commands

| Command | Purpose |
|---------|---------|
| `login [--complete]` | OAuth authorize (step 1, then step 2 after clicking Authorize) |
| `trips [--past] [--include-objects] [--page-size N]` | List upcoming (or past) trips |
| `trip --id ID [--no-objects]` | One trip, reservations inlined by default |
| `points` / `point --id ID` | Points / rewards programs (TripIt Pro only) |
| `profile` | Your TripIt profile |
| `object --type air\|lodging\|car\|… --id ID` | A single reservation object |
| `create-trip --start --end --location [--name] [--confirm]` | Create a trip |
| `create --xml FILE [--confirm]` | POST a raw `<Request>` XML payload |
| `delete --entity trip\|air\|… --id ID [--confirm]` | Delete an object |

## IMPORTANT — safety

- `create`, `create-trip`, `delete`, and `replace` **change the user's real
  TripIt account**. They run as a **dry run** by default (printing the payload);
  only pass `--confirm` after showing the user and getting explicit approval.
- `delete --confirm` is **irreversible**.
- **Points/rewards** (`points`, `point`) require **TripIt Pro**; on a free account
  these return no program data.
- Never write credentials into committed files. `.env` and `.tripit_state.json`
  are gitignored.

## Tuning

The whole API surface lives in `tripitcli/client.py`; OAuth signing in
`tripitcli/oauth.py`. Run `pytest` for the offline unit tests (signing, payload
encoding, dry-run behavior — no network or credentials needed).
