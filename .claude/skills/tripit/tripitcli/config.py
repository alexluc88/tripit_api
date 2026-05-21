"""Runtime configuration for the TripIt client, loaded from environment variables.

Required for any API call:
  TRIPIT_API_KEY     (a.k.a. consumer key, from tripit.com/developer)
  TRIPIT_API_SECRET  (a.k.a. consumer secret)

After a one-time ``tripit login`` you also get an access token + secret. Cache
them by exporting these (recommended for ephemeral cloud sessions), otherwise
they are read from the gitignored state file:
  TRIPIT_TOKEN
  TRIPIT_TOKEN_SECRET
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

API_BASE = "https://api.tripit.com"
WEB_BASE = "https://www.tripit.com"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _first(*names: str) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


@dataclass
class Settings:
    consumer_key: str | None = field(
        default_factory=lambda: _first("TRIPIT_API_KEY", "TRIPIT_CONSUMER_KEY")
    )
    consumer_secret: str | None = field(
        default_factory=lambda: _first("TRIPIT_API_SECRET", "TRIPIT_CONSUMER_SECRET")
    )
    token: str | None = field(default_factory=lambda: os.getenv("TRIPIT_TOKEN") or None)
    token_secret: str | None = field(
        default_factory=lambda: os.getenv("TRIPIT_TOKEN_SECRET") or None
    )
    api_base: str = field(default_factory=lambda: os.getenv("TRIPIT_API_URL", API_BASE).rstrip("/"))
    web_base: str = field(default_factory=lambda: os.getenv("TRIPIT_WEB_URL", WEB_BASE).rstrip("/"))
    # TripIt shows "Access Request Failed" on /oauth/authorize unless an
    # oauth_callback is supplied (or a URL was registered with the app). For a
    # CLI there is no real redirect target; any valid URL works since OAuth 1.0
    # carries no verifier — the user just lands here after clicking Authorize.
    oauth_callback: str = field(
        default_factory=lambda: os.getenv("TRIPIT_OAUTH_CALLBACK", "https://www.tripit.com/")
    )
    # Enable ONLY behind a TLS-intercepting proxy (e.g. Claude Code on the web).
    insecure_tls: bool = field(default_factory=lambda: _env_bool("TRIPIT_INSECURE_TLS", False))
    timeout: int = field(default_factory=lambda: int(os.getenv("TRIPIT_TIMEOUT", "45")))
    state_file: Path = field(
        default_factory=lambda: Path(
            os.getenv("TRIPIT_STATE_FILE", str(Path.cwd() / ".tripit_state.json"))
        )
    )

    def require_consumer(self) -> None:
        missing = [
            n
            for n, v in (("TRIPIT_API_KEY", self.consumer_key), ("TRIPIT_API_SECRET", self.consumer_secret))
            if not v
        ]
        if missing:
            raise SystemExit(
                "Missing credentials: set "
                + " and ".join(missing)
                + " (env vars or a .env file). Get them by registering an app at "
                "https://www.tripit.com/developer."
            )

    def load_tokens(self) -> tuple[str | None, str | None]:
        """Access token + secret: env vars win, else fall back to the state file."""
        if self.token and self.token_secret:
            return self.token, self.token_secret
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            return data.get("access_token"), data.get("access_token_secret")
        return None, None

    def require_tokens(self) -> tuple[str, str]:
        tok, sec = self.load_tokens()
        if not tok or not sec:
            raise SystemExit(
                "Not authorized yet. Run `tripit login`, open the authorize URL, "
                "click Authorize, then `tripit login --complete`."
            )
        return tok, sec
