"""Pure seat-data helpers: parsing labels and classifying position from geometry.

Kept free of Playwright so it can be unit-tested without a browser.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

SEAT_LABEL_RE = re.compile(r"^(\d{1,3})\s*([A-HJ-Z])$")  # airlines skip "I"

# A within-row horizontal gap wider than (typical gap * this) is read as an aisle.
# Real ExpertFlyer 3-3 maps show an aisle/seat spacing ratio around 1.4.
AISLE_GAP_RATIO = 1.3


@dataclass
class Seat:
    label: str          # e.g. "12A"
    row: int            # 12
    column: str         # "A"
    available: bool
    state: str = ""     # raw state from the page, e.g. available/occupied/blocked
    position: str = ""  # window | middle | aisle (filled by classify_positions)
    # Bounding box in screenshot pixels, used for offline preview rendering.
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2

    def to_dict(self) -> dict:
        return asdict(self)


def parse_label(text: str) -> tuple[int, str] | None:
    """Return (row, column) for a seat label like '12A', else None."""
    if not text:
        return None
    m = SEAT_LABEL_RE.match(text.strip().upper())
    if not m:
        return None
    return int(m.group(1)), m.group(2)


def _group_into_rows(seats: list[Seat], tol_ratio: float = 0.5) -> list[list[Seat]]:
    """Cluster seats into rows by y-centre. Falls back to the row number when no
    geometry is present (all heights zero)."""
    if not seats:
        return []
    if all(s.height == 0 for s in seats):
        rows: dict[int, list[Seat]] = {}
        for s in seats:
            rows.setdefault(s.row, []).append(s)
        return [rows[k] for k in sorted(rows)]

    median_h = sorted(s.height for s in seats)[len(seats) // 2] or 1.0
    tol = median_h * tol_ratio
    out: list[list[Seat]] = []
    for s in sorted(seats, key=lambda s: s.cy):
        if out and abs(s.cy - out[-1][0].cy) <= tol:
            out[-1].append(s)
        else:
            out.append([s])
    return out


def classify_positions(seats: list[Seat]) -> list[Seat]:
    """Tag each seat window/middle/aisle using horizontal gaps within its row.

    A gap noticeably wider than the typical seat-to-seat spacing is an aisle;
    seats touching an aisle (or the row ends) are 'aisle'/'window' respectively.
    When geometry is absent, falls back to a letter-only heuristic.
    """
    rows = _group_into_rows(seats)
    for row in rows:
        row.sort(key=lambda s: (s.x, s.column))
        if len(row) == 1:
            row[0].position = "window"
            continue

        have_geometry = any(s.width for s in row)
        if have_geometry:
            centres = [s.cx for s in row]
            gaps = [centres[i + 1] - centres[i] for i in range(len(centres) - 1)]
            typical = sorted(gaps)[len(gaps) // 2] or 1.0
            aisle_after = {i for i, g in enumerate(gaps) if g > typical * AISLE_GAP_RATIO}
        else:
            # No geometry: assume a single aisle in the middle of the row.
            aisle_after = {len(row) // 2 - 1}

        for i, seat in enumerate(row):
            if i == 0 or i == len(row) - 1:
                seat.position = "window"
            elif (i - 1) in aisle_after or i in aisle_after:
                seat.position = "aisle"
            else:
                seat.position = "middle"
        # Window seats that also border an aisle stay 'window'; ends win.
    return seats


def summarize(seats: list[Seat]) -> dict:
    avail = [s for s in seats if s.available]
    by_pos: dict[str, int] = {}
    for s in avail:
        by_pos[s.position or "?"] = by_pos.get(s.position or "?", 0) + 1
    return {
        "total": len(seats),
        "available": len(avail),
        "available_by_position": by_pos,
    }
