#!/usr/bin/env python3
"""
harvester.py — the only writer to the knowledge base.

Runs as a Cloud Run Job on a schedule, not inside the MCP server. Keeping the
writer separate is what lets the server stay stateless and fast: a tool call
answers from data that is already there instead of triggering a multi-minute
sweep of every mailbox in the company while a client waits.

The sweep is incremental everywhere it can be. Gmail is queried with an
`after:` cursor, Drive through the Changes API with a page token, Calendar
across a bounded window. A daily run therefore reads what changed yesterday,
not the whole history, which is what keeps it inside both Google's quota and
D1's 100k-writes-per-day free tier.

Order matters and is deliberate:

    1. roster      — everything else is keyed to a person
    2. projects    — tagging rules must be loaded before events are tagged
    3. events      — gmail, calendar, drive, per user, concurrently
    4. derive      — threads and counterparties rolled up from raw events
    5. rollups     — permanent daily aggregates
    6. detect      — rules run over the freshly-written data
    7. prune       — age out raw detail, never rollups or flags

Usage:
    python harvester.py                 full incremental sweep
    python harvester.py --users a@b,c@d limit to specific mailboxes
    python harvester.py --days 30       widen the lookback (first run)
    python harvester.py --detect-only   re-run rules without re-fetching
    python harvester.py --dry-run       report what would be written
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import kb
import workspace

CONCURRENCY = int(os.environ.get("HARVEST_CONCURRENCY", "5"))
DEFAULT_LOOKBACK_DAYS = int(os.environ.get("HARVEST_LOOKBACK_DAYS", "2"))
RETAIN_DAYS = int(os.environ.get("KB_RETAIN_DAYS", "400"))

# Thresholds — every one is an env var because the right value is a matter of
# how your team actually works, and a rule that cries wolf gets ignored.
T_REPLY_HOURS = int(os.environ.get("T_REPLY_HOURS", "48"))
T_ACTIVITY_GAP_DAYS = int(os.environ.get("T_ACTIVITY_GAP_DAYS", "3"))
T_LOGIN_ABSENCE_DAYS = int(os.environ.get("T_LOGIN_ABSENCE_DAYS", "5"))
T_ESCALATION_COUNT = int(os.environ.get("T_ESCALATION_COUNT", "3"))
T_MASS_DELETE = int(os.environ.get("T_MASS_DELETE", "20"))
T_STALE_PROJECT_DAYS = int(os.environ.get("T_STALE_PROJECT_DAYS", "14"))

# Language that reliably precedes a problem becoming expensive. Tuned for how
# public owners, CMs and subs actually write — direct, contractual, and rarely
# subtle. Matched against subject lines only; bodies are never stored.
ESCALATION_TERMS = [
    "notice of", "cure", "default", "breach", "liquidated damages", "backcharge",
    "back charge", "claim", "dispute", "attorney", "counsel", "lien", "bond claim",
    "termination", "stop work", "non-compliance", "noncompliance", "deficient",
    "rejected", "unacceptable", "escalate", "escalation", "urgent", "immediately",
    "overdue", "past due", "final notice", "second request", "third request",
    "still waiting", "no response", "unresolved", "delay", "time impact",
    "differing site", "failed inspection", "punch", "warranty claim",
]
_ESC_RE = re.compile("|".join(re.escape(t) for t in ESCALATION_TERMS), re.I)

HIGH_VALUE_TERMS = ["pay app", "payment application", "g702", "g703", "invoice",
                    "change order", "rfi", "submittal", "contract", "award",
                    "notice to proceed", "ntp", "certificate of substantial"]
_HV_RE = re.compile("|".join(re.escape(t) for t in HIGH_VALUE_TERMS), re.I)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def _addr(raw: str) -> str:
    m = _EMAIL_RE.search(raw or "")
    return m.group(0).lower() if m else ""


def risk_of(subject: str) -> int:
    """0-3. Escalation language dominates; high-value nouns add a point.

    Kept crude on purpose. The score's job is to make a row findable later,
    not to adjudicate anything — a human or the model reads the thread.
    """
    s = subject or ""
    score = 0
    if _ESC_RE.search(s):
        score += 2
    if _HV_RE.search(s):
        score += 1
    return min(score, 3)


# ---------------------------------------------------------------------------
# Project tagging
# ---------------------------------------------------------------------------


class Tagger:
    """Resolves an event to a project by folder, domain, or keyword.

    Compiled once per run rather than per event: with a few dozen projects and
    tens of thousands of events, rebuilding regexes inside the loop is the
    difference between a fast job and a slow one.
    """

    def __init__(self, projects: List[Dict[str, Any]]):
        self.by_folder: Dict[str, str] = {}
        self.by_domain: Dict[str, str] = {}
        self.keyword_res: List[Tuple[re.Pattern, str]] = []
        for p in projects:
            pid = p["project_id"]
            if p.get("drive_folder_id"):
                self.by_folder[p["drive_folder_id"]] = pid
            for d in json.loads(p.get("match_domains") or "[]"):
                self.by_domain[d.lower()] = pid
            kws = json.loads(p.get("match_keywords") or "[]")
            if kws:
                self.keyword_res.append(
                    (re.compile("|".join(re.escape(k) for k in kws), re.I), pid)
                )

    def tag(self, *, text: str = "", domain: str = "", folder: str = "") -> Optional[str]:
        if folder and folder in self.by_folder:
            return self.by_folder[folder]
        if domain and domain.lower() in self.by_domain:
            return self.by_domain[domain.lower()]
        for rx, pid in self.keyword_res:
            if text and rx.search(text):
                return pid
        return None


# ---------------------------------------------------------------------------
# Cursors
# ---------------------------------------------------------------------------


async def get_cursor(source: str, scope: str) -> Optional[str]:
    rows = await kb.d1(
        "SELECT cursor FROM sync_state WHERE source = ? AND scope = ?", [source, scope]
    )
    return rows[0]["cursor"] if rows else None


async def set_cursor(source: str, scope: str, cursor: Optional[str],
                     seen: int = 0, error: Optional[str] = None) -> None:
    now = kb.utcnow()
    await kb.d1_write(
        """INSERT INTO sync_state (source, scope, cursor, last_run, last_ok,
                                   last_error, items_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(source, scope) DO UPDATE SET
             cursor     = COALESCE(excluded.cursor, sync_state.cursor),
             last_run   = excluded.last_run,
             last_ok    = CASE WHEN excluded.last_error IS NULL
                               THEN excluded.last_run ELSE sync_state.last_ok END,
             last_error = excluded.last_error,
             items_seen = sync_state.items_seen + excluded.items_seen""",
        [source, scope, cursor, now, None if error else now, error, seen],
    )


# ---------------------------------------------------------------------------
# Stage 1 — roster
# ---------------------------------------------------------------------------


async def sync_roster(dry: bool) -> List[str]:
    users = await workspace.directory_users(max_results=1000)
    now = kb.utcnow()
    rows = [
        (u["email"], u["full_name"], u["given_name"], u["org_unit"], u["title"],
         1 if u["is_admin"] else 0, 1 if u["suspended"] else 0,
         u["last_login_ts"], u["created_ts"], now, now)
        for u in users if u.get("email")
    ]
    if not dry:
        await kb.upsert_many(
            "people",
            ["email", "full_name", "given_name", "org_unit", "title", "is_admin",
             "suspended", "last_login_ts", "created_ts", "first_seen", "last_seen"],
            rows,
            conflict_key="email",
            update_cols=["full_name", "given_name", "org_unit", "title", "is_admin",
                         "suspended", "last_login_ts", "last_seen"],
        )
    active = [u["email"] for u in users if not u["suspended"]]
    log(f"roster: {len(users)} users, {len(active)} active")
    return active


async def load_projects() -> List[Dict[str, Any]]:
    try:
        return await kb.d1(
            "SELECT project_id, drive_folder_id, match_domains, match_keywords "
            "FROM projects WHERE status = 'active'"
        )
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Stage 3 — per-user event sweeps
# ---------------------------------------------------------------------------


async def sweep_gmail(email: str, tagger: Tagger, lookback: int, dry: bool) -> int:
    """Metadata for messages newer than the cursor.

    Uses an `after:` epoch rather than Gmail's historyId because history IDs
    expire after roughly a week — a job that misses two runs over a holiday
    would silently lose the gap. An epoch cursor always resumes correctly, and
    re-reading a small overlap is harmless since rows are keyed and upserted.
    """
    cursor = await get_cursor("gmail", email)
    if cursor:
        after = int(cursor)
    else:
        after = int((datetime.now(timezone.utc) - timedelta(days=lookback)).timestamp())
    # Small overlap absorbs clock skew and messages that land mid-run.
    query = f"after:{max(0, after - 600)}"

    try:
        msgs = await workspace.gmail_search(email, query, max_results=400)
    except Exception as exc:
        await set_cursor("gmail", email, None, 0, workspace.explain_error(exc, email))
        return 0

    now = kb.utcnow()
    rows = []
    for m in msgs:
        frm, to = _addr(m.get("from", "")), _addr(m.get("to", ""))
        outbound = frm == email
        counterparty = to if outbound else frm
        cp_domain = counterparty.split("@")[-1] if "@" in counterparty else ""
        subject = (m.get("subject") or "")[:500]
        rows.append((
            f"{email}:{m['id']}", m["ts"], email,
            "outbound" if outbound else "inbound",
            counterparty, cp_domain,
            0 if workspace.is_internal(counterparty) else 1,
            subject, m.get("thread_id"),
            len([x for x in (m.get("to", "") + "," + m.get("cc", "")).split(",") if x.strip()]) or 1,
            1 if "has:attachment" in query else 0,
            json.dumps(m.get("labels", [])),
            tagger.tag(text=subject, domain=cp_domain),
            risk_of(subject), now,
        ))

    if rows and not dry:
        await kb.upsert_many(
            "comm_events",
            ["id", "ts", "person", "direction", "counterparty", "cp_domain",
             "is_external", "subject", "thread_id", "recipient_count",
             "has_attachment", "labels", "project_id", "risk_score", "harvested_at"],
            rows, conflict_key="id",
        )
    if not dry:
        await set_cursor("gmail", email, str(int(datetime.now(timezone.utc).timestamp())),
                         len(rows))
    return len(rows)


async def sweep_calendar(email: str, tagger: Tagger, lookback: int, dry: bool) -> int:
    try:
        events = await workspace.calendar_events(
            email, days_back=lookback, days_forward=30, max_results=250
        )
    except Exception as exc:
        await set_cursor("calendar", email, None, 0, workspace.explain_error(exc, email))
        return 0

    now = kb.utcnow()
    rows = []
    for e in events:
        start, end = e.get("start"), e.get("end")
        dur = None
        try:
            if start and end and "T" in start:
                dur = int((datetime.fromisoformat(end.replace("Z", "+00:00"))
                           - datetime.fromisoformat(start.replace("Z", "+00:00"))
                           ).total_seconds() / 60)
        except Exception:
            pass
        title = (e.get("title") or "")[:300]
        organizer = e.get("organizer") or ""
        rows.append((
            f"{email}:{e['event_id']}", e["event_id"], email, start, end, dur,
            title, organizer, 1 if e.get("is_organizer") else 0,
            (e.get("location") or "")[:200], e.get("attendee_count", 0),
            e.get("external_count", 0), e.get("response_status"), e.get("status"),
            e.get("recurring_id"),
            tagger.tag(text=title, domain=organizer.split("@")[-1] if "@" in organizer else ""),
            now,
        ))

    if rows and not dry:
        await kb.upsert_many(
            "calendar_events",
            ["id", "event_id", "person", "ts_start", "ts_end", "duration_min",
             "title", "organizer", "is_organizer", "location", "attendee_count",
             "external_count", "response_status", "status", "recurring_id",
             "project_id", "harvested_at"],
            rows, conflict_key="id",
        )
    if not dry:
        await set_cursor("calendar", email, None, len(rows))
    return len(rows)


async def sweep_drive(email: str, tagger: Tagger, dry: bool) -> int:
    token = await get_cursor("drive", email)
    try:
        res = await workspace.drive_changes(email, token)
    except Exception as exc:
        await set_cursor("drive", email, None, 0, workspace.explain_error(exc, email))
        return 0

    if res.get("bootstrapped"):
        # First sight of this drive: store the start token and take the deltas
        # from the next run. There is no way to ask Drive for "changes before
        # now", so the alternative would be a full-drive crawl for no benefit.
        if not dry:
            await set_cursor("drive", email, res["new_token"], 0)
        return 0

    now = kb.utcnow()
    rows = []
    for ch in res.get("changes", []):
        f = ch.get("file") or {}
        fid = ch.get("fileId") or f.get("id")
        if not fid:
            continue
        ts = ch.get("time") or now
        if ch.get("removed") or f.get("trashed"):
            action = "trashed"
        elif f.get("createdTime") and f.get("createdTime") == f.get("modifiedTime"):
            action = "created"
        else:
            action = "modified"

        perms = f.get("permissions") or []
        ext_shared = any(
            p.get("type") == "anyone"
            or (p.get("emailAddress") and not workspace.is_internal(p["emailAddress"]))
            or (p.get("domain") and workspace.PRIMARY_DOMAIN
                and p["domain"].lower() != workspace.PRIMARY_DOMAIN.lower())
            for p in perms
        )
        parents = f.get("parents") or []
        parent = parents[0] if parents else None
        name = (f.get("name") or "")[:300]

        risk = 0
        if ext_shared:
            risk += 2
        if action == "trashed":
            risk += 1
        if _HV_RE.search(name):
            risk += 1

        rows.append((
            f"{email}:{fid}:{ts}", ts, email,
            (f.get("lastModifyingUser") or {}).get("emailAddress"),
            fid, name, f.get("mimeType"), action, parent, None, None,
            1 if ext_shared else 0,
            int(f.get("size") or 0) or None,
            tagger.tag(text=name, folder=parent or ""),
            min(risk, 3), now,
        ))

    if rows and not dry:
        await kb.upsert_many(
            "drive_events",
            ["id", "ts", "person", "actor", "file_id", "file_name", "mime_type",
             "action", "parent_id", "parent_name", "path_hint", "shared_external",
             "size_bytes", "project_id", "risk_score", "harvested_at"],
            rows, conflict_key="id",
        )
    if not dry:
        await set_cursor("drive", email, res.get("new_token"), len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Stage 4 — derive threads and counterparties
# ---------------------------------------------------------------------------


async def rebuild_threads(days: int, dry: bool) -> int:
    """Collapse recent messages into per-thread state.

    `awaiting_reply` is computed here rather than queried on demand because the
    on-demand version is a self-join over the whole message table — the single
    most expensive question anyone asks, turned into an indexed lookup.
    """
    since = kb.days_ago(days)
    msgs = await kb.d1(
        "SELECT thread_id, ts, direction, subject, project_id, counterparty, "
        "is_external, risk_score FROM comm_events WHERE ts >= ? AND thread_id IS NOT NULL "
        "ORDER BY ts",
        [since],
    )
    if not msgs:
        return 0

    agg: Dict[str, Dict[str, Any]] = {}
    for m in msgs:
        t = agg.setdefault(m["thread_id"], {
            "subject": m["subject"], "project_id": m["project_id"],
            "first_ts": m["ts"], "last_ts": m["ts"], "last_direction": m["direction"],
            "last_inbound_ts": None, "last_outbound_ts": None, "msg_count": 0,
            "participants": set(), "is_external": 0, "max_risk": 0,
        })
        t["msg_count"] += 1
        t["last_ts"] = m["ts"]
        t["last_direction"] = m["direction"]
        t["project_id"] = t["project_id"] or m["project_id"]
        t["max_risk"] = max(t["max_risk"], m["risk_score"] or 0)
        t["is_external"] = max(t["is_external"], m["is_external"] or 0)
        if m["counterparty"]:
            t["participants"].add(m["counterparty"])
        if m["direction"] == "inbound":
            t["last_inbound_ts"] = m["ts"]
        else:
            t["last_outbound_ts"] = m["ts"]

    rows = []
    for tid, t in agg.items():
        awaiting = int(
            bool(t["last_inbound_ts"])
            and (not t["last_outbound_ts"] or t["last_outbound_ts"] < t["last_inbound_ts"])
        )
        rows.append((
            tid, t["subject"], t["project_id"], t["first_ts"], t["last_ts"],
            t["last_direction"], t["last_inbound_ts"], t["last_outbound_ts"],
            t["msg_count"], json.dumps(sorted(t["participants"])[:20]),
            t["is_external"], awaiting, t["max_risk"],
        ))

    if not dry:
        await kb.upsert_many(
            "threads",
            ["thread_id", "subject", "project_id", "first_ts", "last_ts",
             "last_direction", "last_inbound_ts", "last_outbound_ts", "msg_count",
             "participants", "is_external", "awaiting_reply", "max_risk"],
            rows, conflict_key="thread_id",
        )
    log(f"threads: {len(rows)} rebuilt")
    return len(rows)


async def rebuild_counterparties(days: int, dry: bool) -> int:
    since = kb.days_ago(days)
    rows = await kb.d1(
        """SELECT counterparty address, cp_domain domain,
                  MIN(ts) first_contact, MAX(ts) last_contact, COUNT(*) msg_count,
                  SUM(CASE WHEN direction='inbound' THEN 1 ELSE 0 END) inbound_count,
                  SUM(CASE WHEN direction='outbound' THEN 1 ELSE 0 END) outbound_count,
                  MAX(project_id) project_id, MIN(is_external) is_ext
           FROM comm_events WHERE ts >= ? AND counterparty IS NOT NULL AND counterparty != ''
           GROUP BY counterparty""",
        [since],
    )
    if rows and not dry:
        await kb.upsert_many(
            "counterparties",
            ["address", "domain", "is_internal", "first_contact", "last_contact",
             "msg_count", "inbound_count", "outbound_count", "project_id"],
            [(r["address"], r["domain"] or "", 0 if r["is_ext"] else 1,
              r["first_contact"], r["last_contact"], r["msg_count"],
              r["inbound_count"], r["outbound_count"], r["project_id"]) for r in rows],
            conflict_key="address",
            update_cols=["domain", "last_contact", "msg_count", "inbound_count",
                         "outbound_count", "project_id"],
        )
    log(f"counterparties: {len(rows)}")
    return len(rows)


# ---------------------------------------------------------------------------
# Stage 5 — daily rollups
# ---------------------------------------------------------------------------


async def build_rollups(days: int, dry: bool) -> int:
    """Aggregate raw events into one permanent row per person per day.

    Everything trend-shaped answers from this table. It is roughly 1/500th the
    row count of the raw tables, which is the whole reason a 'how has her
    workload changed since March' question stays inside the read budget.
    """
    since = kb.days_ago(days)
    agg: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
        lambda: defaultdict(int) | {"first": None, "last": None}
    )

    mail = await kb.d1(
        """SELECT substr(ts,1,10) day, person, direction, is_external,
                  COUNT(*) n, MIN(ts) mn, MAX(ts) mx,
                  COUNT(DISTINCT thread_id) threads
           FROM comm_events WHERE ts >= ?
           GROUP BY day, person, direction, is_external""",
        [since],
    )
    for r in mail:
        a = agg[(r["day"], r["person"])]
        if r["direction"] == "outbound":
            a["emails_sent"] += r["n"]
            if r["is_external"]:
                a["external_out"] += r["n"]
        else:
            a["emails_received"] += r["n"]
            if r["is_external"]:
                a["external_in"] += r["n"]
        a["threads_touched"] += r["threads"]
        a["first"] = min(x for x in (a["first"], r["mn"]) if x)
        a["last"] = max(x for x in (a["last"], r["mx"]) if x)

    cal = await kb.d1(
        """SELECT substr(ts_start,1,10) day, person, COUNT(*) n,
                  COALESCE(SUM(duration_min),0) mins
           FROM calendar_events WHERE ts_start >= ? AND status != 'cancelled'
           GROUP BY day, person""",
        [since],
    )
    for r in cal:
        a = agg[(r["day"], r["person"])]
        a["meetings"] += r["n"]
        a["meeting_minutes"] += int(r["mins"] or 0)

    drv = await kb.d1(
        """SELECT substr(ts,1,10) day, person, action, COUNT(*) n,
                  SUM(shared_external) shares, MIN(ts) mn, MAX(ts) mx
           FROM drive_events WHERE ts >= ? GROUP BY day, person, action""",
        [since],
    )
    for r in drv:
        a = agg[(r["day"], r["person"])]
        if r["action"] == "created":
            a["drive_creates"] += r["n"]
        else:
            a["drive_edits"] += r["n"]
        a["drive_shares"] += int(r["shares"] or 0)
        a["first"] = min(x for x in (a["first"], r["mn"]) if x)
        a["last"] = max(x for x in (a["last"], r["mx"]) if x)

    rows = []
    for (day, person), a in agg.items():
        total = (a["emails_sent"] + a["emails_received"] + a["meetings"]
                 + a["drive_creates"] + a["drive_edits"])
        rows.append((
            day, person, a["emails_sent"], a["emails_received"], a["external_in"],
            a["external_out"], a["threads_touched"], a["meetings"],
            a["meeting_minutes"], a["drive_creates"], a["drive_edits"],
            a["drive_shares"], a["first"], a["last"], 1 if total else 0,
        ))

    if rows and not dry:
        await kb.upsert_many(
            "rollups_daily",
            ["day", "person", "emails_sent", "emails_received", "external_in",
             "external_out", "threads_touched", "meetings", "meeting_minutes",
             "drive_creates", "drive_edits", "drive_shares", "first_activity",
             "last_activity", "active"],
            rows, conflict_key="day, person",
        )
    log(f"rollups: {len(rows)} person-days")
    return len(rows)


# ---------------------------------------------------------------------------
# Stage 6 — detection rules
# ---------------------------------------------------------------------------


async def detect(dry: bool) -> List[Dict[str, Any]]:
    """Each rule is a query plus a dedupe key.

    The dedupe key is the important half. Without one, a daily job turns a
    single real problem into a wall of identical rows and the queue becomes
    noise nobody opens. With one, a persistent problem is a single row whose
    occurrence count climbs — which is also a better signal than thirty rows.
    """
    found: List[Dict[str, Any]] = []

    async def fire(rule, key, title, detail, severity="medium",
                   person=None, project=None, evidence=None):
        found.append({"rule": rule, "title": title, "severity": severity,
                      "person": person, "project": project, "detail": detail})
        if not dry:
            await kb.flag_upsert(rule, key, title, detail, severity,
                                 person, project, evidence)

    # 1. External inbound nobody has answered.
    for r in await kb.d1(
        "SELECT thread_id, subject, project_id, last_inbound_ts, hours_waiting, "
        "participants FROM v_awaiting_reply WHERE hours_waiting >= ? "
        "ORDER BY hours_waiting DESC LIMIT 50", [T_REPLY_HOURS]
    ):
        sev = "high" if r["hours_waiting"] >= T_REPLY_HOURS * 2 else "medium"
        await fire(
            "unanswered_inbound", f"unanswered:{r['thread_id']}",
            f"Unanswered {r['hours_waiting']}h — {(r['subject'] or '(no subject)')[:90]}",
            f"External inbound on {r['last_inbound_ts']} with no reply since. "
            f"Participants: {r['participants']}.",
            sev, None, r["project_id"], {"thread_id": r["thread_id"]},
        )

    # 2. Escalation language on a live thread.
    for r in await kb.d1(
        "SELECT thread_id, subject, project_id, last_ts, max_risk FROM threads "
        "WHERE max_risk >= 2 AND last_ts >= ? ORDER BY last_ts DESC LIMIT 50",
        [kb.days_ago(7)],
    ):
        await fire(
            "escalation_language", f"escalation:{r['thread_id']}",
            f"Escalation language — {(r['subject'] or '(no subject)')[:90]}",
            f"Contractual or dispute wording detected in the subject line. "
            f"Last message {r['last_ts']}. Read the thread before it hardens.",
            "high", None, r["project_id"], {"thread_id": r["thread_id"]},
        )

    # 3. Anything shared outside the domain.
    for r in await kb.d1(
        "SELECT file_name, actor, ts, project_id, file_id FROM drive_events "
        "WHERE shared_external = 1 AND ts >= ? ORDER BY ts DESC LIMIT 50",
        [kb.days_ago(2)],
    ):
        await fire(
            "external_share", f"extshare:{r['file_id']}",
            f"Shared outside the domain — {(r['file_name'] or 'file')[:80]}",
            f"{r['actor'] or 'someone'} shared this externally on {r['ts']}. "
            "Confirm the recipient is intended and the content is releasable.",
            "high", r["actor"], r["project_id"], {"file_id": r["file_id"]},
        )

    # 4. Bulk deletion — the shape of either a cleanup or a problem.
    for r in await kb.d1(
        "SELECT person, COUNT(*) n FROM drive_events WHERE action = 'trashed' "
        "AND ts >= ? GROUP BY person HAVING n >= ?",
        [kb.days_ago(1), T_MASS_DELETE],
    ):
        await fire(
            "mass_delete", f"massdel:{r['person']}:{kb.utcnow()[:10]}",
            f"{r['n']} files trashed in 24h — {r['person']}",
            f"{r['person']} moved {r['n']} files to trash in one day. Usually a "
            "folder cleanup; occasionally not. Worth a glance.",
            "critical" if r["n"] >= T_MASS_DELETE * 3 else "high", r["person"],
        )

    # 5. Someone has gone quiet.
    for r in await kb.d1(
        "SELECT email, full_name, days_quiet FROM v_last_activity "
        "WHERE days_quiet >= ? OR last_active_day IS NULL LIMIT 50",
        [T_ACTIVITY_GAP_DAYS],
    ):
        d = r["days_quiet"]
        await fire(
            "activity_gap", f"gap:{r['email']}:{kb.utcnow()[:7]}",
            f"No recorded activity for {d or 'many'} days — {r['full_name'] or r['email']}",
            "No email, calendar, or Drive activity recorded. Could be leave, "
            "field work without a laptop, or an account problem.",
            "high" if d and d >= T_ACTIVITY_GAP_DAYS * 2 else "medium", r["email"],
        )

    # 6. Not logging in at all.
    for r in await kb.d1(
        "SELECT email, full_name, last_login_ts FROM people WHERE suspended = 0 "
        "AND (last_login_ts IS NULL OR last_login_ts < ?) LIMIT 50",
        [kb.days_ago(T_LOGIN_ABSENCE_DAYS)],
    ):
        await fire(
            "login_absence", f"nologin:{r['email']}:{kb.utcnow()[:7]}",
            f"No login since {(r['last_login_ts'] or 'ever')[:10]} — "
            f"{r['full_name'] or r['email']}",
            "Account has not signed in recently. Check whether it should still "
            "be licensed and active.",
            "medium", r["email"],
        )

    # 7. An active project that has gone silent.
    for r in await kb.d1(
        """SELECT p.project_id, p.name,
                  MAX(COALESCE(c.last_ts, '')) last_comm
           FROM projects p LEFT JOIN threads c ON c.project_id = p.project_id
           WHERE p.status = 'active' GROUP BY p.project_id
           HAVING last_comm < ? OR last_comm = ''""",
        [kb.days_ago(T_STALE_PROJECT_DAYS)],
    ):
        await fire(
            "stale_project", f"stale:{r['project_id']}:{kb.utcnow()[:7]}",
            f"No project traffic in {T_STALE_PROJECT_DAYS}+ days — {r['name']}",
            f"Last recorded communication: {r['last_comm'] or 'none'}. An active "
            "project with no email, meetings, or file changes is usually a "
            "tracking gap rather than a genuinely idle job.",
            "medium", None, r["project_id"],
        )

    # 8. A brand-new external domain now in regular contact.
    for r in await kb.d1(
        "SELECT domain, COUNT(*) addrs, SUM(msg_count) msgs, MIN(first_contact) first "
        "FROM counterparties WHERE is_internal = 0 AND first_contact >= ? "
        "GROUP BY domain HAVING msgs >= ? LIMIT 25",
        [kb.days_ago(14), T_ESCALATION_COUNT],
    ):
        await fire(
            "new_external_domain", f"newdomain:{r['domain']}",
            f"New external domain in regular contact — {r['domain']}",
            f"{r['msgs']} messages across {r['addrs']} addresses since "
            f"{(r['first'] or '')[:10]}. If this is a project party, register the "
            "project so their traffic gets tagged automatically.",
            "low", None, None,
        )

    log(f"detect: {len(found)} signals")
    return found


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def run(users: Optional[List[str]], lookback: int, dry: bool,
              detect_only: bool) -> Dict[str, Any]:
    started = datetime.now(timezone.utc)
    stats: Dict[str, Any] = {"started": started.isoformat(), "dry_run": dry}

    if detect_only:
        stats["signals"] = await detect(dry)
        stats["duration_s"] = (datetime.now(timezone.utc) - started).total_seconds()
        return stats

    targets = users or await sync_roster(dry)
    tagger = Tagger(await load_projects())
    log(f"sweeping {len(targets)} mailboxes, lookback {lookback}d, "
        f"concurrency {CONCURRENCY}")

    sem = asyncio.Semaphore(CONCURRENCY)
    totals = defaultdict(int)
    errors: List[str] = []

    async def one(email: str):
        async with sem:
            try:
                g, c, d = await asyncio.gather(
                    sweep_gmail(email, tagger, lookback, dry),
                    sweep_calendar(email, tagger, lookback, dry),
                    sweep_drive(email, tagger, dry),
                )
                totals["gmail"] += g
                totals["calendar"] += c
                totals["drive"] += d
            except Exception as exc:
                errors.append(f"{email}: {workspace.explain_error(exc, email)}")

    await asyncio.gather(*[one(e) for e in targets])
    log(f"events: {dict(totals)}")

    window = max(lookback, 7)
    await rebuild_threads(window, dry)
    await rebuild_counterparties(window, dry)
    await build_rollups(window, dry)
    stats["signals"] = await detect(dry)

    if not dry:
        stats["pruned"] = await kb.prune(RETAIN_DAYS)

    stats.update({
        "mailboxes": len(targets), "events": dict(totals), "errors": errors,
        "duration_s": round((datetime.now(timezone.utc) - started).total_seconds(), 1),
    })
    return stats


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--users", help="Comma-separated mailboxes; default is all active.")
    p.add_argument("--days", type=int, default=DEFAULT_LOOKBACK_DAYS,
                   help="Lookback window when no cursor exists yet.")
    p.add_argument("--dry-run", action="store_true", help="Fetch and report; write nothing.")
    p.add_argument("--detect-only", action="store_true",
                   help="Re-run detection rules over existing data.")
    a = p.parse_args()

    users = [u.strip().lower() for u in a.users.split(",")] if a.users else None
    try:
        stats = asyncio.run(run(users, a.days, a.dry_run, a.detect_only))
    except Exception as exc:
        log(f"FAILED: {exc}")
        sys.exit(1)

    print("\n" + json.dumps(stats, indent=2, default=str))
    sys.exit(1 if stats.get("errors") and not stats.get("mailboxes") else 0)


if __name__ == "__main__":
    main()
