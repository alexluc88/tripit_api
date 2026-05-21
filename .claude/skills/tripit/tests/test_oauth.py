"""Offline checks for OAuth 1.0a signing — no network, no credentials needed."""
from tripitcli import oauth


def test_enc_matches_rfc3986_unreserved():
    # Unreserved set is left alone; everything else is percent-encoded.
    assert oauth._enc("aZ09-._~") == "aZ09-._~"
    assert oauth._enc("a b/c") == "a%20b%2Fc"
    assert oauth._enc("k=v&x") == "k%3Dv%26x"


def test_base_url_drops_default_port_and_query():
    assert oauth._base_url("https://api.tripit.com:443/v1/list/trip?x=1") == (
        "https://api.tripit.com/v1/list/trip"
    )
    assert oauth._base_url("https://api.tripit.com/v1/get/trip") == (
        "https://api.tripit.com/v1/get/trip"
    )


def test_signature_is_deterministic_and_known():
    # Fixed inputs -> fixed HMAC-SHA1/base64 signature (regression guard).
    params = {
        "oauth_consumer_key": "ck",
        "oauth_nonce": "n",
        "oauth_timestamp": "1",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_version": "1.0",
        "format": "json",
    }
    sig = oauth.signature(
        "GET", "https://api.tripit.com/v1/list/trip", params,
        consumer_secret="cs", token_secret="ts",
    )
    assert sig == "zfTn+oy+ZGCaRFivT+aIe/IqGaI="


def test_authorization_header_includes_signature_and_realm():
    header = oauth.authorization_header(
        "GET", "https://api.tripit.com/v1/list/trip",
        consumer_key="ck", consumer_secret="cs",
        token="tk", token_secret="ts", extra_params={"format": "json"},
    )
    assert header.startswith('OAuth realm="https://api.tripit.com"')
    assert "oauth_consumer_key=" in header
    assert "oauth_token=" in header
    assert "oauth_signature=" in header
