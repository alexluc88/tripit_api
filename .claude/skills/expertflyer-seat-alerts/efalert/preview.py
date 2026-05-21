"""Render a preview image highlighting the seats chosen for an alert.

Works offline from the seatmap.json produced by `capture_seatmap` (each seat
carries its screenshot bounding box), so it is deterministic and unit-testable.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

HIGHLIGHT = (40, 167, 69)      # green outline for the chosen seats
HIGHLIGHT_FILL = (40, 167, 69, 70)
MISSING = (220, 53, 69)        # red for requested seats not found on the map


def _index(seats: list[dict]) -> dict[str, dict]:
    return {s["label"].upper(): s for s in seats}


def render_preview(
    seatmap_json: Path | str,
    chosen: list[str],
    out_path: Path | str,
    pad: int = 3,
) -> dict:
    """Outline `chosen` seats on the captured seat-map screenshot.

    Returns a report of which seats were found vs. missing.
    """
    data = json.loads(Path(seatmap_json).read_text())
    by_label = _index(data["seats"])
    base = Image.open(data["screenshot"]).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    found, missing = [], []
    for label in chosen:
        seat = by_label.get(label.strip().upper())
        if not seat or not seat.get("width"):
            missing.append(label.strip().upper())
            continue
        found.append(seat["label"])
        x0, y0 = seat["x"] - pad, seat["y"] - pad
        x1, y1 = seat["x"] + seat["width"] + pad, seat["y"] + seat["height"] + pad
        draw.rectangle([x0, y0, x1, y1], fill=HIGHLIGHT_FILL, outline=HIGHLIGHT, width=3)

    out = Image.alpha_composite(base, overlay).convert("RGB")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return {"preview": str(out_path), "found": found, "missing": missing}
