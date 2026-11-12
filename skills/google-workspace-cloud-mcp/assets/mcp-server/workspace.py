#!/usr/bin/env python3
"""
workspace.py — the Google data layer.

Everything here reads Workspace through one service account with domain-wide
delegation, impersonating whichever user's data is being read. That mechanism
is not a stylistic choice: Google offers no other way for one credential to
read across every mailbox and drive in a domain.

Configuration is environment variables only — no config.json. On a stateless
service the container filesystem is ephemeral and an instance may be created
to serve a single request, so anything read from disk has to be either baked
into the image or mounted from Secret Manager. Env vars keep that honest and
make `gcloud run services update` the single place configuration changes.

Nothing in this module writes to Google. Reads only. The harvester writes to
the knowledge base; the knowledge base is the only thing this system mutates.
"""

from __future__ import annotations

import asyncio
import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# The service account that holds domain-wide delegation. Leave unset on Cloud
# Run: the service's own identity is used. No key file exists anywhere.
SA_EMAIL = os.environ.get("SERVICE_ACCOUNT_EMAIL", "").strip()
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
CUSTOMER_ID = os.environ.get("CUSTOMER_ID", "my_customer")
PRIMARY_DOMAIN = os.environ.get("PRIMARY_DOMAIN", "")

S_GMAIL = "https://www.googleapis.com/auth/gmail.readonly"
S_CAL = "https://www.googleapis.com/auth/calendar.readonly"
S_DRIVE = "https://www.googleapis.com/auth/drive.readonly"
S_TASKS = "https://www.googleapis.com/auth/tasks.readonly"
S_CONTACTS = "https://www.googleapis.com/auth/contacts.readonly"
S_DIR_USER = "https://www.googleapis.com/auth/admin.directory.user.readonly"
S_DIR_GROUP = "https://www.googleapis.com/auth/admin.directory.group.readonly"
S_DIR_OU = "https://www.googleapis.com/auth/admin.directory.orgunit.readonly"
S_RPT_AUDIT = "https://www.googleapis.com/auth/admin.reports.audit.readonly"
S_RPT_USAGE = "https://www.googleapis.com/auth/admin.reports.usage.readonly"

# Write scopes. Used only by the admin write functions at the end of this file.
W_GMAIL = "https://www.googleapis.com/auth/gmail.modify"
W_GMAIL_SEND = "https://www.googleapis.com/auth/gmail.send"
W_CAL = "https://www.googleapis.com/auth/calendar"
W_DRIVE = "https://www.googleapis.com/auth/drive"
W_DIR_USER = "https://www.googleapis.com/auth/admin.directory.user"
W_DIR_GROUP = "https://www.googleapis.com/auth/admin.directory.group"
WRITE_SCOPES = [W_GMAIL, W_GMAIL_SEND, W_CAL, W_DRIVE, W_DIR_USER, W_DIR_GROUP]

ALL_SCOPES = [
    S_GMAIL, S_CAL, S_DRIVE, S_TASKS, S_CONTACTS,
    S_DIR_USER, S_DIR_GROUP, S_DIR_OU, S_RPT_AUDIT, S_RPT_USAGE,
]

GOOGLE_EXPORT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}
VALID_ACTIVITY_APPS = {
    "login", "drive", "token", "admin", "calendar", "mobile",
    "groups", "user_accounts", "meet", "chat", "access_transparency",
}

# Per-instance client cache. Safe despite statelessness: it is a pure
# performance optimisation that speeds up warm instances and is simply absent
# on cold ones. No correctness depends on it surviving.
_clients: Dict[tuple, Any] = {}


class WorkspaceError(RuntimeError):
    """Google-side failure with a message written for a human to act on."""


_base_creds: Any = None


