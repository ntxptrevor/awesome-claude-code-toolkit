"""SQLite store: the access log, the append-only lists, and OAuth records.

The MCP protocol layer is stateless (no session). This file is the only
persistent state. `access_log` rows can never be updated or deleted, and
`entries` rows can never be updated; SQLite triggers enforce both.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS access_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email  TEXT NOT NULL,
    role        TEXT,
    ts_utc      TEXT NOT NULL,           -- full ISO 8601 timestamp, UTC
    date_stamp  TEXT NOT NULL,           -- YYYY-MM-DD
    time_stamp  TEXT NOT NULL,           -- HH:MM:SS
    epoch       REAL NOT NULL,
    action      TEXT NOT NULL CHECK (action IN ('read','write','delete','copy','auth','sync')),
    tool        TEXT NOT NULL,
    target      TEXT,
    outcome     TEXT NOT NULL CHECK (outcome IN ('ok','denied','error')),
    flag        TEXT,                    -- copy_attempt, cross_user, misuse, ...
    reason      TEXT,
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS ix_log_user ON access_log (user_email, epoch);
CREATE INDEX IF NOT EXISTS ix_log_flag ON access_log (flag);
CREATE TRIGGER IF NOT EXISTS access_log_no_update BEFORE UPDATE ON access_log
BEGIN SELECT RAISE(ABORT, 'access_log is append only'); END;
CREATE TRIGGER IF NOT EXISTS access_log_no_delete BEFORE DELETE ON access_log
BEGIN SELECT RAISE(ABORT, 'access_log is append only'); END;

CREATE TABLE IF NOT EXISTS entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT NOT NULL CHECK (kind IN ('changelog','activity','usage_note')),
    scope         TEXT NOT NULL,         -- a skill or plugin name, or 'forge'
    author_email  TEXT NOT NULL,
    ts_utc        TEXT NOT NULL,
    date_stamp    TEXT NOT NULL,
    body          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_entries ON entries (kind, scope, id);
CREATE TRIGGER IF NOT EXISTS entries_no_update BEFORE UPDATE ON entries
BEGIN SELECT RAISE(ABORT, 'entries are append only'); END;

CREATE TABLE IF NOT EXISTS users (
    email       TEXT PRIMARY KEY,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id   TEXT PRIMARY KEY,
    info_json   TEXT NOT NULL,
    created     REAL NOT NULL
);

-- One row per spent authorization code or revoked token id.
CREATE TABLE IF NOT EXISTS spent_tokens (
    jti  TEXT PRIMARY KEY,
    exp  REAL NOT NULL
);
"""


def _now() -> tuple[str, str, str, float]:
    now = datetime.now(timezone.utc)
    return (now.isoformat(timespec="seconds"), now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"), now.timestamp())


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        if self.path != ":memory:":
            self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)

    @contextmanager
    def transaction(self):
        """Run several statements as one unit: all are saved, or none is."""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            self._db.execute("COMMIT")

    def _all(self, sql: str, args: tuple = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._db.execute(sql, args).fetchall()]

    def _run(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._db.execute(sql, args)

    # -- access log ----------------------------------------------------------
    def log(self, user: str, role: str | None, action: str, tool: str, *,
            target: str = "", outcome: str = "ok", flag: str = "",
            reason: str = "", detail: str = "") -> int:
        ts, date, clock, epoch = _now()
        cur = self._run(
            "INSERT INTO access_log (user_email, role, ts_utc, date_stamp, time_stamp, epoch,"
            " action, tool, target, outcome, flag, reason, detail)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (user or "anonymous", role, ts, date, clock, epoch, action, tool,
             target or None, outcome, flag or None, reason or None, (detail or None)))
        return int(cur.lastrowid)

    def query_log(self, *, user: str = "", action: str = "", flag: str = "",
                  flagged_only: bool = False, since: str = "", limit: int = 100) -> list[dict]:
        where, args = [], []
        if user:
            where.append("user_email = ?"); args.append(user)
        if action:
            where.append("action = ?"); args.append(action)
        if flag:
            where.append("flag = ?"); args.append(flag)
        if flagged_only:
            where.append("flag IS NOT NULL")
        if since:
            where.append("date_stamp >= ?"); args.append(since)
        sql = ("SELECT id, user_email, role, ts_utc, date_stamp, time_stamp, action, tool,"
               " target, outcome, flag, reason, detail FROM access_log")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(max(1, min(int(limit), 1000)))
        return self._all(sql, tuple(args))

    def files_read(self, user: str, window: int, tool: str = "package_file") -> set[str]:
        """Distinct file targets one user read successfully inside the window."""
        rows = self._all(
            "SELECT DISTINCT target FROM access_log WHERE user_email = ? AND tool = ?"
            " AND outcome = 'ok' AND epoch >= ?", (user, tool, time.time() - window))
        return {r["target"] for r in rows if r["target"]}

    # -- users ---------------------------------------------------------------
    def touch_user(self, email: str) -> bool:
        """Record a visit. Returns True on the user's first use of the server."""
        ts = _now()[0]
        with self._lock:
            first = self._db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone() is None
            if first:
                self._db.execute("INSERT INTO users VALUES (?,?,?)", (email, ts, ts))
            else:
                self._db.execute("UPDATE users SET last_seen = ? WHERE email = ?", (ts, email))
        return first

    # -- append-only lists ---------------------------------------------------
    def append_entry(self, kind: str, scope: str, author: str, body: str) -> int:
        ts, date, _, _ = _now()
        cur = self._run(
            "INSERT INTO entries (kind, scope, author_email, ts_utc, date_stamp, body)"
            " VALUES (?,?,?,?,?,?)", (kind, scope, author, ts, date, body))
        return int(cur.lastrowid)

    def list_entries(self, kind: str = "", scope: str = "", limit: int = 100) -> list[dict]:
        where, args = [], []
        if kind:
            where.append("kind = ?"); args.append(kind)
        if scope:
            where.append("scope = ?"); args.append(scope)
        sql = "SELECT * FROM entries"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(max(1, min(int(limit), 1000)))
        return self._all(sql, tuple(args))

    def get_entry(self, entry_id: int) -> dict | None:
        rows = self._all("SELECT * FROM entries WHERE id = ?", (entry_id,))
        return rows[0] if rows else None

    def delete_entry(self, entry_id: int) -> bool:
        return self._run("DELETE FROM entries WHERE id = ?", (entry_id,)).rowcount > 0

    # -- OAuth records -------------------------------------------------------
    def save_client(self, client_id: str, info_json: str) -> None:
        self._run("INSERT OR REPLACE INTO oauth_clients VALUES (?,?,?)",
                  (client_id, info_json, time.time()))

    def get_client(self, client_id: str) -> str | None:
        rows = self._all("SELECT info_json FROM oauth_clients WHERE client_id = ?", (client_id,))
        return rows[0]["info_json"] if rows else None

    def spend(self, jti: str, exp: float) -> bool:
        """Mark a code or token id as used. Returns False if it was used before."""
        with self._lock:
            self._db.execute("DELETE FROM spent_tokens WHERE exp < ?", (time.time(),))
            try:
                self._db.execute("INSERT INTO spent_tokens VALUES (?,?)", (jti, exp))
                return True
            except sqlite3.IntegrityError:
                return False

    def is_spent(self, jti: str) -> bool:
        return bool(self._all("SELECT 1 FROM spent_tokens WHERE jti = ?", (jti,)))
