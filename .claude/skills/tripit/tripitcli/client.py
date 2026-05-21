"""Thin TripIt API client: OAuth-signed reads and writes against api.tripit.com/v1.

Responses are requested as JSON (``format=json``), which TripIt documents as 50%+
smaller than the XML default. Writes (create/replace) still take an XML payload, as
the API requires.
"""
from __future__ import annotations

from urllib.parse import parse_qsl

import requests

from . import oauth
from .config import Settings

API_VERSION = "v1"

# Entities addressable by id via /get and /delete.
OBJECT_TYPES = (
    "air", "lodging", "car", "rail", "transport", "cruise",
    "restaurant", "activity", "note", "map", "directions",
)


class TripItError(RuntimeError):
    pass


def _form(params: dict) -> str:
    """RFC 3986 form-encode a dict so the wire bytes match the signature base string."""
    return "&".join(f"{oauth._enc(k)}={oauth._enc(v)}" for k, v in params.items())


class TripItClient:
    def __init__(self, settings: Settings, token: str = "", token_secret: str = ""):
        self.s = settings
        self.token = token or ""
        self.token_secret = token_secret or ""
        self._verify = not settings.insecure_tls
        if settings.insecure_tls:
            import urllib3

            urllib3.disable_warnings()  # silence the single InsecureRequestWarning

    # -- low-level signed requests -------------------------------------------------
    def _get(self, url: str, params: dict | None = None, parse_json: bool = True):
        params = params or {}
        header = oauth.authorization_header(
            "GET", url, self.s.consumer_key, self.s.consumer_secret,
            self.token, self.token_secret, extra_params=params,
        )
        full = f"{url}?{_form(params)}" if params else url
        resp = requests.get(
            full, headers={"Authorization": header}, verify=self._verify, timeout=self.s.timeout
        )
        return self._handle(resp, parse_json)

    def _post(self, url: str, params: dict):
        header = oauth.authorization_header(
            "POST", url, self.s.consumer_key, self.s.consumer_secret,
            self.token, self.token_secret, extra_params=params,
        )
        resp = requests.post(
            url,
            data=_form(params),
            headers={
                "Authorization": header,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            verify=self._verify,
            timeout=self.s.timeout,
        )
        return self._handle(resp, parse_json=True)

    @staticmethod
    def _handle(resp: requests.Response, parse_json: bool):
        if resp.status_code != 200:
            raise TripItError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        if not parse_json:
            return resp.text
        try:
            return resp.json()
        except ValueError as exc:
            raise TripItError(f"Expected JSON, got: {resp.text[:500]}") from exc

    def _api(self, verb: str, entity: str | None = None, params: dict | None = None):
        params = dict(params or {})
        params.setdefault("format", "json")
        path = "/".join(["", API_VERSION, verb] + ([entity] if entity else []))
        return self._get(f"{self.s.api_base}{path}", params)

    # -- OAuth dance ---------------------------------------------------------------
    def get_request_token(self) -> dict:
        body = self._get(f"{self.s.api_base}/oauth/request_token", parse_json=False)
        return dict(parse_qsl(body))

    def get_access_token(self) -> dict:
        body = self._get(f"{self.s.api_base}/oauth/access_token", parse_json=False)
        return dict(parse_qsl(body))

    # -- reads ---------------------------------------------------------------------
    def list_trips(self, past: bool = False, include_objects: bool = False,
                   page_size: int | None = None, modified_since: int | None = None) -> dict:
        params: dict = {}
        if past:
            params["past"] = "true"
        if include_objects:
            params["include_objects"] = "true"
        if page_size:
            params["page_size"] = str(page_size)
        if modified_since:
            params["modified_since"] = str(modified_since)
        return self._api("list", "trip", params)

    def get_trip(self, trip_id: str, include_objects: bool = True) -> dict:
        params = {"id": str(trip_id)}
        if include_objects:
            params["include_objects"] = "true"
        return self._api("get", "trip", params)

    def list_points_programs(self) -> dict:
        return self._api("list", "points_program")

    def get_points_program(self, program_id: str) -> dict:
        return self._api("get", "points_program", {"id": str(program_id)})

    def get_profile(self) -> dict:
        return self._api("get", "profile")

    def get_object(self, obj_type: str, obj_id: str) -> dict:
        if obj_type not in OBJECT_TYPES:
            raise SystemExit(f"Unknown object type {obj_type!r}; choose one of {', '.join(OBJECT_TYPES)}")
        return self._api("get", obj_type, {"id": str(obj_id)})

    # -- writes --------------------------------------------------------------------
    def create(self, xml: str) -> dict:
        return self._post(f"{self.s.api_base}/{API_VERSION}/create", {"xml": xml, "format": "json"})

    def delete(self, entity: str, obj_id: str) -> dict:
        return self._api("delete", entity, {"id": str(obj_id)})

    def replace(self, entity: str, obj_id: str, xml: str) -> dict:
        return self._post(
            f"{self.s.api_base}/{API_VERSION}/replace",
            {"id": str(obj_id), "xml": xml, "format": "json"},
        )