def _delegated_credentials(scopes: List[str], subject: str):
    """Credentials that act as `subject`, with no private key on disk.

    Domain-wide delegation needs a JWT signed by the service account. The IAM
    Credentials API signs it (signJwt), so the key stays inside Google. The
    runtime identity needs roles/iam.serviceAccountTokenCreator on the service
    account named here, which on Cloud Run is normally itself.
    """
    global _base_creds
    import google.auth
    from google.auth import iam
    from google.auth.transport import requests as ga_requests
    from google.oauth2 import service_account

    request = ga_requests.Request()
    if _base_creds is None:
        _base_creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _base_creds.valid:
        _base_creds.refresh(request)
    sa_email = SA_EMAIL or getattr(_base_creds, "service_account_email", "")
    if not sa_email or sa_email == "default":
        raise WorkspaceError(
            "The service account is unknown. Set SERVICE_ACCOUNT_EMAIL to the "
            "account that holds domain-wide delegation.")
    signer = iam.Signer(request, _base_creds, sa_email)
    return service_account.Credentials(
        signer, sa_email, "https://oauth2.googleapis.com/token",
        scopes=scopes, subject=subject)


def _svc(api: str, version: str, scopes: List[str], subject: str):
    from googleapiclient.discovery import build

    key = (api, version, subject, tuple(sorted(scopes)))
    if key in _clients:
        return _clients[key]
    client = build(api, version, credentials=_delegated_credentials(scopes, subject),
                   cache_discovery=False)
    if len(_clients) > 256:      # bound memory on a long-lived warm instance
        _clients.clear()
    _clients[key] = client
    return client


def _admin() -> str:
    if not ADMIN_EMAIL:
        raise WorkspaceError("ADMIN_EMAIL is not set on the service.")
    return ADMIN_EMAIL


async def _run(fn):
    """Google's client library is synchronous; keep the event loop free."""
    return await asyncio.to_thread(fn)


def explain_error(exc: Exception, email: Optional[str] = None) -> str:
    """Translate Google's status codes into the actual fix.

    A bare '403' sends people hunting through three consoles. Naming the likely
    cause turns most of these into a sixty-second correction.
    """
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        return f"Google client library not installed: {exc}"
    if isinstance(exc, HttpError):
        status = getattr(exc.resp, "status", None)
        if status == 403:
            return (
                "Permission denied (403). Either a scope is missing from the service "
                "account's domain-wide delegation, or ADMIN_EMAIL lacks the required "
                "admin privilege. Admin console → Security → Access and data control → "
                "API controls → Domain-wide delegation."
            )
        if status == 401:
            return "Unauthorized (401). The service-account key was revoked, or ADMIN_EMAIL is wrong."
        if status == 404:
            return f"Not found (404){f' for {email}' if email else ''}."
        if status == 429:
            return "Rate limited (429) by Google. Retry shortly; harvests back off automatically."
        return f"Google API error {status}: {exc}"
    return f"{type(exc).__name__}: {exc}"


def rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def header(headers: List[Dict[str, str]], name: str) -> str:
    return next(
        (h["value"] for h in headers if h.get("name", "").lower() == name.lower()), ""
    )


def is_internal(address: str) -> bool:
    dom = PRIMARY_DOMAIN.lower()
    return bool(dom) and address.lower().endswith("@" + dom)


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------


async def directory_users(max_results: int = 500, query: Optional[str] = None) -> List[Dict]:
    def call():
        svc = _svc("admin", "directory_v1", [S_DIR_USER], _admin())
        out, page = [], None
        while len(out) < max_results:
            resp = svc.users().list(
                customer=CUSTOMER_ID,
                maxResults=min(500, max_results - len(out)),
                query=query,
                orderBy="email",
                pageToken=page,
            ).execute()
            out.extend(resp.get("users", []))
            page = resp.get("nextPageToken")
            if not page:
                break
        return out

    users = await _run(call)
    return [
        {
            "email": u.get("primaryEmail"),
            "full_name": (u.get("name") or {}).get("fullName"),
            "given_name": (u.get("name") or {}).get("givenName"),
            "org_unit": u.get("orgUnitPath"),
            "title": ((u.get("organizations") or [{}])[0] or {}).get("title"),
            "is_admin": bool(u.get("isAdmin")),
            "is_delegated_admin": bool(u.get("isDelegatedAdmin")),
            "suspended": bool(u.get("suspended")),
            "last_login_ts": u.get("lastLoginTime"),
            "created_ts": u.get("creationTime"),
        }
        for u in users
    ]


async def get_directory_user(email: str) -> Dict[str, Any]:
    def call():
        svc = _svc("admin", "directory_v1", [S_DIR_USER], _admin())
        return svc.users().get(userKey=email).execute()

    return await _run(call)


