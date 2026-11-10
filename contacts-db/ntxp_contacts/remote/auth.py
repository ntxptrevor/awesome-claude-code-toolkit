"""OAuth-token gate for the cloud MCP — verification only (not a full AS).

The cloud MCP is stateless: each request carries a Bearer token. v1 verifies a
Google Workspace OAuth access token and requires the ntxpllc.com hosted domain,
so access ends up being "zero setup except OAuth". Modes (env ``NTXP_MCP_AUTH``):

* ``google`` (default) — validate the access token at Google's userinfo endpoint
  and require ``hd == NTXP_MCP_ALLOWED_DOMAIN``.
* ``static`` — accept a single shared token (``NTXP_MCP_TOKEN``); for a private
  deployment behind the agent proxy / an internal gateway.
* ``none``   — dev bypass (no auth). Never use in production.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.parse
import urllib.request

ALLOWED_DOMAIN = os.environ.get("NTXP_MCP_ALLOWED_DOMAIN", "ntxpllc.com")
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# Google answers userinfo for ANY access token with an email scope, so without an audience check a
# token minted for a third-party app by an ntxpllc.com user would be accepted. When
# NTXP_GOOGLE_CLIENT_ID is set we also require the token's aud/azp to be that client (or one listed in
# NTXP_GOOGLE_ALLOWED_CLIENT_IDS, comma separated, for MCP clients that use their own OAuth client).
_CACHE: dict[str, tuple[float, dict | None]] = {}
_CACHE_LOCK = threading.Lock()
_OK_TTL, _BAD_TTL, _CACHE_MAX = 60.0, 15.0, 2048


def _allowed_clients() -> set[str]:
    ids = {os.environ.get("NTXP_GOOGLE_CLIENT_ID", "").strip()}
    ids |= {x.strip() for x in os.environ.get("NTXP_GOOGLE_ALLOWED_CLIENT_IDS", "").split(",")}
    return {i for i in ids if i}


def _get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        return json.load(resp)


def _google_check(token: str) -> dict | None:
    try:
        info = _get_json(USERINFO_URL, token)
    except Exception:
        return None
    if not isinstance(info, dict) or info.get("hd") != ALLOWED_DOMAIN:
        return None
    if info.get("email_verified") in (False, "false"):
        return None
    clients = _allowed_clients()
    if clients:
        try:
            ti = json.load(urllib.request.urlopen(
                TOKENINFO_URL + "?" + urllib.parse.urlencode({"access_token": token}), timeout=6))
        except Exception:
            return None
        if not isinstance(ti, dict) or not ({ti.get("aud"), ti.get("azp")} & clients):
            return None
    return {"email": info.get("email"), "domain": info.get("hd")}


def _cached_google(token: str) -> dict | None:
    key = hashlib.sha256(token.encode("utf-8", "replace")).hexdigest()
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and hit[0] > now:
            return hit[1]
    result = _google_check(token)
    with _CACHE_LOCK:
        if len(_CACHE) >= _CACHE_MAX:
            for k in [k for k, v in _CACHE.items() if v[0] <= now] or list(_CACHE)[: _CACHE_MAX // 2]:
                _CACHE.pop(k, None)
        _CACHE[key] = (now + (_OK_TTL if result else _BAD_TTL), result)
    return result


async def verify_token_async(token: str | None, allow_service: bool = False) -> dict | None:
    """verify_token without blocking the event loop (the Google call can take seconds)."""
    return await asyncio.to_thread(verify_token, token, allow_service)


def verify_token(token: str | None, allow_service: bool = False) -> dict | None:
    """Return {'email','domain'} for a valid token, else None.

    Peer service tokens (``svc.<peer>.<secret>``) are accepted only when the caller opts in
    (``allow_service=True``, used for /api/v1 alone): a peer key must never open /mcp,
    /carddav or the human /api surface."""
    if token and token.startswith("svc."):
        if not allow_service:
            return None
        from ..peers import load_peers, verify_service_token
        return verify_service_token(token, load_peers()[0])
    mode = os.environ.get("NTXP_MCP_AUTH", "google").lower()
    if mode == "none":
        return {"email": "anonymous@" + ALLOWED_DOMAIN, "domain": ALLOWED_DOMAIN}
    if not token:
        return None
    if mode == "static":
        want = os.environ.get("NTXP_MCP_TOKEN")
        if want and hmac.compare_digest(token.encode("utf-8", "replace"), want.encode("utf-8", "replace")):
            return {"email": "service@" + ALLOWED_DOMAIN, "domain": ALLOWED_DOMAIN}
        return None
    # mode == "google"
    return _cached_google(token)
