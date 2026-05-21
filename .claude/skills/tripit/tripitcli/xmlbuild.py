"""Build the small XML payloads TripIt requires for write operations.

Reads come back as JSON, but create/replace take an XML ``<Request>`` document.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring


def trip_request(start_date: str, end_date: str, primary_location: str,
                 display_name: str | None = None) -> str:
    """A minimal ``<Request><Trip>…</Trip></Request>`` for creating a trip.

    Dates are ``YYYY-MM-DD``; primary_location is a free-text place TripIt geocodes.
    """
    root = Element("Request")
    trip = SubElement(root, "Trip")
    SubElement(trip, "start_date").text = start_date
    SubElement(trip, "end_date").text = end_date
    SubElement(trip, "primary_location").text = primary_location
    if display_name:
        SubElement(trip, "display_name").text = display_name
    return tostring(root, encoding="unicode")