async def active_users() -> List[str]:
    """Non-suspended mailboxes, preferring the KB roster.

    Reading the roster from D1 rather than Directory on every call is what
    keeps a stateless server cheap: Directory is a slow, quota-limited API and
    the roster changes a few times a year, not a few times a minute. Directory
    remains the fallback so a fresh deployment works before the first harvest.
    """
    try:
        import kb
        rows = await kb.d1(
            "SELECT email FROM people WHERE suspended = 0 ORDER BY email"
        )
        if rows:
            return [r["email"] for r in rows]
    except Exception:
        pass
    return [u["email"] for u in await directory_users() if not u["suspended"]]


async def directory_groups(max_results: int = 200) -> List[Dict]:
    def call():
        svc = _svc("admin", "directory_v1", [S_DIR_GROUP], _admin())
        return svc.groups().list(customer=CUSTOMER_ID, maxResults=max_results).execute()

    resp = await _run(call)
    return [
        {
            "email": g.get("email"), "name": g.get("name"),
            "description": g.get("description"),
            "member_count": g.get("directMembersCount"),
        }
        for g in resp.get("groups", [])
    ]


async def group_members(group_email: str) -> List[Dict]:
    def call():
        svc = _svc("admin", "directory_v1", [S_DIR_GROUP], _admin())
        return svc.members().list(groupKey=group_email, maxResults=200).execute()

    resp = await _run(call)
    return [
        {"email": m.get("email"), "role": m.get("role"), "type": m.get("type")}
        for m in resp.get("members", [])
    ]


async def directory_orgunits() -> List[Dict]:
    def call():
        svc = _svc("admin", "directory_v1", [S_DIR_OU], _admin())
        return svc.orgunits().list(customerId=CUSTOMER_ID, type="all").execute()

    resp = await _run(call)
    return [
        {"path": o.get("orgUnitPath"), "name": o.get("name"),
         "parent": o.get("parentOrgUnitPath")}
        for o in resp.get("organizationUnits", [])
    ]


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


async def activity_report(
    user_email: str = "all", application: str = "login",
    days: int = 7, max_results: int = 100,
) -> List[Dict]:
    if application not in VALID_ACTIVITY_APPS:
        raise WorkspaceError(
            f"'{application}' is not a valid application. Choose from: "
            f"{', '.join(sorted(VALID_ACTIVITY_APPS))}"
        )
    start = datetime.now(timezone.utc) - timedelta(days=days)

    def call():
        svc = _svc("admin", "reports_v1", [S_RPT_AUDIT], _admin())
        return svc.activities().list(
            userKey=user_email, applicationName=application,
            startTime=rfc3339(start), maxResults=max_results,
        ).execute()

    resp = await _run(call)
    out = []
    for item in resp.get("items", []):
        for ev in item.get("events", []):
            out.append(
                {
                    "ts": item.get("id", {}).get("time"),
                    "actor": (item.get("actor") or {}).get("email"),
                    "ip": item.get("ipAddress"),
                    "type": ev.get("type"),
                    "name": ev.get("name"),
                    "params": {
                        p.get("name"): p.get("value") or p.get("boolValue")
                        or p.get("intValue") or p.get("multiValue")
                        for p in ev.get("parameters", [])
                    },
                }
            )
    return out


