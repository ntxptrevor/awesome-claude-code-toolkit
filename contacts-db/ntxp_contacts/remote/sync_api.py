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
        if p == "/api/sync/outbox" and method == "GET":
            return _json(200, _outbox(conn, body if isinstance(body, dict) else {}))
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
            _touch(conn, system)
            return _json(200, {"applied": stats, "skipped": skipped})
        if p == "/api/sync/outbox":
            return _json(200, _outbox(conn, body))
        if p == "/api/sync/ack":
            return _json(200, _ack(conn, body))
        if p == "/api/sync/baseline":
            return _json(200, _baseline(conn))
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


def _touch(conn, system: str) -> None:
    conn.execute("INSERT INTO sync_state(system, last_seq, last_pull_at) VALUES (?,0,datetime('now')) "
                 "ON CONFLICT(system) DO UPDATE SET last_pull_at = datetime('now')", (system,))
    conn.commit()


def _outbox(conn, q: dict) -> dict:
    """Edits made here that a connected system has not seen yet (updates by default; creates only on request)."""
    from ..sync.engine import SyncEngine
    system = q.get("system")
    if system not in SYSTEMS:
        raise ApiError(400, f"system must be one of {SYSTEMS}")
    limit = max(1, min(int(q.get("limit") or 50), 200))
    plan = SyncEngine(conn, system).plan("push")
    if not q.get("include_create"):
        plan = [o for o in plan if o["op"] == "update"]
    return {"system": system, "count": len(plan), "ops": plan[:limit]}


def _ack(conn, body: dict) -> dict:
    """The worker reports pushes it completed: record the link/hash, advance the high-water mark."""
    from ..sync.engine import SyncEngine
    system = body.get("system")
    if system not in SYSTEMS:
        raise ApiError(400, f"system must be one of {SYSTEMS}")
    eng, n = SyncEngine(conn, system), 0
    for r in body.get("results") or []:
        if not isinstance(r, dict):
            continue
        eng.record_result(int(r["entity_id"]), str(r["external_id"]), str(r["payload_hash"]))
        n += 1
    _touch(conn, system)
    return {"recorded": n}


def _baseline(conn) -> dict:
    """After the initial bulk load: treat everything so far as already in sync, so only NEW edits are pushed."""
    from ..sync.engine import SyncEngine
    seq = conn.execute("SELECT COALESCE(MAX(seq),0) AS s FROM change_log").fetchone()["s"]
    for s in SYSTEMS:
        SyncEngine(conn, s).set_high_water(seq)
    return {"high_water": seq}


def connections(conn) -> dict:
    """Per-source live state for the header icons: connected (has linked records), active (synced in the
    last 2 minutes or has edits waiting), pending edits not yet pushed."""
    labels = {"lightfield": "Lightfield", "jobtread": "JobTread", "gcontacts": "Google Workspace"}
    out = []
    for s in SYSTEMS:
        linked = conn.execute("SELECT COUNT(*) AS n FROM external_ids WHERE system=?", (s,)).fetchone()["n"]
        st = conn.execute("SELECT last_seq, last_pull_at FROM sync_state WHERE system=?", (s,)).fetchone()
        hw = int(st["last_seq"]) if st else 0
        pending = conn.execute("SELECT COUNT(DISTINCT entity_id) AS n FROM change_log WHERE seq > ? AND entity_type='contact' "
                               "AND origin <> ?", (hw, f"pull:{s}")).fetchone()["n"]
        last = str(st["last_pull_at"]) if st and st["last_pull_at"] else None
        out.append({"system": s, "label": labels[s], "linked": linked, "last_synced_at": last, "pending": pending,
                    "connected": linked > 0})
    return {"connections": out}
