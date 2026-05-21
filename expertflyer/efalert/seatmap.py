"""Capture a flight's seat map: screenshot, legend, and structured seat data.

The extractor is intentionally markup-agnostic. It scans the page for elements
whose visible label looks like a seat ("12A") and reads availability from the
element's class / aria-label / title text. This survives most cosmetic markup
changes; tune SEAT_*_TOKENS and SEATMAP selectors in selectors.py if needed.
"""
from __future__ import annotations

import json
from pathlib import Path

from .browser import Session
from . import selectors
from .seats import Seat, classify_positions, parse_label, summarize

# JS runs in the page: collect seat-like elements with geometry + state hints.
_EXTRACT_JS = r"""
() => {
  const scX = window.scrollX, scY = window.scrollY;
  const labelRe = /^\d{1,3}\s*[A-HJ-Z]$/;
  const out = [];
  const seen = new Set();
  for (const el of document.querySelectorAll('*')) {
    if (el.children.length > 2) continue;          // want leaf-ish cells
    const txt = (el.textContent || '').trim();
    const aria = el.getAttribute('aria-label') || '';
    const title = el.getAttribute('title') || '';
    let label = '';
    if (labelRe.test(txt)) label = txt;
    else {
      const m = (aria + ' ' + title).match(/\b(\d{1,3}\s*[A-HJ-Z])\b/);
      if (m) label = m[1];
    }
    if (!label) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const key = label.replace(/\s+/g, '') + '@' + Math.round(r.left) + ',' + Math.round(r.top);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      label: label.replace(/\s+/g, ''),
      cls: (el.className && el.className.toString ? el.className.toString() : '') + ' ' + aria + ' ' + title,
      x: r.left + scX, y: r.top + scY, width: r.width, height: r.height,
    });
  }
  return out;
}
"""

_LEGEND_JS = r"""
(rootSel) => {
  const root = document.querySelector(rootSel);
  if (!root) return [];
  const items = root.querySelectorAll('li, [class*="item" i], tr, span, div');
  const seen = new Set(); const out = [];
  for (const el of items) {
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ');
    if (t && t.length < 60 && !seen.has(t)) { seen.add(t); out.push(t); }
  }
  return out.slice(0, 30);
}
"""


def _availability(cls: str) -> bool:
    low = cls.lower()
    if any(tok in low for tok in selectors.SEAT_UNAVAILABLE_TOKENS):
        return False
    if any(tok in low for tok in selectors.SEAT_AVAILABLE_TOKENS):
        return True
    return False  # unknown = treat as not available (conservative for alerts)


def capture_seatmap(session: Session, url: str, out_dir: Path, name: str = "seatmap") -> dict:
    """Navigate to a seat-map URL and capture screenshot + legend + seats."""
    page = session.page
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(2500)

    raw = page.evaluate(_EXTRACT_JS)
    seats: list[Seat] = []
    for r in raw:
        parsed = parse_label(r["label"])
        if not parsed:
            continue
        row, col = parsed
        seats.append(Seat(
            label=r["label"], row=row, column=col,
            available=_availability(r["cls"]),
            x=r["x"], y=r["y"], width=r["width"], height=r["height"],
        ))
    classify_positions(seats)

    legend: list[str] = []
    try:
        legend = page.evaluate(_LEGEND_JS, selectors.SEATMAP["legend_root"])
    except Exception:
        pass

    shot = out_dir / f"{name}.png"
    page.screenshot(path=str(shot), full_page=True)

    seats_sorted = sorted(seats, key=lambda s: (s.row, s.column))
    data = {
        "url": url,
        "screenshot": str(shot),
        "legend": legend,
        "seats": [s.to_dict() for s in seats_sorted],
        "summary": summarize(seats_sorted),
    }
    (out_dir / f"{name}.json").write_text(json.dumps(data, indent=2))
    return data
