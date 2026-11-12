#!/usr/bin/env python3
"""
kb.py — knowledge base layer over Cloudflare D1.

Why D1 and not a local file: the MCP server is stateless and runs on Cloud Run,
which may spin up several instances or none at all. Any state on local disk is
gone between requests. D1 is SQLite reachable over plain HTTPS, so every
instance sees the same database with no connection pool to manage and nothing
to keep warm.

The one D1 behaviour worth internalising: billing counts rows SCANNED, not rows
returned. `SELECT * FROM comm_events WHERE subject LIKE '%foo%'` on a 300k-row
table costs 300k reads against a 5M/day budget — about sixteen such queries and
you are done for the day. Every helper here filters on an indexed column, and
`sql_query()` refuses obviously unbounded statements. When you need text search,
search `threads` (thousands of rows) rather than `comm_events` (hundreds of
thousands), or add a targeted index.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")
CF_DATABASE_ID = os.environ.get("CF_DATABASE_ID", "")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "")

_D1_URL = (
    "https://api.cloudflare.com/client/v4/accounts/{acct}/d1/database/{db}/query"
)

# D1 caps a single statement's bound parameters. Chunk bulk writes below it.
_MAX_PARAMS = 100
_HTTP_TIMEOUT = 30.0


class KBError(RuntimeError):
    """Knowledge base failure. Messages are safe to surface to the user."""


def _configured() -> bool:
    return bool(CF_ACCOUNT_ID and CF_DATABASE_ID and CF_API_TOKEN)


def _require_config() -> None:
    if not _configured():
        raise KBError(
            "Knowledge base is not configured. Set CF_ACCOUNT_ID, CF_DATABASE_ID "
            "and CF_API_TOKEN in the Cloud Run environment. Until then the "
            "intelligence tools still work — only KB history is unavailable."
        )


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Core transport
# ---------------------------------------------------------------------------


async def d1(sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
    """Run one statement and return its rows as dicts.

    Raises KBError with Cloudflare's own message on failure, because those
    messages ("no such column: x") are the fastest route to a fix.
    """
    _require_config()
    url = _D1_URL.format(acct=CF_ACCOUNT_ID, db=CF_DATABASE_ID)
    payload = {"sql": sql, "params": [_bind(p) for p in params]}
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code == 401:
        raise KBError("D1 rejected the API token (401). Regenerate CF_API_TOKEN "
                      "with 'D1:Edit' permission on this account.")
    if resp.status_code == 404:
        raise KBError("D1 database not found (404). Check CF_DATABASE_ID.")
    try:
        body = resp.json()
    except ValueError:
        raise KBError(f"D1 returned non-JSON ({resp.status_code}): {resp.text[:200]}")

    if not body.get("success"):
        errs = "; ".join(e.get("message", str(e)) for e in body.get("errors", []))
        if "exceeded" in errs.lower() or "limit" in errs.lower():
            raise KBError(
                f"D1 daily limit reached: {errs}. Free tier allows 5M rows read "
                "and 100k rows written per day. Check for a query missing an index."
            )
        raise KBError(f"D1 error: {errs or body}")

    results = body.get("result") or []
    if not results:
        return []
    return results[0].get("results") or []


def _bind(value: Any) -> Any:
    """D1 accepts null/number/string/blob. Coerce everything else sensibly."""
    if value is None or isinstance(value, (int, float, str)):
        return value
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"))
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat(timespec="seconds")
    return str(value)


async def d1_write(sql: str, params: Sequence[Any] = ()) -> None:
    await d1(sql, params)


async def upsert_many(
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    conflict_key: str = "id",
    update_cols: Optional[Sequence[str]] = None,
) -> int:
    """Insert or update many rows in as few round trips as the param cap allows.

    Chunking on parameter count rather than row count keeps this correct for
    both the 6-column rollup table and the 17-column comm_events table.
    """
    rows = [tuple(r) for r in rows]
    if not rows:
        return 0

    per_row = len(columns)
    chunk_rows = max(1, _MAX_PARAMS // per_row)
    cols_sql = ", ".join(columns)
    updates = update_cols if update_cols is not None else [
        c for c in columns if c not in conflict_key.split(",")
    ]
    set_sql = ", ".join(f"{c}=excluded.{c}" for c in updates) or f"{columns[0]}={columns[0]}"

    written = 0
    for i in range(0, len(rows), chunk_rows):
        chunk = rows[i : i + chunk_rows]
        placeholders = ", ".join(
            "(" + ", ".join("?" * per_row) + ")" for _ in chunk
        )
        sql = (
            f"INSERT INTO {table} ({cols_sql}) VALUES {placeholders} "
            f"ON CONFLICT({conflict_key}) DO UPDATE SET {set_sql}"
        )
        flat: List[Any] = [v for row in chunk for v in row]
        await d1(sql, flat)
        written += len(chunk)
    return written


# ---------------------------------------------------------------------------
# Guarded ad-hoc SQL — exposed as an MCP tool
# ---------------------------------------------------------------------------

_FORBIDDEN = (
    "insert ", "update ", "delete ", "drop ", "alter ", "create ",
    "attach ", "detach ", "pragma ", "replace ", "vacuum ",
)


async def sql_query(sql: str, limit: int = 200) -> Dict[str, Any]:
    """Run a read-only SELECT against the KB.

    Two guards, both about protecting the daily quota rather than protecting
    the data (the data is already scoped to this org):
      - writes are rejected outright; use the dedicated tools for those
      - a LIMIT is injected when absent, so a mistyped WHERE cannot scan the
        whole event history
    """
    stripped = sql.strip().rstrip(";")
    low = stripped.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise KBError("Only SELECT / WITH statements are allowed here.")
    for bad in _FORBIDDEN:
        if bad in low:
            raise KBError(
                f"'{bad.strip()}' is not permitted in sql_query. Use kb_flag_update "
                "or the harvester for writes."
            )
    if " limit " not in low:
        stripped = f"{stripped} LIMIT {int(limit)}"

    rows = await d1(stripped)
    return {"row_count": len(rows), "rows": rows, "sql": stripped}


# ---------------------------------------------------------------------------
# Typed helpers the MCP tools call
# ---------------------------------------------------------------------------


async def kb_health() -> Dict[str, Any]:
    """Table counts, last harvest per source, storage sanity. Cheap by design."""
    out: Dict[str, Any] = {"configured": _configured()}
    if not _configured():
        out["hint"] = "Set CF_ACCOUNT_ID / CF_DATABASE_ID / CF_API_TOKEN."
        return out

    counts = await d1(
        """
        SELECT 'people' t, COUNT(*) n FROM people
        UNION ALL SELECT 'comm_events', COUNT(*) FROM comm_events
        UNION ALL SELECT 'threads', COUNT(*) FROM threads
        UNION ALL SELECT 'calendar_events', COUNT(*) FROM calendar_events
        UNION ALL SELECT 'drive_events', COUNT(*) FROM drive_events
        UNION ALL SELECT 'flags', COUNT(*) FROM flags
        UNION ALL SELECT 'rollups_daily', COUNT(*) FROM rollups_daily
        """
    )
    out["tables"] = {r["t"]: r["n"] for r in counts}
    out["sync"] = await d1(
        "SELECT source, COUNT(*) scopes, MAX(last_ok) last_ok, "
        "SUM(CASE WHEN last_error IS NOT NULL THEN 1 ELSE 0 END) errors "
        "FROM sync_state GROUP BY source"
    )
    out["open_flags"] = await d1(
        "SELECT severity, COUNT(*) n FROM flags WHERE status IN ('open','acknowledged') "
        "GROUP BY severity"
    )
    return out


async def person_timeline(email: str, days: int = 30) -> Dict[str, Any]:
    """Everything the KB knows about one person over a window, in one payload."""
    since = days_ago(days)
    email = email.strip().lower()
    return {
        "person": await d1("SELECT * FROM people WHERE email = ?", [email]),
        "daily": await d1(
            "SELECT * FROM rollups_daily WHERE person = ? AND day >= date(?) "
            "ORDER BY day DESC",
            [email, since],
        ),
        "recent_comms": await d1(
            "SELECT ts, direction, counterparty, subject, project_id, risk_score "
            "FROM comm_events WHERE person = ? AND ts >= ? ORDER BY ts DESC LIMIT 50",
            [email, since],
        ),
        "meetings": await d1(
            "SELECT ts_start, title, organizer, attendee_count, response_status "
            "FROM calendar_events WHERE person = ? AND ts_start >= ? "
            "ORDER BY ts_start DESC LIMIT 50",
            [email, since],
        ),
        "drive": await d1(
            "SELECT ts, action, file_name, parent_name, shared_external "
            "FROM drive_events WHERE person = ? AND ts >= ? ORDER BY ts DESC LIMIT 50",
            [email, since],
        ),
        "open_flags": await d1(
            "SELECT flag_id, rule, severity, title, created_at FROM flags "
            "WHERE person = ? AND status IN ('open','acknowledged')",
            [email],
        ),
    }


async def project_activity(project_id: str, days: int = 30) -> Dict[str, Any]:
    since = days_ago(days)
    return {
        "project": await d1("SELECT * FROM projects WHERE project_id = ?", [project_id]),
        "comms": await d1(
            "SELECT ts, person, direction, counterparty, subject FROM comm_events "
            "WHERE project_id = ? AND ts >= ? ORDER BY ts DESC LIMIT 100",
            [project_id, since],
        ),
        "folder_changes": await d1(
            "SELECT ts, actor, action, file_name, parent_name, shared_external "
            "FROM drive_events WHERE project_id = ? AND ts >= ? ORDER BY ts DESC LIMIT 100",
            [project_id, since],
        ),
        "meetings": await d1(
            "SELECT ts_start, title, organizer, attendee_count FROM calendar_events "
            "WHERE project_id = ? AND ts_start >= ? ORDER BY ts_start DESC LIMIT 50",
            [project_id, since],
        ),
        "open_flags": await d1(
            "SELECT flag_id, rule, severity, title FROM flags "
            "WHERE project_id = ? AND status IN ('open','acknowledged')",
            [project_id],
        ),
        "awaiting_reply": await d1(
            "SELECT thread_id, subject, last_inbound_ts, hours_waiting "
            "FROM v_awaiting_reply WHERE project_id = ? ORDER BY hours_waiting DESC",
            [project_id],
        ),
    }


async def flags_list(
    status: str = "open",
    severity: Optional[str] = None,
    person: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    where = []
    params: List[Any] = []
    if status == "open":
        where.append("status IN ('open','acknowledged')")
    elif status != "all":
        where.append("status = ?")
        params.append(status)
    if severity:
        where.append("severity = ?")
        params.append(severity)
    if person:
        where.append("person = ?")
        params.append(person.strip().lower())
    if project_id:
        where.append("project_id = ?")
        params.append(project_id)
    clause = " WHERE " + " AND ".join(where) if where else ""
    params.append(int(limit))
    return await d1(
        f"SELECT flag_id, created_at, updated_at, rule, status, severity, person, "
        f"project_id, title, detail, occurrences FROM flags{clause} "
        f"ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
        f"WHEN 'medium' THEN 2 ELSE 3 END, updated_at DESC LIMIT ?",
        params,
    )


async def flag_update(
    flag_id: str, status: str, actor: str, note: Optional[str] = None
) -> Dict[str, Any]:
    valid = {"open", "acknowledged", "resolved", "dismissed"}
    if status not in valid:
        raise KBError(f"status must be one of {sorted(valid)}")

    cur = await d1("SELECT status FROM flags WHERE flag_id = ?", [flag_id])
    if not cur:
        raise KBError(f"No flag with id {flag_id}.")
    prev = cur[0]["status"]
    now = utcnow()
    resolved_at = now if status in ("resolved", "dismissed") else None

    await d1_write(
        "UPDATE flags SET status = ?, updated_at = ?, resolved_at = ?, "
        "resolved_by = CASE WHEN ? IS NULL THEN resolved_by ELSE ? END, "
        "note = COALESCE(?, note) WHERE flag_id = ?",
        [status, now, resolved_at, resolved_at, actor, note, flag_id],
    )
    await d1_write(
        "INSERT INTO flag_events (flag_id, ts, actor, from_status, to_status, note) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [flag_id, now, actor, prev, status, note],
    )
    return {"flag_id": flag_id, "from": prev, "to": status, "actor": actor, "ts": now}


async def flag_upsert(
    rule: str,
    dedupe_key: str,
    title: str,
    detail: str,
    severity: str = "medium",
    person: Optional[str] = None,
    project_id: Optional[str] = None,
    evidence: Optional[Any] = None,
) -> str:
    """Create a flag, or bump its occurrence count if the same signal recurs.

    Deduping matters more than it looks: without it a daily harvester turns one
    genuine problem into thirty identical rows and the queue stops being read.
    """
    now = utcnow()
    flag_id = f"{rule}-{abs(hash(dedupe_key)) % (10**10):010d}"
    await d1_write(
        """
        INSERT INTO flags (flag_id, created_at, updated_at, rule, status, severity,
                           person, project_id, title, detail, evidence, dedupe_key,
                           first_seen, occurrences)
        VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(dedupe_key) DO UPDATE SET
            updated_at  = excluded.updated_at,
            occurrences = flags.occurrences + 1,
            detail      = excluded.detail,
            severity    = excluded.severity,
            status      = CASE WHEN flags.status IN ('resolved','dismissed')
                               THEN flags.status ELSE 'open' END
        """,
        [flag_id, now, now, rule, severity, person, project_id, title, detail,
         _bind(evidence), dedupe_key, now],
    )
    row = await d1("SELECT flag_id FROM flags WHERE dedupe_key = ?", [dedupe_key])
    return row[0]["flag_id"] if row else flag_id


async def search(term: str, days: int = 90, limit: int = 50) -> Dict[str, Any]:
    """Text search across the low-cardinality tables only.

    Deliberately does not LIKE-scan comm_events. Threads carry the same
    subjects at a fraction of the row count, and drive_events is indexed by
    time so the window bounds the scan.
    """
    like = f"%{term}%"
    since = days_ago(days)
    return {
        "threads": await d1(
            "SELECT thread_id, subject, project_id, last_ts, msg_count, awaiting_reply "
            "FROM threads WHERE last_ts >= ? AND subject LIKE ? "
            "ORDER BY last_ts DESC LIMIT ?",
            [since, like, limit],
        ),
        "files": await d1(
            "SELECT ts, file_name, parent_name, action, actor, project_id "
            "FROM drive_events WHERE ts >= ? AND file_name LIKE ? "
            "ORDER BY ts DESC LIMIT ?",
            [since, like, limit],
        ),
        "meetings": await d1(
            "SELECT ts_start, title, organizer, person FROM calendar_events "
            "WHERE ts_start >= ? AND title LIKE ? ORDER BY ts_start DESC LIMIT ?",
            [since, like, limit],
        ),
        "flags": await d1(
            "SELECT flag_id, rule, severity, status, title FROM flags "
            "WHERE title LIKE ? OR detail LIKE ? LIMIT ?",
            [like, like, limit],
        ),
        "people": await d1(
            "SELECT email, full_name, org_unit FROM people "
            "WHERE email LIKE ? OR full_name LIKE ? LIMIT 25",
            [like, like],
        ),
    }


async def prune(retain_days: int = 400) -> Dict[str, int]:
    """Age out raw events. Rollups and flags are never pruned.

    Called by the harvester, not by a tool — it is a maintenance action and
    should not be one mistyped argument away from deleting a year of history.
    """
    cutoff = days_ago(retain_days)
    removed: Dict[str, int] = {}
    for table, col in (
        ("comm_events", "ts"),
        ("drive_events", "ts"),
        ("calendar_events", "ts_start"),
    ):
        before = await d1(f"SELECT COUNT(*) n FROM {table} WHERE {col} < ?", [cutoff])
        await d1_write(f"DELETE FROM {table} WHERE {col} < ?", [cutoff])
        removed[table] = before[0]["n"] if before else 0
    return removed
