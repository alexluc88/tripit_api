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


def select_candidates(seats: list[dict], top_k: int = 4) -> dict[str, list[dict]]:
    """Pick up to `top_k` available seats per position, preferring lower rows."""
    out: dict[str, list[dict]] = {p: [] for p in _POSITIONS}
    available = sorted(
        (s for s in seats if s.get("available")),
        key=_row_key,
    )
    for seat in available:
        pos = seat.get("position") or ""
        if pos in out and len(out[pos]) < top_k:
            out[pos].append({
                "label": seat["label"],
                "row": seat["row"],
                "column": seat["column"],
                "position": pos,
            })
    return out


def load_and_select(json_path: Path, top_k: int = 4) -> dict:
    """Read a captured seat-map JSON and return curated candidates + metadata."""
    data = json.loads(Path(json_path).read_text())
    cands = select_candidates(data.get("seats", []), top_k=top_k)
    return {
        "source": str(json_path),
        "url": data.get("url"),
        "summary": data.get("summary", {}),
        "candidates": cands,
    }
