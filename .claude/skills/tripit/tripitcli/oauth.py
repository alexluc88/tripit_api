"""OAuth 1.0a (HMAC-SHA1) request signing for the TripIt API.

TripIt uses three-legged OAuth 1.0 (no oauth_verifier step). This module produces
the ``Authorization: OAuth ...`` header for an arbitrary signed request. It is a
faithful port of the official TripIt Ruby gem's signing, using only the standard
library so the skill has no hard-to-install dependencies.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import quote, urlsplit


def _enc(value) -> str:
    """RFC 3986 percent-encoding (OAuth Core 1.0 sec. 5.1).

    Python keeps ``A-Za-z0-9_.-~`` unescaped and, with ``safe=""``, encodes
    everything else (including ``/``) — exactly the OAuth unreserved set.
    """
    return quote(str(value), safe="")


def _base_url(url: str) -> str:
    """Scheme + host + path with the default port dropped (OAuth normalization)."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    netloc = host
    if parts.port and not (
        (scheme == "https" and parts.port == 443)
        or (scheme == "http" and parts.port == 80)
    ):
        netloc = f"{host}:{parts.port}"
    return f"{scheme}://{netloc}{parts.path}"


def signature(method: str, url: str, params: dict, consumer_secret: str,
              token_secret: str = "") -> str:
    """HMAC-SHA1 signature for ``params`` (which must already exclude oauth_signature)."""
    norm = "&".join(
        f"{_enc(k)}={_enc(v)}" for k, v in sorted(params.items(), key=lambda kv: str(kv[0]))
    )
    base_string = "&".join([method.upper(), _enc(_base_url(url)), _enc(norm)])
    key = f"{_enc(consumer_secret)}&{_enc(token_secret)}"
    digest = hmac.new(key.encode(), base_string.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def authorization_header(method: str, url: str, consumer_key: str, consumer_secret: str,
                         token: str = "", token_secret: str = "",
                         extra_params: dict | None = None) -> str:
    """Build the ``Authorization`` header value for a signed TripIt request.

    ``extra_params`` are the request's own parameters (query args for GET, form
    fields for POST) — they must participate in the signature base string.
    """
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(20),
        "oauth_timestamp": str(int(time.time())),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_version": "1.0",
    }
    if token:
        oauth_params["oauth_token"] = token

    to_sign = dict(oauth_params)
    if extra_params:
        to_sign.update(extra_params)
    oauth_params["oauth_signature"] = signature(
        method, url, to_sign, consumer_secret, token_secret
    )

    realm = "{0.scheme}://{0.netloc}".format(urlsplit(url))
    rendered = ", ".join(f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(oauth_params.items()))
    return f'OAuth realm="{realm}", {rendered}'