async def usage_report(user_email: str = "all", date: Optional[str] = None) -> List[Dict]:
    """Usage data lags 2-3 days on Google's side; audit reports do not.
    Use this for trends, activity_report for anything time-sensitive."""
    day = date or (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")

    def call():
        svc = _svc("admin", "reports_v1", [S_RPT_USAGE], _admin())
        return svc.userUsageReport().get(
            userKey=user_email, date=day, maxResults=500
        ).execute()

    resp = await _run(call)
    out = []
    for rec in resp.get("usageReports", []):
        flat = {"date": rec.get("date"), "email": (rec.get("entity") or {}).get("userEmail")}
        for p in rec.get("parameters", []):
            val = p.get("intValue", p.get("stringValue", p.get("boolValue")))
            flat[p.get("name")] = val
        out.append(flat)
    return out


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------


async def gmail_search(
    user_email: str, query: str = "", max_results: int = 25
) -> List[Dict]:
    def call():
        svc = _svc("gmail", "v1", [S_GMAIL], user_email)
        listed = svc.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        out = []
        for m in listed.get("messages", []):
            msg = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["Subject", "From", "To", "Cc", "Date"],
            ).execute()
            h = msg.get("payload", {}).get("headers", [])
            out.append(
                {
                    "id": msg["id"],
                    "thread_id": msg.get("threadId"),
                    "ts": datetime.fromtimestamp(
                        int(msg.get("internalDate", 0)) / 1000, timezone.utc
                    ).isoformat(timespec="seconds"),
                    "subject": header(h, "Subject"),
                    "from": header(h, "From"),
                    "to": header(h, "To"),
                    "cc": header(h, "Cc"),
                    "labels": msg.get("labelIds", []),
                    "snippet": msg.get("snippet", "")[:200],
                    "mailbox": user_email,
                }
            )
        return out

    return await _run(call)


