"""Offline checks for CLI parsing + dry-run safety — no network, no credentials."""
import io
import json
from contextlib import redirect_stdout

from tripitcli import cli
from tripitcli.config import Settings


def _run(argv, settings):
    args = cli.build_parser().parse_args(argv)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = args.func(args, settings)
    return rc, json.loads(buf.getvalue())


def test_create_trip_dry_run_does_not_call_api():
    settings = Settings(consumer_key="ck", consumer_secret="cs")
    rc, out = _run(
        ["create-trip", "--start", "2026-06-01", "--end", "2026-06-05",
         "--location", "Paris, France", "--name", "Holiday"],
        settings,
    )
    assert rc == 0
    assert out["dry_run"] is True
    assert "<primary_location>Paris, France</primary_location>" in out["would_create"]


def test_delete_dry_run_does_not_call_api():
    settings = Settings(consumer_key="ck", consumer_secret="cs")
    rc, out = _run(["delete", "--entity", "trip", "--id", "42"], settings)
    assert rc == 0
    assert out["dry_run"] is True
    assert out["would_delete"] == {"entity": "trip", "id": "42"}
