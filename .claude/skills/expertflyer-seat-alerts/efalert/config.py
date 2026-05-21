"""Runtime configuration, loaded from environment variables with sane defaults.

All ExpertFlyer-specific knobs live here so the rest of the code stays generic.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# A real desktop Chrome UA is required: ExpertFlyer sits behind a CloudFront WAF
# that 403s the default headless-shell User-Agent. Verified against the live site.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)

BASE_URL = "https://www.expertflyer.com"
# /auth/login 302s to the Auth0 tenant (auth.expertflyer.com) and back to
# /auth/callback once credentials are accepted. Verified.
LOGIN_PATH = "/auth/login"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    email: str | None = os.getenv("EF_EMAIL") or None
    password: str | None = os.getenv("EF_PASSWORD") or None
    base_url: str = os.getenv("EF_BASE_URL", BASE_URL).rstrip("/")
    login_path: str = LOGIN_PATH
    user_agent: str = os.getenv("EF_USER_AGENT", DEFAULT_USER_AGENT)
    headless: bool = _env_bool("EF_HEADLESS", True)
    # Enable only behind a TLS-intercepting proxy (e.g. the cloud sandbox). On a
    # normal machine the cert is valid and this should stay False.
    insecure_tls: bool = _env_bool("EF_INSECURE_TLS", False)
    timeout_ms: int = int(os.getenv("EF_TIMEOUT_MS", "45000"))
    state_file: Path = field(
        default_factory=lambda: Path(
            os.getenv("EF_STATE_FILE", str(Path.cwd() / ".efstate.json"))
        )
    )
    out_dir: Path = field(
        default_factory=lambda: Path(os.getenv("EF_OUT_DIR", str(Path.cwd() / "out")))
    )

    def login_url(self) -> str:
        return f"{self.base_url}{self.login_path}"

    def require_credentials(self) -> None:
        missing = [n for n, v in (("EF_EMAIL", self.email), ("EF_PASSWORD", self.password)) if not v]
        if missing:
            raise SystemExit(
                "Missing credentials: set "
                + " and ".join(missing)
                + " (env vars or a .env). Note: only email/password Auth0 logins "
                "can be automated; Google social login cannot."
            )
