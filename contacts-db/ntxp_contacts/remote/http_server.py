"""Stateless streamable-HTTP MCP app, gated by a Bearer OAuth token.

The MCP tools are the same ones the stdio server exposes (search/get/upsert/
reconcile/qualify/enrich/context/locate …). Statelessness means every request
stands alone — all state lives in the canonical DB — so this scales horizontally
on the VPS with no server-side session store.
"""
from __future__ import annotations

import json

from .auth import verify_token

_OPEN_PATHS = ("/health", "/healthz", "/.well-known/")


async def _send_json(send, status: int, body: dict) -> None:
    payload = json.dumps(body).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"),
                            (b"content-length", str(len(payload)).encode())]})
    await send({"type": "http.response.body", "body": payload})


class AuthMiddleware:
    """Pure-ASGI Bearer-token gate. Imports no server deps, so it is unit-testable
    on its own with a stub inner app."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if any(path.startswith(p) or path.rstrip("/").endswith("/health") for p in _OPEN_PATHS):
            return await _send_json(send, 200, {"ok": True, "service": "ntxp-contacts-mcp"})
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers") or []}
        auth = headers.get("authorization", "")
        token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        if verify_token(token) is None:
            return await _send_json(send, 401, {
                "error": "unauthorized",
                "detail": "Bearer Google Workspace (ntxpllc.com) OAuth token required.",
            })
        return await self.app(scope, receive, send)


def build_http_app(db_override=None):
    """Return the auth-gated stateless MCP ASGI app (requires the `mcp` extra)."""
    from ..mcp_server import build_server
    mcp = build_server(db_override, stateless_http=True)
    return AuthMiddleware(mcp.streamable_http_app())


def serve(db_override=None, host: str = "0.0.0.0", port: int = 8080) -> None:
    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover
        raise SystemExit("uvicorn is required: pip install 'ntxp-contacts[remote]'") from exc
    uvicorn.run(build_http_app(db_override), host=host, port=port)
