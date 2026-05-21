"""Runtime configuration, loaded from environment variables with sane defaults.

All Alaska-specific knobs live here so the rest of the code stays generic. The
page paths are overridable because alaskaair.com is mid-rebrand (Mileage Plan ->
Atmos Rewards) and routes shift; a wrong path can be corrected without code edits.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_URL = "https://www.alaskaair.com"
# Account portal routes (NEEDS-VERIFICATION: confirm against the live site and
# override via env if Alaska has moved them).
LOGIN_PATH = "/account/login"
OVERVIEW_PATH = "/account/overview"
WALLET_PATH = "/account/wallet"
ACTIVITY_PATH = "/account/activity"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    username: str | None = os.getenv("AS_USERNAME") or None
    password: str | None = os.getenv("AS_PASSWORD") or None
    base_url: str = os.getenv("AS_BASE_URL", BASE_URL).rstrip("/")
    login_path: str = os.getenv("AS_LOGIN_PATH", LOGIN_PATH)
    overview_path: str = os.getenv("AS_OVERVIEW_PATH", OVERVIEW_PATH)
    wallet_path: str = os.getenv("AS_WALLET_PATH", WALLET_PATH)
    activity_path: str = os.getenv("AS_ACTIVITY_PATH", ACTIVITY_PATH)
    # Patchright runs best with a real Chrome channel + headed; leave channel
    # empty to use the bundled Chromium. On a real machine, "chrome" is stealthier.
    channel: str | None = os.getenv("AS_BROWSER_CHANNEL") or None
    user_agent: str | None = os.getenv("AS_USER_AGENT") or None
    headless: bool = _env_bool("AS_HEADLESS", True)
    # Enable only behind a TLS-intercepting proxy (e.g. the cloud sandbox).
    insecure_tls: bool = _env_bool("AS_INSECURE_TLS", False)
    timeout_ms: int = int(os.getenv("AS_TIMEOUT_MS", "60000"))
    # Persistent browser profile dir (cookies/session live here, like the AA skill's
    # named profiles) so repeat runs skip the login + 2FA dance for a while.
    profile_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("AS_PROFILE_DIR", str(Path.cwd() / ".as-profile"))
        )
    )
    # 2FA handoff: when Alaska emails a code, the script signals "2FA REQUIRED" on
    # stderr and polls this file for the digits (the agent can't read your email).
    two_fa_file: Path = field(
        default_factory=lambda: Path(
            os.getenv("AS_2FA_FILE", "/tmp/as-2fa-code.txt")
        )
    )
    two_fa_wait_ms: int = int(os.getenv("AS_2FA_WAIT_MS", "180000"))
    out_dir: Path = field(
        default_factory=lambda: Path(os.getenv("AS_OUT_DIR", str(Path.cwd() / "out")))
    )

    def login_url(self) -> str:
        return f"{self.base_url}{self.login_path}"

    def overview_url(self) -> str:
        return f"{self.base_url}{self.overview_path}"

    def wallet_url(self) -> str:
        return f"{self.base_url}{self.wallet_path}"

    def activity_url(self) -> str:
        return f"{self.base_url}{self.activity_path}"

    def require_credentials(self) -> None:
        missing = [
            n for n, v in (("AS_USERNAME", self.username), ("AS_PASSWORD", self.password))
            if not v
        ]
        if missing:
            raise SystemExit(
                "Missing credentials: set "
                + " and ".join(missing)
                + " (env vars or a .env). Alaska emails a one-time code on new "
                "devices; supply it via the 2FA file or run headed (AS_HEADLESS=false)."
            )
