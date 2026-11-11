"""Vercel entrypoint: the whole Contacts app (page, /api, /api/v1, /mcp, /carddav) as one ASGI function.
State lives in Postgres (NTXP_DB_URL); nothing is written to the function's disk."""
from ntxp_contacts.remote.http_server import build_http_app

app = build_http_app()
