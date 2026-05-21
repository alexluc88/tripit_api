from asaccount.parse import find_miles, find_status, parse_int, parse_money


def test_parse_int():
    assert parse_int("48,123 miles") == 48123
    assert parse_int(" 1000 ") == 1000
    assert parse_int("no digits") is None
    assert parse_int("") is None
    assert parse_int(None) is None


def test_parse_money():
    assert parse_money("Balance: $125.00") == 125.0
    assert parse_money("$1,250.50 available") == 1250.5
    assert parse_money("$75") == 75.0
    assert parse_money("nothing here") is None


def test_find_miles_prefers_labelled():
    assert find_miles("Your balance is 48,123 miles as of today") == 48123
    assert find_miles("Miles: 12,000") == 12000
    # Falls back when no 'miles' label is present.
    assert find_miles("balance 9,999") is None
    assert find_miles(None) is None


def test_find_status_highest_tier_wins():
    assert find_status("Welcome, MVP Gold 75K member") == "MVP Gold 75K"
    assert find_status("You are MVP Gold 100K") == "MVP Gold 100K"
    assert find_status("Status: MVP") == "MVP"
    # A page mentioning both should report the higher tier.
    assert find_status("MVP Gold and base MVP perks") == "MVP Gold"
    assert find_status("no tier here") is None
