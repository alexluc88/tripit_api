"""Pure text->value helpers for Alaska account data. No browser imports here, so
these stay fully unit-testable offline (the live DOM is behind a login)."""
from __future__ import annotations

import re

# Alaska / Atmos Rewards elite tiers, longest first so "MVP Gold 100K" wins over
# "MVP Gold" / "MVP" when scanning free text.
KNOWN_TIERS = [
    "MVP Gold 100K",
    "MVP Gold 75K",
    "MVP Gold",
    "MVP",
]

_INT_RE = re.compile(r"-?\d[\d,]*")
_MONEY_RE = re.compile(r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)")


def parse_int(text: str | None) -> int | None:
    """First integer in a string, commas allowed: '48,123 miles' -> 48123."""
    if not text:
        return None
    m = _INT_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_money(text: str | None) -> float | None:
    """First dollar amount in a string: 'Balance: $125.00' -> 125.0."""
    if not text:
        return None
    m = _MONEY_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def find_miles(text: str | None) -> int | None:
    """Pull a miles balance out of free page text.

    Prefers a number that sits next to the word 'miles'; falls back to the first
    integer if no labelled match is found.
    """
    if not text:
        return None
    labelled = re.search(r"(\d[\d,]*)\s*miles\b", text, re.IGNORECASE)
    if labelled:
        return parse_int(labelled.group(1))
    nearby = re.search(r"miles?\b[^\d]{0,20}(\d[\d,]*)", text, re.IGNORECASE)
    if nearby:
        return parse_int(nearby.group(1))
    return None


def find_status(text: str | None) -> str | None:
    """Return the highest Alaska/Atmos elite tier mentioned in the text, if any."""
    if not text:
        return None
    for tier in KNOWN_TIERS:
        if re.search(r"\b" + re.escape(tier) + r"\b", text, re.IGNORECASE):
            return tier
    return None
