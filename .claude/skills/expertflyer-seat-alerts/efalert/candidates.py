"""Curate candidate seats from a captured seat map for in-chat selection UIs.

The output is shaped for `AskUserQuestion`: a small, ordered list per position
(window/aisle/middle), capped so the agent can render it as 2-4 chat options.
Forward-row seats are preferred since they're typically the better pick.
"""
from __future__ import annotations

import json
from pathlib import Path

_POSITIONS = ("window", "aisle", "middle")


def _row_key(seat: dict) -> tuple[int, str]:
    return (int(seat.get("row", 9999)), seat.get("column", "Z"))


def filter_seats(
    seats: list[dict],
    *,
    positions: tuple[str, ...] | None = None,
    seat_types: tuple[str, ...] | None = None,
    only_available: bool = True,
) -> list[dict]:
    """Return seats matching every supplied filter, sorted forward-to-back.

    `positions` / `seat_types`: if None, no filter on that axis.
    `only_available`: when False, occupied/blocked seats are kept too — useful
    for enumerating alert targets (you watch seats that are currently taken).
    """
    out = []
    for s in seats:
        if only_available and not s.get("available"):
            continue
        if positions and (s.get("position") or "") not in positions:
            continue
        if seat_types and (s.get("seat_type") or "standard") not in seat_types:
            continue
        out.append(s)
    out.sort(key=_row_key)
    return out


def select_candidates(seats: list[dict], top_k: int = 4) -> dict[str, list[dict]]:
    """Pick up to `top_k` available seats per position, preferring lower rows."""
    out: dict[str, list[dict]] = {p: [] for p in _POSITIONS}
    for seat in filter_seats(seats, only_available=True):
        pos = seat.get("position") or ""
        if pos in out and len(out[pos]) < top_k:
            out[pos].append({
                "label": seat["label"],
                "row": seat["row"],
                "column": seat["column"],
                "position": pos,
            })
    return out


def load_and_select(
    json_path: Path,
    top_k: int = 4,
    *,
    positions: tuple[str, ...] | None = None,
    seat_types: tuple[str, ...] | None = None,
    only_available: bool = True,
) -> dict:
    """Read a captured seat-map JSON and return curated candidates + filtered list."""
    data = json.loads(Path(json_path).read_text())
    seats = data.get("seats", [])
    cands = select_candidates(seats, top_k=top_k)
    matches = filter_seats(
        seats, positions=positions, seat_types=seat_types,
        only_available=only_available,
    )
    return {
        "source": str(json_path),
        "url": data.get("url"),
        "summary": data.get("summary", {}),
        "candidates": cands,
        "matches": [
            {"label": s["label"], "row": s["row"], "column": s["column"],
             "position": s.get("position", ""), "seat_type": s.get("seat_type", ""),
             "available": s.get("available", False)}
            for s in matches
        ],
    }
