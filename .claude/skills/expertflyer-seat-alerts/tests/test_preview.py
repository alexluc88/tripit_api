import json

from PIL import Image

from efalert.preview import render_preview


def _make_seatmap(tmp_path):
    base = tmp_path / "shot.png"
    Image.new("RGB", (200, 200), (255, 255, 255)).save(base)
    data = {
        "url": "https://example/seatmap",
        "screenshot": str(base),
        "legend": [],
        "seats": [
            {"label": "12A", "row": 12, "column": "A", "available": True,
             "position": "window", "x": 20, "y": 20, "width": 18, "height": 18},
            {"label": "12C", "row": 12, "column": "C", "available": True,
             "position": "aisle", "x": 80, "y": 20, "width": 18, "height": 18},
        ],
    }
    j = tmp_path / "seatmap.json"
    j.write_text(json.dumps(data))
    return j


def test_render_preview_highlights_found(tmp_path):
    j = _make_seatmap(tmp_path)
    out = tmp_path / "preview.png"
    report = render_preview(j, ["12A"], out)
    assert report["found"] == ["12A"]
    assert report["missing"] == []
    assert out.exists()
    # Pixels near 12A should no longer be pure white (highlight drawn).
    img = Image.open(out).convert("RGB")
    assert img.getpixel((20, 19)) != (255, 255, 255)


def test_render_preview_reports_missing(tmp_path):
    j = _make_seatmap(tmp_path)
    out = tmp_path / "preview.png"
    report = render_preview(j, ["12A", "99Z"], out)
    assert report["found"] == ["12A"]
    assert report["missing"] == ["99Z"]