async def gmail_get_message(user_email: str, message_id: str) -> Dict:
    """Full body of one message. Called on demand only — bodies are never
    harvested into the knowledge base."""
    def call():
        svc = _svc("gmail", "v1", [S_GMAIL], user_email)
        msg = svc.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        h = msg.get("payload", {}).get("headers", [])

        def walk(part) -> str:
            if part.get("mimeType") == "text/plain":
                data = (part.get("body") or {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", "replace")
            for sub in part.get("parts", []) or []:
                if text := walk(sub):
                    return text
            return ""

        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "subject": header(h, "Subject"),
            "from": header(h, "From"),
            "to": header(h, "To"),
            "date": header(h, "Date"),
            "body": walk(msg.get("payload", {}))[:20000],
        }

    return await _run(call)


async def org_gmail_search(
    query: str, users: Optional[List[str]] = None,
    max_per_user: int = 10, concurrency: int = 6,
) -> Dict[str, Any]:
    """One query across every active mailbox, merged and date-sorted.

    This is the highest-leverage tool in the set — the difference between
    "search one person's inbox" and "find every mention of this across the company"
    — so it fans out concurrently and tolerates individual mailbox failures
    rather than aborting the whole sweep on one bad account.
    """
    targets = users or await active_users()
    sem = asyncio.Semaphore(concurrency)
    errors: List[str] = []

    async def one(email: str) -> List[Dict]:
        async with sem:
            try:
                return await gmail_search(email, query, max_per_user)
            except Exception as exc:
                errors.append(f"{email}: {explain_error(exc, email)}")
                return []

    batches = await asyncio.gather(*[one(e) for e in targets])
    merged = [m for b in batches for m in b]
    merged.sort(key=lambda m: m.get("ts") or "", reverse=True)
    return {
        "query": query,
        "mailboxes_searched": len(targets),
        "total_hits": len(merged),
        "errors": errors,
        "messages": merged,
    }


# ---------------------------------------------------------------------------
# Calendar / Drive / Tasks / Contacts
# ---------------------------------------------------------------------------


async def calendar_events(
    user_email: str, days_back: int = 0, days_forward: int = 14, max_results: int = 50
) -> List[Dict]:
    now = datetime.now(timezone.utc)

    def call():
        svc = _svc("calendar", "v3", [S_CAL], user_email)
        return svc.events().list(
            calendarId="primary",
            timeMin=rfc3339(now - timedelta(days=days_back)),
            timeMax=rfc3339(now + timedelta(days=days_forward)),
            singleEvents=True, orderBy="startTime", maxResults=max_results,
        ).execute()

    resp = await _run(call)
    out = []
    for e in resp.get("items", []):
        attendees = e.get("attendees", []) or []
        me = next((a for a in attendees if a.get("self")), {})
        start = (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date")
        end = (e.get("end") or {}).get("dateTime") or (e.get("end") or {}).get("date")
        out.append(
            {
                "event_id": e.get("id"),
                "title": e.get("summary"),
                "start": start,
                "end": end,
                "organizer": (e.get("organizer") or {}).get("email"),
                "is_organizer": bool((e.get("organizer") or {}).get("self")),
                "location": e.get("location"),
                "status": e.get("status"),
                "recurring_id": e.get("recurringEventId"),
                "attendee_count": len(attendees),
                "external_count": sum(
                    1 for a in attendees if a.get("email") and not is_internal(a["email"])
                ),
                "response_status": me.get("responseStatus"),
                "attendees": [a.get("email") for a in attendees][:25],
                "person": user_email,
            }
        )
    return out


async def drive_files(
    user_email: str, query: Optional[str] = None, max_results: int = 25
) -> List[Dict]:
    def call():
        svc = _svc("drive", "v3", [S_DRIVE], user_email)
        return svc.files().list(
            q=query, pageSize=max_results, orderBy="modifiedTime desc",
            fields=("files(id,name,mimeType,modifiedTime,createdTime,size,owners(emailAddress),"
                    "parents,shared,webViewLink,lastModifyingUser(emailAddress))"),
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()

    resp = await _run(call)
    return [
        {
            "id": f.get("id"), "name": f.get("name"), "mime_type": f.get("mimeType"),
            "modified": f.get("modifiedTime"), "created": f.get("createdTime"),
            "size": f.get("size"),
            "owner": ((f.get("owners") or [{}])[0] or {}).get("emailAddress"),
            "last_modified_by": (f.get("lastModifyingUser") or {}).get("emailAddress"),
            "parents": f.get("parents", []), "shared": f.get("shared"),
            "link": f.get("webViewLink"),
        }
        for f in resp.get("files", [])
    ]


async def drive_changes(user_email: str, page_token: Optional[str] = None) -> Dict[str, Any]:
    """Incremental Drive changes since a cursor.

    Polling `files.list` would re-read the whole drive every harvest and burn
    quota to learn nothing. The Changes API returns only what moved, which is
    what makes per-hour folder monitoring affordable.
    """
    def call():
        svc = _svc("drive", "v3", [S_DRIVE], user_email)
        token = page_token
        if not token:
            token = svc.changes().getStartPageToken(supportsAllDrives=True).execute()[
                "startPageToken"
            ]
            return {"changes": [], "new_token": token, "bootstrapped": True}
        out, cursor, new_token = [], token, None
        while cursor:
            resp = svc.changes().list(
                pageToken=cursor, pageSize=200,
                includeItemsFromAllDrives=True, supportsAllDrives=True,
                fields=("nextPageToken,newStartPageToken,changes(time,removed,fileId,"
                        "file(id,name,mimeType,size,parents,trashed,shared,"
                        "modifiedTime,createdTime,lastModifyingUser(emailAddress),"
                        "permissions(emailAddress,type,domain)))"),
            ).execute()
            out.extend(resp.get("changes", []))
            new_token = resp.get("newStartPageToken") or new_token
            cursor = resp.get("nextPageToken")
            if len(out) >= 1000:      # bound one harvest; the cursor resumes next run
                new_token = cursor or new_token
                break
        return {"changes": out, "new_token": new_token, "bootstrapped": False}

    return await _run(call)


async def drive_file_text(user_email: str, file_id: str, max_chars: int = 20000) -> Dict:
    def call():
        svc = _svc("drive", "v3", [S_DRIVE], user_email)
        meta = svc.files().get(
            fileId=file_id, fields="id,name,mimeType", supportsAllDrives=True
        ).execute()
        mime = meta.get("mimeType", "")
        if mime in GOOGLE_EXPORT:
            data = svc.files().export(fileId=file_id, mimeType=GOOGLE_EXPORT[mime]).execute()
        elif mime.startswith("text/"):
            data = svc.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
        else:
            return {"name": meta.get("name"), "mime_type": mime,
                    "text": f"(binary type {mime} — not extractable here)"}
        text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
        return {"name": meta.get("name"), "mime_type": mime, "text": text[:max_chars]}

    return await _run(call)


async def tasks_list(user_email: str, max_results: int = 50) -> List[Dict]:
    def call():
        svc = _svc("tasks", "v1", [S_TASKS], user_email)
        out = []
        for tl in svc.tasklists().list(maxResults=20).execute().get("items", []):
            got = svc.tasks().list(
                tasklist=tl["id"], maxResults=max_results, showCompleted=False
            ).execute()
            for t in got.get("items", []):
                out.append({"list": tl.get("title"), "title": t.get("title"),
                            "due": t.get("due"), "status": t.get("status"),
                            "notes": (t.get("notes") or "")[:300]})
        return out

    return await _run(call)


async def contacts_list(user_email: str, max_results: int = 100) -> List[Dict]:
    def call():
        svc = _svc("people", "v1", [S_CONTACTS], user_email)
        resp = svc.people().connections().list(
            resourceName="people/me", pageSize=max_results,
            personFields="names,emailAddresses,organizations,phoneNumbers",
        ).execute()
        out = []
        for p in resp.get("connections", []):
            out.append(
                {
                    "name": ((p.get("names") or [{}])[0] or {}).get("displayName"),
                    "emails": [e.get("value") for e in p.get("emailAddresses", [])],
                    "phones": [x.get("value") for x in p.get("phoneNumbers", [])],
                    "org": ((p.get("organizations") or [{}])[0] or {}).get("name"),
                }
            )
        return out

    return await _run(call)


# ---------------------------------------------------------------------------
# Cross-source collation
# ---------------------------------------------------------------------------


async def person_snapshot(user_email: str) -> Dict[str, Any]:
    """One person across every live source, fetched in parallel.

    Partial failure returns partial data with the error attached, because an
    inaccessible Tasks list should not hide a person's calendar.
    """
    email = user_email.strip().lower()

    async def safe(coro, label):
        try:
            return await coro
        except Exception as exc:
            return {"error": explain_error(exc, email), "source": label}

    directory, mail, cal, drive, tasks = await asyncio.gather(
        safe(get_directory_user(email), "directory"),
        safe(gmail_search(email, "newer_than:7d", 15), "gmail"),
        safe(calendar_events(email, 0, 14, 20), "calendar"),
        safe(drive_files(email, None, 15), "drive"),
        safe(tasks_list(email, 20), "tasks"),
    )
    return {
        "email": email, "generated_at": datetime.now(timezone.utc).isoformat(),
        "directory": directory, "recent_mail": mail,
        "upcoming_calendar": cal, "recent_drive": drive, "open_tasks": tasks,
    }


async def org_overview() -> Dict[str, Any]:
    users = await directory_users()
    active = [u for u in users if not u["suspended"]]
    by_ou: Dict[str, int] = {}
    for u in active:
        by_ou[u.get("org_unit") or "/"] = by_ou.get(u.get("org_unit") or "/", 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_users": len(users),
        "active_users": len(active),
        "suspended_users": len(users) - len(active),
        "admins": [u["email"] for u in active if u["is_admin"]],
        "by_org_unit": by_ou,
        "groups": await directory_groups(),
        "org_units": await directory_orgunits(),
        "quietest": sorted(
            [{"email": u["email"], "last_login": u["last_login_ts"]} for u in active],
            key=lambda x: x["last_login"] or "",
        )[:10],
    }


async def connection_check() -> Dict[str, Any]:
    """Prove every leg of the chain independently.

    Checks are separated by source so a failure names the specific scope to
    fix, instead of reporting one undifferentiated 'connection failed'.
    """
    result: Dict[str, Any] = {
        "admin_email": ADMIN_EMAIL or "(unset)",
        "customer_id": CUSTOMER_ID,
        "primary_domain": PRIMARY_DOMAIN or "(unset)",
        "service_account": SA_EMAIL or "(runtime identity)",
        "key_file": "none (IAM signJwt)",
        "checks": {},
    }
    probes = {
        "directory": lambda: directory_users(max_results=1),
        "reports_audit": lambda: activity_report(_admin(), "login", 7, 1),
        "gmail": lambda: gmail_search(_admin(), "newer_than:30d", 1),
        "calendar": lambda: calendar_events(_admin(), 0, 7, 1),
        "drive": lambda: drive_files(_admin(), None, 1),
    }
    for name, probe in probes.items():
        try:
            await probe()
            result["checks"][name] = "ok"
        except Exception as exc:
            result["checks"][name] = explain_error(exc)
    result["healthy"] = all(v == "ok" for v in result["checks"].values())
    return result
