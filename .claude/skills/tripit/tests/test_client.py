"""Offline checks for request construction + write payloads — no network."""
import pytest

from tripitcli import xmlbuild
from tripitcli.client import TripItClient, _form
from tripitcli.config import Settings


def _settings():
    return Settings(consumer_key="ck", consumer_secret="cs")


def test_form_uses_rfc3986_not_plus():
    # Spaces must be %20 (not +) so the wire body matches the signature base string.
    assert _form({"primary_location": "Paris, France"}) == "primary_location=Paris%2C%20France"


def test_get_signs_and_targets_expected_url(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"ok": True}

    def fake_get(url, headers, verify, timeout):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResp()

    monkeypatch.setattr("tripitcli.client.requests.get", fake_get)
    client = TripItClient(_settings(), token="tk", token_secret="ts")
    out = client.list_trips(past=True)

    assert out == {"ok": True}
    assert captured["url"].startswith("https://api.tripit.com/v1/list/trip?")
    assert "format=json" in captured["url"]
    assert "past=true" in captured["url"]
    assert captured["headers"]["Authorization"].startswith("OAuth ")


def test_get_object_rejects_unknown_type():
    client = TripItClient(_settings(), token="tk", token_secret="ts")
    with pytest.raises(SystemExit):
        client.get_object("spaceship", "1")


def test_trip_request_xml_escapes_and_includes_fields():
    xml = xmlbuild.trip_request("2026-06-01", "2026-06-05", "Paris & Lyon", "Trip <1>")
    assert "<start_date>2026-06-01</start_date>" in xml
    assert "<primary_location>Paris &amp; Lyon</primary_location>" in xml
    assert "&lt;1&gt;" in xml  # display_name is escaped
