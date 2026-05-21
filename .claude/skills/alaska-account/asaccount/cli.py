"""Command-line entrypoint: `asaccount <command>` (or `python -m asaccount`).

Read-only commands that log into alaskaair.com and emit JSON: `balance`,
`wallet`, `activity`, and `account` (all three). `login` just caches a session;
`dump-dom` saves a page's HTML/screenshot/elements for tuning selectors.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .config import Settings


def _load_dotenv() -> None:
    """Minimal .env loader (KEY=VALUE per line) so we avoid an extra dependency."""
    env = Path.cwd() / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _emit(obj: dict) -> None:
    json.dump(obj, sys.stdout, indent=2)
    sys.stdout.write("\n")


def cmd_login(args, settings: Settings) -> int:
    from .auth import login
    from .browser import open_session

    with open_session(settings) as session:
        ok = login(session, force=args.force)
        _emit({"authenticated": ok, "engine": session.engine,
               "profile_dir": str(settings.profile_dir)})
    return 0 if ok else 1


def cmd_balance(args, settings: Settings) -> int:
    from .auth import login
    from .browser import open_session
    from .account import get_balance

    with open_session(settings) as session:
        login(session)
        _emit(get_balance(session))
    return 0


def cmd_wallet(args, settings: Settings) -> int:
    from .auth import login
    from .browser import open_session
    from .account import get_wallet

    with open_session(settings) as session:
        login(session)
        _emit(get_wallet(session))
    return 0


def cmd_activity(args, settings: Settings) -> int:
    from .auth import login
    from .browser import open_session
    from .account import get_activity

    with open_session(settings) as session:
        login(session)
        _emit(get_activity(session, limit=args.limit))
    return 0


def cmd_account(args, settings: Settings) -> int:
    from .auth import login
    from .browser import open_session
    from .account import get_balance, get_wallet, get_activity

    with open_session(settings) as session:
        login(session)
        _emit({
            "balance": get_balance(session),
            "wallet": get_wallet(session),
            "activity": get_activity(session, limit=args.limit),
        })
    return 0


def cmd_dump_dom(args, settings: Settings) -> int:
    """Save HTML + screenshot + interactive-element inventory for selector tuning."""
    from .auth import login
    from .browser import open_session

    settings.out_dir.mkdir(parents=True, exist_ok=True)
    with open_session(settings) as session:
        login(session)
        page = session.page
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_timeout(2500)
        (settings.out_dir / f"{args.name}.html").write_text(page.content())
        page.screenshot(path=str(settings.out_dir / f"{args.name}.png"), full_page=True)
        elements = page.eval_on_selector_all(
            "input,button,select,a[href],[data-testid],[class*='miles' i],"
            "[class*='balance' i],[class*='wallet' i],[class*='tier' i]",
            """els => els.slice(0,400).map(e => ({
                tag:e.tagName.toLowerCase(), type:e.getAttribute('type'),
                id:e.id||null, name:e.getAttribute('name'),
                testid:e.getAttribute('data-testid'),
                cls:(e.className&&e.className.toString?e.className.toString():'')||null,
                aria:e.getAttribute('aria-label'),
                text:(e.innerText||'').trim().slice(0,40)||null,
            }))""",
        )
        (settings.out_dir / f"{args.name}.elements.json").write_text(
            json.dumps(elements, indent=2)
        )
    _emit({"saved": [f"{args.name}.html", f"{args.name}.png", f"{args.name}.elements.json"],
           "out_dir": str(settings.out_dir)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="asaccount",
        description="Read-only Alaska / Atmos Rewards account scraper (browser-driven)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("login", help="Authenticate and cache the session")
    sp.add_argument("--force", action="store_true", help="Re-login even if a session exists")
    sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("balance", help="Miles balance + elite status")
    sp.set_defaults(func=cmd_balance)

    sp = sub.add_parser("wallet", help="Wallet balance + stored credits/certificates")
    sp.set_defaults(func=cmd_wallet)

    sp = sub.add_parser("activity", help="Recent account activity")
    sp.add_argument("--limit", type=int, default=20, help="Max rows to return")
    sp.set_defaults(func=cmd_activity)

    sp = sub.add_parser("account", help="Everything: balance + wallet + activity")
    sp.add_argument("--limit", type=int, default=20, help="Max activity rows")
    sp.set_defaults(func=cmd_account)

    sp = sub.add_parser("dump-dom", help="Save HTML/screenshot/elements of a page for tuning")
    sp.add_argument("--url", required=True)
    sp.add_argument("--name", default="dump")
    sp.set_defaults(func=cmd_dump_dom)
    return p


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = build_parser().parse_args(argv)
    settings = Settings()
    return args.func(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
