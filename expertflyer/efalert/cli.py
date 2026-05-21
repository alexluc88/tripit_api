"""Command-line entrypoint: `efalert <command>` (or `python -m efalert`).

Commands are thin primitives. The natural-language step ("aisle seat near the
front") is meant to happen in the calling agent/conversation: run `seatmap`,
read the screenshot + seats.json, pick labels, `preview` them, then `create-alert`.
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
        _emit({"authenticated": ok, "state_file": str(settings.state_file)})
    return 0 if ok else 1


def cmd_seatmap(args, settings: Settings) -> int:
    from .auth import login
    from .browser import open_session
    from .seatmap import capture_seatmap

    with open_session(settings) as session:
        login(session)
        data = capture_seatmap(session, args.url, settings.out_dir, name=args.name)
    _emit({k: data[k] for k in ("url", "screenshot", "legend", "summary")}
          | {"seats_json": str(settings.out_dir / f"{args.name}.json"),
             "seat_count": len(data["seats"])})
    return 0


def cmd_preview(args, settings: Settings) -> int:
    from .preview import render_preview

    seatmap_json = args.seatmap or (settings.out_dir / f"{args.name}.json")
    out = args.out or (settings.out_dir / "preview.png")
    report = render_preview(seatmap_json, args.seats.split(","), out)
    _emit(report)
    return 0 if not report["missing"] else 2


def cmd_create_alert(args, settings: Settings) -> int:
    from .auth import login
    from .browser import open_session
    from .alert import AlertRequest, create_alert

    req = AlertRequest(
        name=args.name,
        seats=args.seats.split(",") if args.seats else [],
    )
    with open_session(settings) as session:
        login(session)
        result = create_alert(session, args.url, req, settings.out_dir,
                              dry_run=not args.confirm)
    _emit(result)
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
            "input,button,select,textarea,a[href],[class*='seat' i],[class*='legend' i]",
            """els => els.slice(0,400).map(e => ({
                tag:e.tagName.toLowerCase(), type:e.getAttribute('type'),
                id:e.id||null, name:e.getAttribute('name'),
                cls:(e.className&&e.className.toString?e.className.toString():'')||null,
                aria:e.getAttribute('aria-label'), text:(e.innerText||'').trim().slice(0,40)||null,
            }))""",
        )
        (settings.out_dir / f"{args.name}.elements.json").write_text(json.dumps(elements, indent=2))
    _emit({"saved": [f"{args.name}.html", f"{args.name}.png", f"{args.name}.elements.json"],
           "out_dir": str(settings.out_dir)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="efalert", description="ExpertFlyer seat-alert automation")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("login", help="Authenticate and save the session")
    sp.add_argument("--force", action="store_true", help="Re-login even if a session exists")
    sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("seatmap", help="Capture a seat map (screenshot + legend + seats)")
    sp.add_argument("--url", required=True, help="Seat-map page URL (copy from ExpertFlyer)")
    sp.add_argument("--name", default="seatmap", help="Output basename")
    sp.set_defaults(func=cmd_seatmap)

    sp = sub.add_parser("preview", help="Highlight chosen seats on a captured map")
    sp.add_argument("--seats", required=True, help="Comma-separated seats, e.g. 12A,12C")
    sp.add_argument("--seatmap", help="Path to seatmap.json (defaults to out/<name>.json)")
    sp.add_argument("--name", default="seatmap", help="Basename of the seatmap capture")
    sp.add_argument("--out", help="Output preview image path")
    sp.set_defaults(func=cmd_preview)

    sp = sub.add_parser("create-alert",
                        help="Select seats on a seat map + name an alert (optionally submit)")
    sp.add_argument("--url", required=True, help="Seat-map page URL (alerts are created there)")
    sp.add_argument("--name", required=True, help="Alert name (required by ExpertFlyer)")
    sp.add_argument("--seats", required=True, help="Comma-separated seats to watch, e.g. 6C,7C")
    sp.add_argument("--confirm", action="store_true",
                    help="Actually submit (default is a dry-run that selects + screenshots)")
    sp.set_defaults(func=cmd_create_alert)

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
