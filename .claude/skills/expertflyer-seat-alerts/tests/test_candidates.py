from efalert.candidates import select_candidates


def _seat(label, row, col, *, available=True, position="window"):
    return {
        "label": label, "row": row, "column": col,
        "available": available, "position": position,
    }


def test_groups_by_position_and_caps():
    seats = [
        _seat("12A", 12, "A", position="window"),
        _seat("12C", 12, "C", position="aisle"),
        _seat("12D", 12, "D", position="aisle"),
        _seat("12F", 12, "F", position="window"),
        _seat("14A", 14, "A", position="window"),
        _seat("14C", 14, "C", position="aisle"),
        _seat("16B", 16, "B", position="middle"),
    ]
    out = select_candidates(seats, top_k=2)
    assert [s["label"] for s in out["window"]] == ["12A", "12F"]
    assert [s["label"] for s in out["aisle"]] == ["12C", "12D"]
    assert [s["label"] for s in out["middle"]] == ["16B"]


def test_skips_unavailable():
    seats = [
        _seat("1A", 1, "A", position="window", available=False),
        _seat("2A", 2, "A", position="window"),
    ]
    out = select_candidates(seats, top_k=4)
    assert [s["label"] for s in out["window"]] == ["2A"]


def test_prefers_forward_rows():
    seats = [
        _seat("30A", 30, "A", position="window"),
        _seat("5A", 5, "A", position="window"),
        _seat("12A", 12, "A", position="window"),
    ]
    out = select_candidates(seats, top_k=2)
    assert [s["label"] for s in out["window"]] == ["5A", "12A"]
