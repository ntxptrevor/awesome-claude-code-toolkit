"""Local HTTP server for the NTXP API Log dashboard.

Serves the branded single-page dashboard and a small JSON API backed by the
shared SQLite DB. Stdlib only — no web framework. Binds to loopback by default
because it serves live credentials; exposing it on a network interface is an
explicit, deliberate choice (and prints a warning).

Multiple people "share one database" by pointing `NTXP_APILOG_DB_PATH` at the
same synced file. For concurrent multi-user web access, run one instance on a
trusted host behind your own auth/reverse proxy.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import DEFAULT_HOST, DEFAULT_PORT
from .db import connect, migrate
from .db.repository import Repository
from .model import ApiEntry, UsageEvent

DASHBOARD_HTML = Path(__file__).parent / "dashboard" / "index.html"


def _make_handler(db_override: str | None):
    def repo() -> Repository:
        c = connect(db_override)
        migrate(c)
        return Repository(c)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ntxp-apilog/0.1"

        # -- response helpers ------------------------------------------------
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, default=str).encode("utf-8"),
                       "application/json")

        def _read_body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return {}

        def log_message(self, *args):  # quiet by default
            pass

        # -- routing ---------------------------------------------------------
        def do_GET(self):
            parsed = urlparse(self.path)
            path, qs = parsed.path, parse_qs(parsed.query)
            if path in ("/", "/index.html"):
                if DASHBOARD_HTML.exists():
                    self._send(200, DASHBOARD_HTML.read_bytes(), "text/html; charset=utf-8")
                else:
                    self._send(500, b"dashboard html missing", "text/plain")
                return
            if path == "/api/meta":
                from .config import AUTH_TYPES, CATEGORIES, STATUSES
                self._json({"categories": CATEGORIES, "auth_types": AUTH_TYPES,
                            "statuses": STATUSES})
                return
            if path == "/api/stats":
                self._json(repo().stats())
                return
            if path == "/api/apis":
                r = repo()
                q = (qs.get("q") or [""])[0]
                if q:
                    self._json(r.search(q, limit=int((qs.get("limit") or [100])[0])))
                else:
                    self._json(r.list_apis(
                        status=(qs.get("status") or [None])[0],
                        category=(qs.get("category") or [None])[0],
                    ))
                return
            if path.startswith("/api/apis/"):
                api_id = self._id_from(path, suffix="")
                if api_id is not None:
                    api = repo().get_api(api_id, reveal=False)
                    self._json(api or {"error": "not found"}, 200 if api else 404)
                    return
            self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            body = self._read_body()

            if path == "/api/apis":
                self._upsert(body)
                return
            if path.startswith("/api/apis/") and path.endswith("/reveal"):
                api_id = self._id_from(path, suffix="/reveal")
                if api_id is not None:
                    r = repo()
                    api = r.get_api(api_id, reveal=True)
                    if not api:
                        self._json({"error": "not found"}, 404)
                        return
                    r.log_access(api_id, action="reveal",
                                 accessor=body.get("accessor"),
                                 purpose=body.get("purpose"), origin="dashboard")
                    self._json(api)
                    return
            if path.startswith("/api/apis/") and path.endswith("/usage"):
                api_id = self._id_from(path, suffix="/usage")
                if api_id is not None:
                    r = repo()
                    log_id = r.log_usage(UsageEvent(
                        api_id=api_id, cost=float(body.get("cost") or 0),
                        units=body.get("units"), unit_kind=body.get("unit_kind"),
                        description=body.get("description"),
                        requested_by=body.get("requested_by"), origin="dashboard",
                    ))
                    self._json({"log_id": log_id})
                    return
            self._json({"error": "not found"}, 404)

        def do_DELETE(self):
            path = urlparse(self.path).path
            if path.startswith("/api/apis/"):
                api_id = self._id_from(path, suffix="")
                if api_id is not None:
                    repo().delete_api(api_id)
                    self._json({"ok": True})
                    return
            self._json({"error": "not found"}, 404)

        # -- shared ----------------------------------------------------------
        def _id_from(self, path: str, suffix: str) -> int | None:
            try:
                tail = path[len("/api/apis/"):]
                if suffix:
                    tail = tail[: -len(suffix)]
                return int(tail.strip("/"))
            except (ValueError, IndexError):
                return None

        def _upsert(self, body: dict) -> None:
            if not body.get("name"):
                self._json({"error": "name is required"}, 400)
                return
            tags = body.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            entry = ApiEntry(
                name=body["name"], provider=body.get("provider"),
                category=body.get("category"), base_url=body.get("base_url"),
                docs_url=body.get("docs_url"), login_url=body.get("login_url"),
                purpose=body.get("purpose"), auth_type=body.get("auth_type") or "api_key",
                api_key=body.get("api_key") or None,
                key_number=body.get("key_number") or None,
                login_user=body.get("login_user") or None,
                login_secret=body.get("login_secret") or None,
                cost_model=body.get("cost_model"), currency=body.get("currency") or "USD",
                monthly_budget=body.get("monthly_budget"), owner=body.get("owner"),
                tags=tags, notes=body.get("notes"),
            )
            api_id, is_new = repo().upsert_api(entry, origin="dashboard")
            self._json({"api_id": api_id, "is_new": is_new})

    return Handler


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
          db_override: str | None = None) -> None:
    handler = _make_handler(db_override)
    httpd = ThreadingHTTPServer((host, port), handler)
    if host not in ("127.0.0.1", "localhost", "::1"):
        print(f"WARNING: serving live credentials on {host} (not loopback). "
              "Ensure this interface is trusted and access-controlled.")
    print(f"NTXP API Log dashboard → http://{host}:{port}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
