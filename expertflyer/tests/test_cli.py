import pytest

from efalert.cli import build_parser


def test_parser_seatmap():
    args = build_parser().parse_args(["seatmap", "--url", "https://x/sm"])
    assert args.command == "seatmap"
    assert args.url == "https://x/sm"
    assert args.name == "seatmap"


def test_parser_create_alert_defaults_to_dry_run():
    args = build_parser().parse_args(
        ["create-alert", "--url", "https://x/a", "--airline", "UA",
         "--flight", "837", "--date", "2026-06-01"]
    )
    assert args.confirm is False  # safe default: dry-run unless --confirm


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
