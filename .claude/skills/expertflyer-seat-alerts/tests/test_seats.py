from efalert.seats import Seat, classify_positions, parse_label, summarize


def test_parse_label():
    assert parse_label("12A") == (12, "A")
    assert parse_label(" 3 F ") == (3, "F")
    assert parse_label("7I") is None      # airlines skip column I
    assert parse_label("aisle") is None
    assert parse_label("") is None


def _row_3_3(row=10, y=100.0):
    # Two groups of 3 (A B C | D E F) with a wide aisle gap in the middle.
    xs = {"A": 0, "B": 20, "C": 40, "D": 100, "E": 120, "F": 140}
    return [
        Seat(label=f"{row}{c}", row=row, column=c, available=True,
             x=float(x), y=y, width=18.0, height=18.0)
        for c, x in xs.items()
    ]


def test_classify_positions_geometry_3_3():
    seats = classify_positions(_row_3_3())
    pos = {s.column: s.position for s in seats}
    assert pos["A"] == "window"
    assert pos["F"] == "window"
    assert pos["C"] == "aisle"
    assert pos["D"] == "aisle"
    assert pos["B"] == "middle"
    assert pos["E"] == "middle"


def test_classify_positions_no_geometry_fallback():
    seats = [Seat(label=f"5{c}", row=5, column=c, available=True) for c in "ABCDEF"]
    classify_positions(seats)
    pos = {s.column: s.position for s in seats}
    assert pos["A"] == "window" and pos["F"] == "window"
    assert "aisle" in pos.values()


def test_summarize_counts():
    seats = _row_3_3()
    seats[0].available = False
    classify_positions(seats)
    s = summarize(seats)
    assert s["total"] == 6
    assert s["available"] == 5
    assert sum(s["available_by_position"].values()) == 5
