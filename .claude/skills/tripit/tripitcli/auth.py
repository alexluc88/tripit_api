"""Three-legged OAuth login dance and token caching.

TripIt's flow (OAuth 1.0, no verifier):
  1. fetch a request token
  2. user opens the authorize URL and clicks Authorize
  3. exchange the request token for a long-lived access token

Step 1 stashes the request token in the state file; step 3 reads it back and
stores the access token.
"""
from __future__ import annotations

import json

from .client import TripItClient
from .config import Settings


def _save(settings: Settings, data: dict) -> None:
    existing = {}
    if settings.state_file.exists():
        existing = json.loads(settings.state_file.read_text())
    existing.update(data)
    settings.state_file.write_text(json.dumps(existing, indent=2))
    settings.state_file.chmod(0o600)


def start_login(settings: Settings) -> dict:
    """Step 1+2: get a request token, return the authorize URL for the user."""
    settings.require_consumer()
    client = TripItClient(settings)
    tok = client.get_request_token()
    if "oauth_token" not in tok:
        raise SystemExit(f"Could not get a request token: {tok}")
    _save(settings, {
        "request_token": tok["oauth_token"],
        "request_token_secret": tok.get("oauth_token_secret", ""),
    })
    authorize_url = (
        f"{settings.web_base}/oauth/authorize?oauth_token={tok['oauth_token']}"
    )
    return {
        "authorize_url": authorize_url,
        "next": "Open authorize_url, click Authorize, then run `tripit login --complete`.",
        "state_file": str(settings.state_file),
    }


def complete_login(settings: Settings) -> dict:
    """Step 3: exchange the stored request token for an access token."""
    settings.require_consumer()
    if not settings.state_file.exists():
        raise SystemExit("No request token found; run `tripit login` first.")
    state = json.loads(settings.state_file.read_text())
    req_tok = state.get("request_token")
    req_sec = state.get("request_token_secret", "")
    if not req_tok:
        raise SystemExit("No request token found; run `tripit login` first.")

    client = TripItClient(settings, token=req_tok, token_secret=req_sec)
    acc = client.get_access_token()
    if "oauth_token" not in acc:
        raise SystemExit(
            f"Access-token exchange failed: {acc}. Did you click Authorize on the URL?"
        )
    _save(settings, {
        "access_token": acc["oauth_token"],
        "access_token_secret": acc.get("oauth_token_secret", ""),
    })
    return {
        "authorized": True,
        "state_file": str(settings.state_file),
        "persist_hint": (
            "To survive ephemeral cloud sessions, export these as env vars: "
            "TRIPIT_TOKEN and TRIPIT_TOKEN_SECRET."
        ),
        "access_token": acc["oauth_token"],
        "access_token_secret": acc.get("oauth_token_secret", ""),
    }
