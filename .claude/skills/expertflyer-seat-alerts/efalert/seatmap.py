"""Capture a flight's seat map: screenshot, legend, and structured seat data.

Each ExpertFlyer seat is a `<button data-seat-id="6A" aria-label="Seat 6A,
occupied">`. The extractor reads the label from data-seat-id and the state from
the aria-label, capturing each seat's bounding box for offline preview. If
data-seat-id is missing (alternate markup) it falls back to a label-regex scan.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .browser import Session
from . import selectors
from .seats import Seat, classify_positions, parse_label, summarize

# Runs in the page. Prefers exact data-seat-id buttons; falls back to a scan.
_EXTRACT_JS = r"""
() => {
  const scX = window.scrollX, scY = window.scrollY;
  const stateOf = (aria) => (aria && aria.includes(','))
      ? aria.split(',').pop().trim().toLowerCase() : '';
  const iconOf = (el) => {
    const svg = el.querySelector('svg');
    if (!svg) return '';
    const cls = Array.from(svg.classList).find(c => c.startsWith('lucide-'));
    return cls ? cls.replace('lucide-', '') : '';
  };
  const buttons = document.querySelectorAll('button[data-seat-id], [data-seat-id]');
  const out = [];
  if (buttons.length) {
    for (const el of buttons) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      const aria = el.getAttribute('aria-label') || '';
      const cls = (el.className && el.className.toString)
        ? el.className.toString() : (el.className || '');
      out.push({
        label: (el.getAttribute('data-seat-id') || '').toUpperCase().replace(/\s+/g, ''),
        state: stateOf(aria), aria, cls, icon: iconOf(el),
        x: r.left + scX, y: r.top + scY, width: r.width, height: r.height,
      });
    }
    return { mode: 'data-seat-id', seats: out };
  }
  const labelRe = /^\d{1,3}\s*[A-HJ-Z]$/;
  const seen = new Set();
  for (const el of document.querySelectorAll('*')) {
    if (el.children.length > 2) continue;
    const txt = (el.textContent || '').trim();
    const aria = el.getAttribute('aria-label') || '';
    const title = el.getAttribute('title') || '';
    let label = '';
    if (labelRe.test(txt)) label = txt;
    else { const m = (aria + ' ' + title).match(/\b(\d{1,3}\s*[A-HJ-Z])\b/); if (m) label = m[1]; }
    if (!label) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const key = label.replace(/\s+/g, '') + '@' + Math.round(r.left) + ',' + Math.round(r.top);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      label: label.replace(/\s+/g, '').toUpperCase(), state: stateOf(aria),
      aria: aria + ' ' + title,
      x: r.left + scX, y: r.top + scY, width: r.width, height: r.height,
    });
  }
  return { mode: 'scan', seats: out };
}
"""

_LEGEND_JS = r"""
(rootSel) => {
  const root = document.querySelector(rootSel);
  if (!root) return [];
  const out = []; const seen = new Set();
  for (const el of root.querySelectorAll('li, [class*="item" i], span, div')) {
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ');
    if (t && t.length < 40 && !seen.has(t)) { seen.add(t); out.push(t); }
  }
  return out.slice(0, 20);
}
"""


def _is_available(state: str, aria: str) -> bool:
    text = f"{state} {aria}".lower()
    if any(tok in text for tok in selectors.SEAT_UNAVAILABLE_TOKENS):
        return False
    if any(tok in text for tok in selectors.SEAT_AVAILABLE_TOKENS):
        return True
    return False  # unknown = not bookable (conservative for alerts)


# EF's seat-map renders each seat as a button with an inner lucide-react SVG.
# The icon class is the most reliable signal for "what kind of seat is this":
#   user           -> occupied (carries no extra type info)
#   x              -> blocked
#   dot            -> standard available seat
#   star           -> premium / extra-legroom seat (Main Cabin Extra, Premium Class)
#   accessibility  -> accessible seat
#   door-open / door-closed / log-out -> exit-row marker (observed variations)
# Anything else still available falls back to "standard".
_ICON_TYPES: dict[str, str] = {
    "star": "premium",
    "accessibility": "accessible",
    "door-open": "exit",
    "door-closed": "exit",
    "log-out": "exit",
    "dollar-sign": "paid",
    "circle-dollar-sign": "paid",
}
# Backstop: aria-label / class tokens, used when the icon is missing or unknown.
_TYPE_TOKENS: list[tuple[str, tuple[str, ...]]] = [
    ("paid_premium", ("paid premium",)),
    ("paid",         ("paid",)),
    ("premium",      ("premium",)),
    ("exit",         ("exit row", "exit-row", "exitrow", "exit ")),
    ("accessible",   ("accessible",)),
]


def _classify_types(seats: list) -> None:
    for s in seats:
        icon_type = _ICON_TYPES.get((s.icon or "").lower())
        if icon_type:
            s.seat_type = icon_type
            continue
        text = f"{s.aria} {s.cls}".lower()
        for label, tokens in _TYPE_TOKENS:
            if any(tok in text for tok in tokens):
                s.seat_type = label
                break
        else:
            s.seat_type = "standard"


def capture_seatmap(session: Session, url: str, out_dir: Path, name: str = "seatmap") -> dict:
    """Navigate to a seat-map URL and capture screenshot + legend + seats."""
    page = session.page
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(url, wait_until="networkidle")
    # Seats render asynchronously; wait for them before extracting.
    try:
        page.wait_for_selector(selectors.SEATMAP["seat_cell"], timeout=session.settings.timeout_ms)
    except Exception:
        page.wait_for_timeout(2500)

    result = page.evaluate(_EXTRACT_JS)
    seats: list[Seat] = []
    for r in result["seats"]:
        parsed = parse_label(r["label"])
        if not parsed:
            continue
        row, col = parsed
        seats.append(Seat(
            label=r["label"], row=row, column=col,
            available=_is_available(r.get("state", ""), r.get("aria", "")),
            state=r.get("state", ""),
            aria=r.get("aria", ""), cls=r.get("cls", ""),
            icon=r.get("icon", ""),
            x=r["x"], y=r["y"], width=r["width"], height=r["height"],
        ))
    classify_positions(seats)
    _classify_types(seats)

    # Prefer the page's legend panel; otherwise derive one from observed states.
    legend: list[str] = []
    try:
        legend = page.evaluate(_LEGEND_JS, selectors.SEATMAP["legend_root"])
    except Exception:
        pass
    state_counts = Counter(s.state or "unknown" for s in seats)
    if not legend:
        legend = [f"{st}: {n}" for st, n in sorted(state_counts.items())]

    shot = out_dir / f"{name}.png"
    page.screenshot(path=str(shot), full_page=True)

    seats_sorted = sorted(seats, key=lambda s: (s.row, s.column))
    summary = summarize(seats_sorted)
    summary["states"] = dict(sorted(state_counts.items()))
    summary["extract_mode"] = result["mode"]
    data = {
        "url": url,
        "screenshot": str(shot),
        "legend": legend,
        "seats": [s.to_dict() for s in seats_sorted],
        "summary": summary,
    }
    (out_dir / f"{name}.json").write_text(json.dumps(data, indent=2))
    return data
