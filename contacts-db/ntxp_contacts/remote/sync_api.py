"""/api/sync/* — the machine surface the sync worker uses to pull source data in and push edits out.
Authenticated by NTXP_SYNC_TOKEN only (see ApiApp); it never reaches the human /api, /mcp or /carddav."""
from __future__ import annotations

from ..sync.base import RemoteRecord
from ..sync.prepare import prepare
from ..sync.reconcile import Reconciler
from .api import ApiError, _json, _need_dict

SYSTEMS = ("lightfield", "jobtread", "gcontacts")
MAX_BATCH = 200


def handle_sync(conn, method: str, path: str, body):
    p = path.rstrip("/")
    try:
        if p == "/api/sync/status" and method == "GET":
            return _json(200, _status(conn))
        if method != "POST":
            return _json(405, {"error": "POST only"})
        body = _need_dict(body)
        if p == "/api/sync/reconcile":
            system = body.get("system")
            recs = body.get("records")
            if system not in SYSTEMS or not isinstance(recs, list):
                raise ApiError(400, f"system must be one of {SYSTEMS} and records a list")
            if len(recs) > MAX_BATCH:
                raise ApiError(413, f"at most {MAX_BATCH} records per call")
            remotes, skipped = [], 0
            for i, r in enumerate(recs):
                if not isinstance(r, dict):
                    skipped += 1
                    continue
                d = prepare(r)
                if d is None:
                    skipped += 1
                    continue
                remotes.append(RemoteRecord(external_id=str(d.get("external_id") or f"{system}-{i}"), payload=d))
            stats = Reconciler(conn, system).apply(remotes, reindex=False)
            return _json(200, {"applied": stats, "skipped": skipped})
        if p == "/api/sync/reindex":
            from ..db.repository import Repository
            Repository(conn).rebuild_fts()
            conn.commit()
            return _json(200, {"ok": True})
        raise ApiError(404, "not found")
    except ApiError as e:
        return _json(e.status, {"error": e.msg})


def _status(conn) -> dict:
    out = {}
    for s in SYSTEMS:
        row = conn.execute("SELECT COUNT(*) AS n, MAX(last_synced_at) AS last FROM external_ids WHERE system=?", (s,)).fetchone()
        out[s] = {"linked": row["n"], "last_synced_at": str(row["last"]) if row["last"] else None}
    out["totals"] = {
        "contacts": conn.execute("SELECT COUNT(*) AS n FROM contacts WHERE is_deleted=0").fetchone()["n"],
        "organizations": conn.execute("SELECT COUNT(*) AS n FROM organizations WHERE is_deleted=0").fetchone()["n"],
    }
    return out
