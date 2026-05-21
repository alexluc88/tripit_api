"""Command-line entrypoint: ``tripit <command>`` (or ``python -m tripitcli``).

Read commands emit the API's JSON straight to stdout. Write commands (create /
delete / replace) default to a DRY RUN that prints the payload; pass ``--confirm``
to actually change your TripIt account.
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


def _emit(obj) -> None:
    json.dump(obj, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _client(settings: Settings):
    from .client import TripItClient

    settings.require_consumer()
    tok, sec = settings.require_tokens()
    return TripItClient(settings, token=tok, token_secret=sec)


# -- auth ----------------------------------------------------------------------
def cmd_login(args, settings: Settings) -> int:
    from .auth import complete_login, start_login

    _emit(complete_login(settings) if args.complete else start_login(settings))
    return 0


# -- reads ---------------------------------------------------------------------
def cmd_trips(args, settings: Settings) -> int:
    _emit(_client(settings).list_trips(
        past=args.past, include_objects=args.include_objects,
        page_size=args.page_size, modified_since=args.modified_since,
    ))
    return 0


def cmd_trip(args, settings: Settings) -> int:
    _emit(_client(settings).get_trip(args.id, include_objects=not args.no_objects))
    return 0


def cmd_points(args, settings: Settings) -> int:
    _emit(_client(settings).list_points_programs())
    return 0


def cmd_point(args, settings: Settings) -> int:
    _emit(_client(settings).get_points_program(args.id))
    return 0


def cmd_profile(args, settings: Settings) -> int:
    _emit(_client(settings).get_profile())
    return 0


def cmd_object(args, settings: Settings) -> int:
    _emit(_client(settings).get_object(args.type, args.id))
    return 0


# -- writes (dry-run unless --confirm) -----------------------------------------
def cmd_create_trip(args, settings: Settings) -> int:
    from .xmlbuild import trip_request

    xml = trip_request(args.start, args.end, args.location, args.name)
    if not args.confirm:
        _emit({"dry_run": True, "would_create": xml,
               "hint": "re-run with --confirm to actually create this trip"})
        return 0
    _emit(_client(settings).create(xml))
    return 0


def cmd_create(args, settings: Settings) -> int:
    xml = Path(args.xml).read_text()
    if not args.confirm:
        _emit({"dry_run": True, "would_post_xml": xml,
               "hint": "re-run with --confirm to actually submit"})
        return 0
    _emit(_client(settings).create(xml))
    return 0


def cmd_delete(args, settings: Settings) -> int:
    if not args.confirm:
        _emit({"dry_run": True, "would_delete": {"entity": args.entity, "id": args.id},
               "hint": "re-run with --confirm to actually delete (irreversible)"})
        return 0
    _emit(_client(settings).delete(args.entity, args.id))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tripit", description="TripIt API client for Claude")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("login", help="Authorize via OAuth (run once, then --complete)")
    sp.add_argument("--complete", action="store_true",
                    help="Finish login after clicking Authorize in the browser")
    sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("trips", help="List trips")
    sp.add_argument("--past", action="store_true", help="Past trips instead of upcoming")
    sp.add_argument("--include-objects", action="store_true",
                    help="Inline reservations (flights, lodging, …) for each trip")
    sp.add_argument("--page-size", type=int, help="Limit results per page")
    sp.add_argument("--modified-since", type=int, help="Only trips changed since this timestamp")
    sp.set_defaults(func=cmd_trips)

    sp = sub.add_parser("trip", help="Get one trip by id (objects inlined by default)")
    sp.add_argument("--id", required=True)
    sp.add_argument("--no-objects", action="store_true", help="Skip inlined reservations")
    sp.set_defaults(func=cmd_trip)

    sp = sub.add_parser("points", help="List points / rewards programs (TripIt Pro)")
    sp.set_defaults(func=cmd_points)

    sp = sub.add_parser("point", help="Get one points program by id (TripIt Pro)")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_point)

    sp = sub.add_parser("profile", help="Get your TripIt profile")
    sp.set_defaults(func=cmd_profile)

    sp = sub.add_parser("object", help="Get a single reservation object by type + id")
    sp.add_argument("--type", required=True,
                    help="air, lodging, car, rail, transport, cruise, restaurant, activity, note, map, directions")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_object)

    sp = sub.add_parser("create-trip", help="Create a trip (dry-run unless --confirm)")
    sp.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    sp.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    sp.add_argument("--location", required=True, help="Primary location, e.g. 'Paris, France'")
    sp.add_argument("--name", help="Display name for the trip")
    sp.add_argument("--confirm", action="store_true", help="Actually create it")
    sp.set_defaults(func=cmd_create_trip)

    sp = sub.add_parser("create", help="POST a raw <Request> XML file (dry-run unless --confirm)")
    sp.add_argument("--xml", required=True, help="Path to an XML payload file")
    sp.add_argument("--confirm", action="store_true", help="Actually submit")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("delete", help="Delete an object by entity + id (dry-run unless --confirm)")
    sp.add_argument("--entity", required=True, help="trip, air, lodging, car, …")
    sp.add_argument("--id", required=True)
    sp.add_argument("--confirm", action="store_true", help="Actually delete (irreversible)")
    sp.set_defaults(func=cmd_delete)

    return p


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = build_parser().parse_args(argv)
    settings = Settings()
    return args.func(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
