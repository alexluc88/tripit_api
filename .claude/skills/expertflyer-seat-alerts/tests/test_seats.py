from efalert.seats import Seat, classify_positions, parse_label, summarize
from efalert.seatmap import _classify_types


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


def test_classify_types_from_icons():
    seats = [
        Seat(label="6A", row=6, column="A", available=True, icon="star"),
        Seat(label="12C", row=12, column="C", available=True, icon="dot"),
        Seat(label="16D", row=16, column="D", available=True, icon="door-open"),
        Seat(label="20A", row=20, column="A", available=True, icon="accessibility"),
        Seat(label="22F", row=22, column="F", available=False, icon="user"),
    ]
    _classify_types(seats)
    assert {s.label: s.seat_type for s in seats} == {
        "6A": "premium", "12C": "standard", "16D": "exit",
        "20A": "accessible", "22F": "standard",
    }


def test_classify_types_fallback_to_aria():
    # Icon missing — fall back to aria/cls token match.
    seats = [
        Seat(label="3A", row=3, column="A", available=True,
             aria="Seat 3A, available, premium"),
        Seat(label="9C", row=9, column="C", available=True,
             aria="Seat 9C, available", cls="bg-exit-row text-white"),
    ]
    _classify_types(seats)
    assert seats[0].seat_type == "premium"
    assert seats[1].seat_type == "exit"


def test_summarize_counts():
    seats = _row_3_3()
    seats[0].available = False
    classify_positions(seats)
    s = summarize(seats)
    assert s["total"] == 6
    assert s["available"] == 5
    assert sum(s["available_by_position"].values()) == 5
