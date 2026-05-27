from efalert.candidates import filter_seats, select_candidates


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


def _seat_with_type(label, row, col, *, position, seat_type, available=False):
    return {"label": label, "row": row, "column": col,
            "position": position, "seat_type": seat_type, "available": available}


def test_filter_by_type_and_position_for_alerts():
    seats = [
        _seat_with_type("6A", 6, "A", position="window", seat_type="premium"),
        _seat_with_type("6C", 6, "C", position="aisle", seat_type="premium"),
        _seat_with_type("6B", 6, "B", position="middle", seat_type="premium"),
        _seat_with_type("12A", 12, "A", position="window", seat_type="standard"),
        _seat_with_type("16D", 16, "D", position="aisle", seat_type="exit"),
    ]
    out = filter_seats(seats, positions=("window", "aisle"),
                       seat_types=("premium", "exit"), only_available=False)
    assert [s["label"] for s in out] == ["6A", "6C", "16D"]


def test_filter_respects_only_available():
    seats = [
        _seat_with_type("6A", 6, "A", position="window",
                        seat_type="premium", available=True),
        _seat_with_type("6F", 6, "F", position="window",
                        seat_type="premium", available=False),
    ]
    assert [s["label"] for s in filter_seats(seats, only_available=True)] == ["6A"]
    assert {s["label"] for s in filter_seats(seats, only_available=False)} == {"6A", "6F"}
