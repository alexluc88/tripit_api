import pytest

from efalert.cli import build_parser


def test_parser_seatmap():
    args = build_parser().parse_args(["seatmap", "--url", "https://x/sm"])
    assert args.command == "seatmap"
    assert args.url == "https://x/sm"
    assert args.name == "seatmap"


def test_parser_create_alert_defaults_to_dry_run():
    args = build_parser().parse_args(
        ["create-alert", "--url", "https://x/sm", "--name", "MyAlert", "--seats", "6C,7C"]
    )
    assert args.confirm is False  # safe default: dry-run unless --confirm
    assert args.seats == "6C,7C"


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_parser_find_flight():
    args = build_parser().parse_args(
        ["find-flight", "--airline", "AS", "--flight", "797", "--date", "2026-05-26"]
    )
    assert args.command == "find-flight"
    assert args.airline == "AS"
    assert args.flight == "797"
    assert args.date == "2026-05-26"
    assert args.from_ is None and args.to is None
    assert args.no_capture is False


def test_parser_candidates_defaults():
    args = build_parser().parse_args(["candidates", "--name", "as797"])
    assert args.command == "candidates"
    assert args.name == "as797"
    assert args.cabin is None
    assert args.top == 4


def test_parser_find_flight_with_route():
    args = build_parser().parse_args(
        ["find-flight", "--airline", "AS", "--flight", "797",
         "--from", "SEA", "--to", "LAX", "--no-capture"]
    )
    assert args.from_ == "SEA"
    assert args.to == "LAX"
    assert args.no_capture is True
