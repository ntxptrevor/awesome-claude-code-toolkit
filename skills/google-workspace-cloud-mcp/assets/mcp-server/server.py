#!/usr/bin/env python3
"""
server.py: Google Workspace Cloud MCP, a stateless cloud MCP server.

Built on the official modelcontextprotocol/python-sdk low-level Server and
StreamableHTTPSessionManager in stateless mode. It runs only as a remote HTTPS
service. The only way in is Google sign-in.

Every request carries what is needed to serve it: a signed access token names
the person and their role, and an optional signed grant names extra read
permissions. No session table and no auth table exist. Cloud Run can scale to
zero and replace instances at any time.

Four layers:

    auth.py             who the caller is         (Google sign-in, signed tokens)
    policy.py           what the caller may do    (roles, task profiles, grants)
    workspace.py        live reads from Google    (keyless domain-wide delegation)
    workspace_write.py  admin writes to Google    (admin role only)
    kb.py               optional history in D1    (Cloudflare HTTP API)

Every tool call is checked by policy.check() and written to the log as one
JSON line: who, which tool, which accounts, allowed or refused.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from typing import Any, Dict, List

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

import auth
import kb
import policy
import workspace
import workspace_write as ww

SERVER_NAME = "google-workspace-cloud-mcp"
SERVER_VERSION = "3.0.0"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

server: Server = Server(SERVER_NAME)


# ---------------------------------------------------------------------------
# Tool catalogue
# ---------------------------------------------------------------------------

_GRANT = {
    "type": "string",
    "description": "Optional access grant from access_request. Readers pass it "
                   "to reach data outside their own account.",
}
_CONFIRM = {
    "type": "boolean",
    "description": "Must be true. Set it only after the person saw exactly what "
                   "will be sent or deleted and said yes.",
}


def _t(name: str, desc: str, props: Dict[str, Any], required: List[str] | None = None):
    rule = policy.RULES.get(name)
    write = policy.is_write_tool(name)
    props = {**props, "grant": _GRANT}
    if rule and rule.destroys:
        props["confirm"] = _CONFIRM
    return types.Tool(
        name=name,
        description=desc + (" Administrator only." if write else ""),
        inputSchema={
            "type": "object",
            "properties": props,
            "required": required or [],
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(
            readOnlyHint=not write and name != "access_request",
            destructiveHint=bool(rule and rule.destroys),
        ),
    )


_STR = {"type": "string"}
_INT = {"type": "integer"}
_BOOL = {"type": "boolean"}
_LIST = {"type": "array", "items": {"type": "string"}}


TOOLS: List[types.Tool] = [
    # -- live intelligence ---------------------------------------------------
    _t("workspace_connection_check",
       "Verify every leg of the Google connection (directory, reports, gmail, "
       "calendar, drive) and report which scope is failing if any. Call this "
       "first in a session, and first when anything returns a permission error.",
       {}),
    _t("workspace_org_overview",
       "The whole organisation at a glance: user counts, org units, groups, "
       "admins, and the ten people with the oldest last-login.", {}),
    _t("workspace_directory_users",
       "Live roster from Admin Directory: name, email, org unit, title, admin "
       "flag, suspension, last login. Resolve names to emails here before "
       "calling any per-user tool.",
       {"max_results": _INT, "query": {**_STR, "description": "Directory query, e.g. 'orgUnitPath=/Field'"}}),
    _t("workspace_directory_groups", "All groups with member counts.", {"max_results": _INT}),
    _t("workspace_group_members", "Members of one group.",
       {"group_email": _STR}, ["group_email"]),
    _t("workspace_directory_orgunits", "The org-unit tree.", {}),
    _t("workspace_activity_report",
       "Audit events for a user, near real-time. Applications: login, drive, "
       "admin, calendar, token, mobile, groups, user_accounts, meet, chat. Use "
       "this rather than usage_report when recency matters.",
       {"user_email": _STR, "application": _STR, "days": _INT, "max_results": _INT}),
    _t("workspace_usage_report",
       "Per-user daily usage metrics. Google publishes these on a 2-3 day lag, "
       "so treat them as trend data, not current state.",
       {"user_email": _STR, "date": {**_STR, "description": "YYYY-MM-DD"}}),
    _t("gmail_search", "Search one mailbox. Metadata and snippets only.",
       {"user_email": _STR, "query": _STR, "max_results": _INT}, ["user_email"]),
    _t("gmail_get_message", "Full body of one message, on demand.",
       {"user_email": _STR, "message_id": _STR}, ["user_email", "message_id"]),
    _t("org_gmail_search",
       "Run one Gmail query across every active mailbox at once, merged and "
       "date-sorted. This is the tool for 'has anyone heard from X', 'who is "
       "handling Y', or tracing a topic across the company.",
       {"query": _STR, "users": {"type": "array", "items": _STR},
        "max_per_user": _INT}, ["query"]),
    _t("calendar_list_events", "Events for one user across a window.",
       {"user_email": _STR, "days_back": _INT, "days_forward": _INT,
        "max_results": _INT}, ["user_email"]),
    _t("drive_list_files", "Recent or searched Drive files for one user.",
       {"user_email": _STR, "query": {**_STR, "description": "Drive query syntax"},
        "max_results": _INT}, ["user_email"]),
    _t("drive_get_file_text", "Extract text from a Doc, Sheet, Slide, or text file.",
       {"user_email": _STR, "file_id": _STR, "max_chars": _INT},
       ["user_email", "file_id"]),
    _t("tasks_list", "Open tasks for one user.", {"user_email": _STR}, ["user_email"]),
    _t("contacts_list", "Personal contacts for one user.", {"user_email": _STR}, ["user_email"]),
    _t("workspace_person_snapshot",
       "One person across every live source at once — directory, recent mail, "
       "upcoming calendar, recent Drive, open tasks.",
       {"user_email": _STR}, ["user_email"]),

    # -- knowledge base ------------------------------------------------------
    _t("kb_health",
       "Knowledge base status: row counts per table, last successful harvest "
       "per source, open flag counts by severity. Check this if KB answers "
       "look stale or empty.", {}),
    _t("kb_sql",
       "Run a read-only SELECT against the knowledge base. This is the most "
       "powerful tool here — the full schema is in references/kb-schema.md and "
       "arbitrary joins and aggregations are allowed. Filter on indexed columns "
       "(ts, person, project_id, thread_id, day) because D1 bills rows scanned, "
       "not rows returned. A LIMIT is added if you omit one.",
       {"sql": _STR, "limit": _INT}, ["sql"]),
    _t("kb_search",
       "Text search across threads, file names, meeting titles, flags, and "
       "people. Use before kb_sql when you know a keyword but not the schema.",
       {"term": _STR, "days": _INT, "limit": _INT}, ["term"]),
    _t("kb_person_timeline",
       "Everything recorded about one person over a window: daily rollups, "
       "recent communications, meetings, Drive activity, open flags.",
       {"email": _STR, "days": _INT}, ["email"]),
    _t("kb_project_activity",
       "Everything recorded against one project: communications, folder "
       "changes, meetings, open flags, and unanswered inbound threads.",
       {"project_id": _STR, "days": _INT}, ["project_id"]),
    _t("kb_flags_list",
       "The flag queue — detected signals awaiting attention, worst first. "
       "Filter by status (open/acknowledged/resolved/dismissed/all), severity, "
       "person, or project.",
       {"status": _STR, "severity": _STR, "person": _STR, "project_id": _STR,
        "limit": _INT}),
    _t("kb_flag_update",
       "Move a flag through its lifecycle and record who did it. Every "
       "transition is written to an append-only audit trail.",
       {"flag_id": _STR, "status": _STR, "note": _STR}, ["flag_id", "status"]),
    _t("kb_flag_create",
       "Log a signal by hand, for something noticed outside the automated "
       "detectors. Deduplicated on dedupe_key so repeats bump a counter rather "
       "than filling the queue.",
       {"title": _STR, "detail": _STR, "severity": _STR, "person": _STR,
        "project_id": _STR, "dedupe_key": _STR}, ["title", "detail"]),
    _t("kb_project_upsert",
       "Register or update a project so communications, folder changes, and "
       "meetings get tagged to it automatically on the next harvest. Matching "
       "is by Drive folder id, counterparty domain, or subject keyword.",
       {"project_id": _STR, "name": _STR, "drive_folder_id": _STR,
        "match_domains": {"type": "array", "items": _STR},
        "match_keywords": {"type": "array", "items": _STR},
        "owner_email": _STR, "status": _STR, "contract_value": {"type": "number"}},
       ["project_id", "name"]),
    # -- access ----------------------------------------------------------------
    _t("access_whoami",
       "Who is signed in, their role, what they may read without a grant, and "
       "the task profiles that need no approval. Call this first in a session.",
       {}),
    _t("access_request",
       "Ask for read access outside your own account. Name the task, the "
       "permissions, the target accounts and the reason. A request that matches "
       "a task profile returns a grant at once. Any other request is emailed to "
       "an administrator, and the grant arrives by email after approval. "
       "Permissions: directory.read, reports.read, gmail.read, calendar.read, "
       "drive.read, tasks.read, contacts.read, kb.read. Write access cannot be "
       "requested.",
       {"task": {**_STR, "description": "A task profile name, or a short task title."},
        "permissions": _LIST, "targets": {**_LIST, "description":
            "Account emails, or [\"*\"] for the whole organisation."},
        "reason": _STR},
       ["task", "permissions", "reason"]),
    # -- admin writes: Gmail ---------------------------------------------------
    _t("gmail_send", "Send an email from one mailbox.",
       {"user_email": _STR, "to": _LIST, "subject": _STR, "body": _STR, "cc": _LIST},
       ["user_email", "to", "subject", "body"]),
    _t("gmail_create_draft", "Save a draft in one mailbox. Nothing is sent.",
       {"user_email": _STR, "to": _LIST, "subject": _STR, "body": _STR, "cc": _LIST},
       ["user_email", "to", "subject", "body"]),
    _t("gmail_modify_labels",
       "Add or remove label ids on a message, for example UNREAD, STARRED, INBOX.",
       {"user_email": _STR, "message_id": _STR, "add": _LIST, "remove": _LIST},
       ["user_email", "message_id"]),
    _t("gmail_trash", "Move a message to Trash. Google keeps it 30 days.",
       {"user_email": _STR, "message_id": _STR}, ["user_email", "message_id"]),
    _t("gmail_untrash", "Take a message out of Trash.",
       {"user_email": _STR, "message_id": _STR}, ["user_email", "message_id"]),
    # -- admin writes: Calendar ------------------------------------------------
    _t("calendar_create_event",
       "Create an event on one person's primary calendar. start and end are "
       "YYYY-MM-DD for all-day, or RFC 3339 date-times.",
       {"user_email": _STR, "summary": _STR, "start": _STR, "end": _STR,
        "attendees": _LIST, "description": _STR, "location": _STR,
        "time_zone": _STR, "notify": _BOOL},
       ["user_email", "summary", "start", "end"]),
    _t("calendar_update_event",
       "Change an event. `changes` may hold summary, description, location, "
       "start, end, attendees.",
       {"user_email": _STR, "event_id": _STR, "changes": {"type": "object"},
        "time_zone": _STR, "notify": _BOOL},
       ["user_email", "event_id", "changes"]),
    _t("calendar_delete_event", "Delete an event from one person's calendar.",
       {"user_email": _STR, "event_id": _STR, "notify": _BOOL},
       ["user_email", "event_id"]),
    # -- admin writes: Drive ---------------------------------------------------
    _t("drive_create_folder", "Create a folder in one person's Drive.",
       {"user_email": _STR, "name": _STR, "parent_id": _STR}, ["user_email", "name"]),
    _t("drive_update_file", "Rename a file, move it to another folder, or both.",
       {"user_email": _STR, "file_id": _STR, "name": _STR, "move_to_folder_id": _STR},
       ["user_email", "file_id"]),
    _t("drive_share",
       "Share a file with one address as reader, commenter or writer. The "
       "result says whether the address is outside the organisation.",
       {"user_email": _STR, "file_id": _STR, "share_with": _STR, "role": _STR,
        "notify": _BOOL},
       ["user_email", "file_id", "share_with"]),
    _t("drive_unshare", "Remove one sharing permission from a file.",
       {"user_email": _STR, "file_id": _STR, "permission_id": _STR},
       ["user_email", "file_id", "permission_id"]),
    _t("drive_trash", "Move a file to Trash. Google keeps it 30 days.",
       {"user_email": _STR, "file_id": _STR}, ["user_email", "file_id"]),
    _t("drive_untrash", "Take a file out of Trash.",
       {"user_email": _STR, "file_id": _STR}, ["user_email", "file_id"]),
    # -- admin writes: Directory -----------------------------------------------
    _t("directory_create_user",
       "Create a Workspace account. The password is random and unseen. Send a "
       "reset from the Admin console afterwards.",
       {"email": _STR, "given_name": _STR, "family_name": _STR, "org_unit_path": _STR},
       ["email", "given_name", "family_name"]),
    _t("directory_update_user",
       "Change an account. `changes` may hold suspended (true or false), "
       "org_unit_path, given_name, family_name, title.",
       {"user_email": _STR, "changes": {"type": "object"}}, ["user_email", "changes"]),
    _t("directory_delete_user",
       "Delete an account. Restore is possible for 20 days in the Admin console.",
       {"user_email": _STR}, ["user_email"]),
    _t("directory_create_group", "Create a group.",
       {"email": _STR, "name": _STR, "description": _STR}, ["email", "name"]),
    _t("directory_delete_group", "Delete a group.", {"group_email": _STR}, ["group_email"]),
    _t("directory_add_group_member", "Add a member to a group.",
       {"group_email": _STR, "member_email": _STR, "role": _STR},
       ["group_email", "member_email"]),
    _t("directory_remove_group_member", "Remove a member from a group.",
       {"group_email": _STR, "member_email": _STR}, ["group_email", "member_email"]),
]



def _caller() -> Dict[str, Any]:
    """The claims of the person behind the current MCP request.

    Read from the HTTP request that carried the call, and verified again here.
    The check is a local signature check, so it costs no network call. Identity
    is never held in a module variable: two people calling at the same moment
    on one instance cannot be confused with each other.
    """
    request = server.request_context.request
    if request is None:
        raise auth.AuthError("unauthorized", "No HTTP request in context.", 401)
    return auth.authenticate(request)


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    visible = policy.visible_tools(_caller().get("role", ""))
    return [t for t in TOOLS if t.name in visible]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def _s(a: Dict[str, Any], k: str, default: Any = None) -> Any:
    v = a.get(k, default)
    return v.strip().lower() if isinstance(v, str) and k.endswith("email") else v


async def _dispatch(name: str, a: Dict[str, Any], caller: Dict[str, Any]) -> Any:
    # access
    if name == "access_whoami":
        return policy.whoami(caller, a.get("grant"))
    if name == "access_request":
        return await policy.request_access(
            caller, a.get("task", ""), a.get("permissions", []),
            a.get("targets", []), a.get("reason", ""))
    # live intelligence
    if name == "workspace_connection_check":
        return await workspace.connection_check()
    if name == "workspace_org_overview":
        return await workspace.org_overview()
    if name == "workspace_directory_users":
        return await workspace.directory_users(a.get("max_results", 200), a.get("query"))
    if name == "workspace_directory_groups":
        return await workspace.directory_groups(a.get("max_results", 200))
    if name == "workspace_group_members":
        return await workspace.group_members(_s(a, "group_email"))
    if name == "workspace_directory_orgunits":
        return await workspace.directory_orgunits()
    if name == "workspace_activity_report":
        return await workspace.activity_report(
            _s(a, "user_email", "all"), a.get("application", "login"),
            a.get("days", 7), a.get("max_results", 100))
    if name == "workspace_usage_report":
        return await workspace.usage_report(_s(a, "user_email", "all"), a.get("date"))
    if name == "gmail_search":
        return await workspace.gmail_search(
            _s(a, "user_email"), a.get("query", ""), a.get("max_results", 25))
    if name == "gmail_get_message":
        return await workspace.gmail_get_message(_s(a, "user_email"), a["message_id"])
    if name == "org_gmail_search":
        return await workspace.org_gmail_search(
            a["query"], a.get("users"), a.get("max_per_user", 10))
    if name == "calendar_list_events":
        return await workspace.calendar_events(
            _s(a, "user_email"), a.get("days_back", 0),
            a.get("days_forward", 14), a.get("max_results", 50))
    if name == "drive_list_files":
        return await workspace.drive_files(
            _s(a, "user_email"), a.get("query"), a.get("max_results", 25))
    if name == "drive_get_file_text":
        return await workspace.drive_file_text(
            _s(a, "user_email"), a["file_id"], a.get("max_chars", 20000))
    if name == "tasks_list":
        return await workspace.tasks_list(_s(a, "user_email"))
    if name == "contacts_list":
        return await workspace.contacts_list(_s(a, "user_email"))
    if name == "workspace_person_snapshot":
        return await workspace.person_snapshot(_s(a, "user_email"))

    # knowledge base
    if name == "kb_health":
        return await kb.kb_health()
    if name == "kb_sql":
        return await kb.sql_query(a["sql"], a.get("limit", 200))
    if name == "kb_search":
        return await kb.search(a["term"], a.get("days", 90), a.get("limit", 50))
    if name == "kb_person_timeline":
        return await kb.person_timeline(_s(a, "email"), a.get("days", 30))
    if name == "kb_project_activity":
        return await kb.project_activity(a["project_id"], a.get("days", 30))
    if name == "kb_flags_list":
        return await kb.flags_list(
            a.get("status", "open"), a.get("severity"), a.get("person"),
            a.get("project_id"), a.get("limit", 100))
    if name == "kb_flag_update":
        return await kb.flag_update(
            a["flag_id"], a["status"],
            caller.get("sub", "unknown"), a.get("note"))
    if name == "kb_flag_create":
        key = a.get("dedupe_key") or f"manual:{a['title'][:60]}"
        flag_id = await kb.flag_upsert(
            "manual", key, a["title"], a["detail"], a.get("severity", "medium"),
            a.get("person"), a.get("project_id"))
        return {"flag_id": flag_id, "status": "open"}
    if name == "kb_project_upsert":
        await kb.d1_write(
            """INSERT INTO projects (project_id, name, status, drive_folder_id,
               match_domains, match_keywords, owner_email, contract_value, created_ts)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(project_id) DO UPDATE SET
                 name=excluded.name, status=excluded.status,
                 drive_folder_id=COALESCE(excluded.drive_folder_id, projects.drive_folder_id),
                 match_domains=COALESCE(excluded.match_domains, projects.match_domains),
                 match_keywords=COALESCE(excluded.match_keywords, projects.match_keywords),
                 owner_email=COALESCE(excluded.owner_email, projects.owner_email),
                 contract_value=COALESCE(excluded.contract_value, projects.contract_value)""",
            [a["project_id"], a["name"], a.get("status", "active"),
             a.get("drive_folder_id"), a.get("match_domains"), a.get("match_keywords"),
             a.get("owner_email"), a.get("contract_value"), kb.utcnow()])
        return {"project_id": a["project_id"], "saved": True}

    # admin writes
    u = _s(a, "user_email")
    if name == "gmail_send":
        return await ww.gmail_send(u, a["to"], a["subject"], a["body"], a.get("cc"))
    if name == "gmail_create_draft":
        return await ww.gmail_create_draft(u, a["to"], a["subject"], a["body"], a.get("cc"))
    if name == "gmail_modify_labels":
        return await ww.gmail_modify_labels(u, a["message_id"], a.get("add"), a.get("remove"))
    if name in ("gmail_trash", "gmail_untrash"):
        return await ww.gmail_trash(u, a["message_id"], restore=name == "gmail_untrash")
    if name == "calendar_create_event":
        return await ww.calendar_create_event(
            u, a["summary"], a["start"], a["end"], a.get("attendees"),
            a.get("description"), a.get("location"), a.get("time_zone"),
            bool(a.get("notify")))
    if name == "calendar_update_event":
        return await ww.calendar_update_event(
            u, a["event_id"], a["changes"], a.get("time_zone"), bool(a.get("notify")))
    if name == "calendar_delete_event":
        return await ww.calendar_delete_event(u, a["event_id"], bool(a.get("notify")))
    if name == "drive_create_folder":
        return await ww.drive_create_folder(u, a["name"], a.get("parent_id"))
    if name == "drive_update_file":
        return await ww.drive_update_file(
            u, a["file_id"], a.get("name"), a.get("move_to_folder_id"))
    if name == "drive_share":
        return await ww.drive_share(
            u, a["file_id"], a["share_with"].strip().lower(), a.get("role", "reader"),
            bool(a.get("notify")))
    if name == "drive_unshare":
        return await ww.drive_unshare(u, a["file_id"], a["permission_id"])
    if name in ("drive_trash", "drive_untrash"):
        return await ww.drive_trash(u, a["file_id"], restore=name == "drive_untrash")
    if name == "directory_create_user":
        return await ww.directory_create_user(
            _s(a, "email"), a["given_name"], a["family_name"], a.get("org_unit_path"))
    if name == "directory_update_user":
        return await ww.directory_update_user(u, a["changes"])
    if name == "directory_delete_user":
        return await ww.directory_delete_user(u)
    if name == "directory_create_group":
        return await ww.directory_create_group(_s(a, "email"), a["name"], a.get("description"))
    if name == "directory_delete_group":
        return await ww.directory_delete_group(_s(a, "group_email"))
    if name in ("directory_add_group_member", "directory_remove_group_member"):
        return await ww.directory_group_member(
            _s(a, "group_email"), _s(a, "member_email"),
            remove=name == "directory_remove_group_member", role=a.get("role", "MEMBER"))

    raise ValueError(f"Unknown tool: {name}")


def _audit(caller: Dict[str, Any], tool: str, args: Dict[str, Any], outcome: str,
           started: float) -> None:
    """One JSON line per call. Cloud Logging keeps it; the server keeps nothing."""
    targets = {k: args[k] for k in ("user_email", "users", "email", "group_email",
                                    "member_email", "share_with") if k in args}
    print(json.dumps({
        "audit": "tool_call", "who": caller.get("sub"), "role": caller.get("role"),
        "tool": tool, "targets": targets, "write": policy.is_write_tool(tool),
        "grant": bool(args.get("grant")), "outcome": outcome,
        "ms": int((time.monotonic() - started) * 1000),
    }, default=str), flush=True)


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.ContentBlock]:
    """Errors come back as readable text, so the model can tell the person
    what to fix. Policy refusals say how to get access."""
    args, started = arguments or {}, time.monotonic()
    caller = _caller()
    try:
        policy.check(caller, name, args)
    except policy.PolicyError as exc:
        _audit(caller, name, args, "refused", started)
        return [types.TextContent(type="text", text=f"Access: {exc}")]
    try:
        result = await _dispatch(name, args, caller)
    except (kb.KBError, workspace.WorkspaceError, policy.PolicyError, ValueError) as exc:
        _audit(caller, name, args, "error", started)
        return [types.TextContent(type="text", text=f"Error: {exc}")]
    except Exception as exc:  # noqa: BLE001
        _audit(caller, name, args, "error", started)
        return [types.TextContent(
            type="text", text=f"Error: {workspace.explain_error(exc)}")]
    _audit(caller, name, args, "ok", started)
    return [types.TextContent(
        type="text", text=json.dumps(result, indent=2, default=str))]


# ---------------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------------

session_manager = StreamableHTTPSessionManager(
    app=server,
    event_store=None,       # no resumability store: nothing to resume when stateless
    json_response=True,     # plain JSON responses; no SSE stream to hold open
    stateless=True,
)


async def mcp_asgi(scope, receive, send):
    """Auth gate in front of the MCP endpoint.

    Raw ASGI, so a 401 can carry the WWW-Authenticate resource_metadata header.
    That header tells the client where to sign in.
    """
    try:
        auth.authenticate(Request(scope, receive))
    except auth.AuthError as exc:
        await auth.unauthorized_response(exc)(scope, receive, send)
        return
    await session_manager.handle_request(scope, receive, send)


async def healthz(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


async def readyz(request: Request) -> JSONResponse:
    """Reports which settings are present. No values, no auth needed."""
    return JSONResponse({
        "server": SERVER_NAME, "version": SERVER_VERSION, "stateless": True,
        "auth_configured": bool(auth.GOOGLE_CLIENT_ID and auth.GOOGLE_CLIENT_SECRET
                                and len(auth.JWT_SIGNING_KEY) >= 32),
        "domain_set": bool(auth.PRIMARY_DOMAIN),
        "admins_configured": len(auth.ADMIN_EMAILS),
        "delegation_subject_set": bool(workspace.ADMIN_EMAIL),
        "kb_configured": bool(kb.CF_ACCOUNT_ID and kb.CF_DATABASE_ID and kb.CF_API_TOKEN),
        "public_url_set": bool(auth.PUBLIC_URL),
    })


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with session_manager.run():
        yield


app = Starlette(
    debug=False,
    lifespan=lifespan,
    routes=[
        Route("/healthz", healthz),
        Route("/readyz", readyz),
        Route("/.well-known/oauth-authorization-server", auth.metadata),
        Route("/.well-known/oauth-protected-resource", auth.protected_resource_metadata),
        Route("/.well-known/oauth-protected-resource/mcp", auth.protected_resource_metadata),
        Route("/register", auth.register, methods=["POST"]),
        Route("/authorize", auth.authorize),
        Route("/auth/callback", auth.callback),
        Route("/token", auth.token, methods=["POST"]),
        Route("/access/review", policy.review),
        Route("/access/decide", policy.decide, methods=["POST"]),
        Mount("/mcp", app=mcp_asgi),
    ],
)


def main() -> None:
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info",
                proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
