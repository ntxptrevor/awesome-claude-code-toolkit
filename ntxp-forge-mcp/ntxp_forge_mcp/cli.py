"""Command line for the NTXP Forge MCP.

    ntxp-forge-mcp serve     HTTP endpoint with Google sign-in (the normal mode)
    ntxp-forge-mcp stdio     local stdio transport for one person, no sign-in
    ntxp-forge-mcp check     show which credentials NTXP ID still has to supply
    ntxp-forge-mcp log       print recent access-log rows
"""
from __future__ import annotations

import argparse
import json
import sys

from . import ntxp_id
from .config import Settings
from .db import Store
from .forge import Forge, ForgeError
from .policy import role_for


def _serve(settings: Settings) -> int:
    try:
        ntxp_id.require_first_run(settings, http=True)
    except ntxp_id.NtxpIdRequired as missing:
        print(missing, file=sys.stderr)
        return 2
    import uvicorn

    from .oauth import GoogleGate
    from .server import http_app

    store = Store(settings.db_path)
    forge = Forge(settings)
    try:
        status = forge.sync(force=True)
    except ForgeError as err:
        print(f"First Forge sync failed: {err}", file=sys.stderr)
        return 3
    print(f"NTXP Forge at {status['commit']}; endpoint {settings.resource_url}", file=sys.stderr)
    app = http_app(settings, store, forge, GoogleGate(settings, store))
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
    return 0


def _stdio(settings: Settings) -> int:
    if role_for(settings.dev_user) is None:
        print("Set NTXP_FORGE_MCP_DEV_USER to your ntxpllc.com address for stdio mode.",
              file=sys.stderr)
        return 2
    try:
        ntxp_id.require_first_run(settings, http=False)
    except ntxp_id.NtxpIdRequired as missing:
        print(missing, file=sys.stderr)
        return 2
    from .server import build_server

    store = Store(settings.db_path)
    build_server(settings, store, Forge(settings)).run()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ntxp-forge-mcp", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve")
    sub.add_parser("stdio")
    sub.add_parser("check")
    log = sub.add_parser("log")
    log.add_argument("--user", default="")
    log.add_argument("--flagged", action="store_true")
    log.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    settings = Settings.from_env()

    if args.cmd == "serve":
        return _serve(settings)
    if args.cmd == "stdio":
        return _stdio(settings)
    if args.cmd == "check":
        status = ntxp_id.status(settings)
        print(json.dumps(status, indent=2))
        return 0 if status["ready"] else 2
    rows = Store(settings.db_path).query_log(user=args.user, flagged_only=args.flagged,
                                             limit=args.limit)
    for r in reversed(rows):
        print(f"{r['date_stamp']} {r['time_stamp']}  {r['user_email']:<28} {r['action']:<6} "
              f"{r['outcome']:<6} {r['tool']:<16} {r['target'] or ''}"
              + (f"  [{r['flag']}]" if r["flag"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
