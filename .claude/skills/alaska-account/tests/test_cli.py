import pytest

from asaccount.cli import build_parser


def test_parser_balance():
    args = build_parser().parse_args(["balance"])
    assert args.command == "balance"


def test_parser_activity_limit_default():
    args = build_parser().parse_args(["activity"])
    assert args.limit == 20
    args = build_parser().parse_args(["activity", "--limit", "5"])
    assert args.limit == 5


def test_parser_login_force_defaults_false():
    args = build_parser().parse_args(["login"])
    assert args.force is False


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
