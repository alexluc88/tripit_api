"""Render a preview image highlighting the seats chosen for an alert.

Works offline from the seatmap.json produced by `capture_seatmap` (each seat
carries its screenshot bounding box), so it is deterministic and unit-testable.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HIGHLIGHT = (40, 167, 69)      # green outline for the chosen seats
HIGHLIGHT_FILL = (40, 167, 69, 70)
MISSING = (220, 53, 69)        # red for requested seats not found on the map
# Picker uses bright green = "available, go pick this".
AVAILABLE = (34, 139, 60)
AVAILABLE_FILL = (34, 139, 60, 240)
# Whole-canvas translucent white wash dims the rest of the map so the green
# tiles read instantly. Tuned to keep occupied-seat shapes visible underneath.
DIM_WASH = (255, 255, 255, 110)


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


def _load_font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_picker(seatmap_json: Path | str, out_path: Path | str,
                   pad: int = 6, scale: int = 3) -> dict:
    """Annotate every available seat on the captured map with an outline + label,
    cropped to the seat-grid region and upscaled so labels are easy to read.
    """
    data = json.loads(Path(seatmap_json).read_text())
    base = Image.open(data["screenshot"]).convert("RGBA")
    all_seats = [s for s in data["seats"] if s.get("width")]
    available = [s for s in all_seats if s.get("available")]
    if not all_seats:
        raise RuntimeError("No seats with geometry to annotate.")

    # Crop tightly around the seat grid (all seats, not just available), with
    # extra room below for labels.
    margin = 40
    label_room = 28
    x_min = max(0, min(s["x"] for s in all_seats) - margin)
    y_min = max(0, min(s["y"] for s in all_seats) - margin)
    x_max = min(base.width, max(s["x"] + s["width"] for s in all_seats) + margin)
    y_max = min(base.height,
                max(s["y"] + s["height"] for s in all_seats) + margin + label_room)
    cropped = base.crop((x_min, y_min, x_max, y_max))

    # Upscale so seat labels remain legible after the chat client resizes.
    if scale != 1:
        cropped = cropped.resize(
            (cropped.width * scale, cropped.height * scale),
            resample=Image.LANCZOS,
        )
    # First wash the whole crop to dim the occupied seats, then drop opaque
    # green tiles on top of the available ones — they read as the only "live"
    # elements on the canvas.
    overlay = Image.new("RGBA", cropped.size, DIM_WASH)
    draw = ImageDraw.Draw(overlay)

    sample_h = sorted(s["height"] for s in available or all_seats)[
        len(available or all_seats) // 2
    ]
    # Size labels to fit inside a seat box (longest label is 3 chars like "30F").
    font = _load_font(max(10, int(sample_h * 0.5 * scale)))

    for seat in available:
        sx = (seat["x"] - x_min) * scale
        sy = (seat["y"] - y_min) * scale
        sw = seat["width"] * scale
        sh = seat["height"] * scale
        x0, y0 = sx - pad, sy - pad
        x1, y1 = sx + sw + pad, sy + sh + pad
        draw.rectangle([x0, y0, x1, y1], fill=AVAILABLE_FILL, outline=AVAILABLE,
                       width=max(2, scale))
        label = seat["label"]
        tb = draw.textbbox((0, 0), label, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        lx = sx + (sw - tw) / 2
        ly = sy + (sh - th) / 2 - 2  # small upward nudge for vertical centering
        draw.text((lx, ly), label, font=font, fill=(255, 255, 255))

    out = Image.alpha_composite(cropped, overlay).convert("RGB")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return {
        "picker": str(out_path),
        "count": len(available),
        "labels": [s["label"] for s in available],
    }
