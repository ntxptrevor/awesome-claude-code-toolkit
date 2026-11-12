#!/usr/bin/env python3
"""
policy.py: what a signed-in person may do.

Two roles exist (see auth.py):

    admin    every tool, on every account: read, write and delete.
    reader   read tools only, limited as follows.

A reader may always:
  * read the company directory (names, groups, org units);
  * read their own mailbox, calendar, Drive, tasks and contacts.

A reader needs a GRANT for anything else, for example another person's
calendar or an organisation-wide mail search. A grant is a signed token that
names one person, a set of permissions, a set of target accounts and an expiry.
The reader passes it in the `grant` argument of a tool call.

A grant is issued in one of two ways:
  1. The request matches a task profile. A profile lists the permissions a
     named task needs. The server issues the grant at once.
  2. An admin approves it. The server emails each admin a link. The admin
     signs in with Google and presses Approve. The server then emails the
     grant to the reader.

Write and delete permissions can never be granted. They belong to the admin
role alone.

Nothing here is stored. The request, the approval and the grant are signed
tokens, checked with the signing key on every call.
"""

from __future__ import annotations

import html
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

from starlette.requests import Request
from starlette.responses import HTMLResponse

import auth

ORG = "*"   # target meaning "every account in the organisation"

READ_PERMS = {
    "directory.read", "reports.read", "gmail.read", "calendar.read",
    "drive.read", "tasks.read", "contacts.read", "kb.read",
}
WRITE_PERMS = {
    "gmail.write", "calendar.write", "drive.write", "directory.write",
    "kb.write", "admin.diagnostics",
}
# Read permissions a reader holds with no grant and no target check.
BASE_PERMS = {"directory.read"}
# Read permissions a reader holds over their own account with no grant.
SELF_PERMS = READ_PERMS - {"reports.read"}

GRANT_TTL_DEFAULT = 8 * 3600
GRANT_TTL_MAX = 24 * 3600
REQUEST_TTL = 24 * 3600

# Task profiles: a named task and the most it may read without an approval.
# Replace or extend with the TASK_PROFILES environment variable (JSON, same shape).
DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "schedule-coordination": {
        "description": "Find meeting times across the team.",
        "perms": ["calendar.read"],
        "targets": [ORG],
        "ttl": GRANT_TTL_DEFAULT,
    },
}


def load_profiles() -> Dict[str, Dict[str, Any]]:
    raw = os.environ.get("TASK_PROFILES", "").strip()
    if not raw:
        return DEFAULT_PROFILES
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return DEFAULT_PROFILES
    out: Dict[str, Dict[str, Any]] = {}
    for name, p in (data or {}).items():
        perms = [x for x in p.get("perms", []) if x in READ_PERMS]
        if perms:
            out[str(name)] = {
                "description": str(p.get("description", "")),
                "perms": perms,
                "targets": [str(t).lower() for t in p.get("targets", [ORG])],
                "ttl": min(int(p.get("ttl", GRANT_TTL_DEFAULT)), GRANT_TTL_MAX),
            }
    return out


class PolicyError(Exception):
    """Access refused. The message tells the caller how to get access."""


@dataclass(frozen=True)
class Rule:
    """What one tool needs.

    perms      every permission the tool uses.
    target     name of the argument that holds the account(s) the tool reads,
               ORG when the tool always spans the organisation, or None when
               no person's data is involved.
    default    target used when the argument is absent ("all" means ORG).
    destroys   True when the tool deletes or sends something. The caller must
               pass confirm=true.
    """
    perms: tuple
    target: Optional[str] = None
    default: Optional[str] = None
    destroys: bool = False


def R(*perms: str, target: Optional[str] = None, default: Optional[str] = None,
      destroys: bool = False) -> Rule:
    return Rule(tuple(perms), target, default, destroys)


RULES: Dict[str, Rule] = {
    # access tools: open to every signed-in person
    "access_whoami": R(),
    "access_request": R(),
    # directory
    "workspace_org_overview": R("directory.read"),
    "workspace_directory_users": R("directory.read"),
    "workspace_directory_groups": R("directory.read"),
    "workspace_group_members": R("directory.read"),
    "workspace_directory_orgunits": R("directory.read"),
    # reports
    "workspace_activity_report": R("reports.read", target="user_email", default="all"),
    "workspace_usage_report": R("reports.read", target="user_email", default="all"),
    # per-person reads
    "gmail_search": R("gmail.read", target="user_email"),
    "gmail_get_message": R("gmail.read", target="user_email"),
    "org_gmail_search": R("gmail.read", target="users", default="all"),
    "calendar_list_events": R("calendar.read", target="user_email"),
    "drive_list_files": R("drive.read", target="user_email"),
    "drive_get_file_text": R("drive.read", target="user_email"),
    "tasks_list": R("tasks.read", target="user_email"),
    "contacts_list": R("contacts.read", target="user_email"),
    "workspace_person_snapshot": R(
        "directory.read", "gmail.read", "calendar.read", "drive.read", "tasks.read",
        target="user_email"),
    # knowledge base reads
    "kb_health": R("kb.read", target=ORG),
    "kb_sql": R("kb.read", target=ORG),
    "kb_search": R("kb.read", target=ORG),
    "kb_person_timeline": R("kb.read", target="email"),
    "kb_project_activity": R("kb.read", target=ORG),
    "kb_flags_list": R("kb.read", target=ORG),
    # admin only below this line
    "workspace_connection_check": R("admin.diagnostics"),
    "kb_flag_update": R("kb.write"),
    "kb_flag_create": R("kb.write"),
    "kb_project_upsert": R("kb.write"),
    "gmail_send": R("gmail.write", target="user_email", destroys=True),
    "gmail_create_draft": R("gmail.write", target="user_email"),
    "gmail_modify_labels": R("gmail.write", target="user_email"),
    "gmail_trash": R("gmail.write", target="user_email", destroys=True),
    "gmail_untrash": R("gmail.write", target="user_email"),
    "calendar_create_event": R("calendar.write", target="user_email"),
    "calendar_update_event": R("calendar.write", target="user_email"),
    "calendar_delete_event": R("calendar.write", target="user_email", destroys=True),
    "drive_create_folder": R("drive.write", target="user_email"),
    "drive_update_file": R("drive.write", target="user_email"),
    "drive_share": R("drive.write", target="user_email"),
    "drive_unshare": R("drive.write", target="user_email", destroys=True),
    "drive_trash": R("drive.write", target="user_email", destroys=True),
    "drive_untrash": R("drive.write", target="user_email"),
    "directory_create_user": R("directory.write"),
    "directory_update_user": R("directory.write", target="user_email"),
    "directory_delete_user": R("directory.write", target="user_email", destroys=True),
    "directory_create_group": R("directory.write"),
    "directory_delete_group": R("directory.write", destroys=True),
    "directory_add_group_member": R("directory.write"),
    "directory_remove_group_member": R("directory.write", destroys=True),
}


def is_write_tool(name: str) -> bool:
    rule = RULES.get(name)
    return bool(rule and set(rule.perms) & WRITE_PERMS)


def visible_tools(role: str) -> Set[str]:
    """Readers do not see admin tools in the tool list at all."""
    if role == auth.ROLE_ADMIN:
        return set(RULES)
    return {n for n in RULES if not is_write_tool(n)}


def _targets(rule: Rule, args: Dict[str, Any]) -> Set[str]:
    """The accounts a call touches. An empty set means no person's data."""
    if rule.target is None:
        return set()
    if rule.target == ORG:
        return {ORG}
    value = args.get(rule.target)
    if value in (None, "", []):
        value = rule.default
    if value is None:
        raise PolicyError(f"The argument '{rule.target}' is required.")
    values = value if isinstance(value, list) else [value]
    out = {str(v).strip().lower() for v in values if str(v).strip()}
    return {ORG} if (not out or "all" in out) else out


def _grant_claims(token: str, email: str) -> Dict[str, Any]:
    try:
        claims = auth.unsign(token, "grant")
    except auth.AuthError as exc:
        raise PolicyError(f"The grant is not valid: {exc.description} "
                          "Call access_request for a new one.")
    if claims.get("sub") != email:
        raise PolicyError("This grant was issued to another person.")
    return claims


def check(claims: Dict[str, Any], tool: str, args: Dict[str, Any]) -> None:
    """Raise PolicyError unless this caller may run this tool with these arguments.

    A tool with no rule is refused. A new tool is closed until someone writes
    its rule.
    """
    rule = RULES.get(tool)
    if rule is None:
        raise PolicyError(f"No access rule exists for '{tool}'. The call is refused.")
    email, role = claims.get("sub", ""), claims.get("role")
    targets = _targets(rule, args)

    if role == auth.ROLE_ADMIN:
        if rule.destroys and args.get("confirm") is not True:
            shown = ", ".join(sorted(targets)) or "the directory"
            raise PolicyError(
                f"'{tool}' sends or deletes data on {shown}. Show the person exactly "
                "what will happen, get a yes, then call again with confirm=true.")
        return

    if role != auth.ROLE_READER:
        raise PolicyError("Unknown role. Sign in again.")
    needed = set(rule.perms)
    if needed & WRITE_PERMS:
        raise PolicyError("Read-only access. Only an administrator can run this tool.")

    grant: Dict[str, Any] = {}
    if args.get("grant"):
        grant = _grant_claims(str(args["grant"]), email)
    g_perms = set(grant.get("perms", []))
    g_targets = set(grant.get("targets", []))

    def covered(perm: str) -> bool:
        if not targets:
            return perm in BASE_PERMS or perm in g_perms
        if perm in BASE_PERMS:
            return True
        if targets == {email} and perm in SELF_PERMS:
            return True
        return perm in g_perms and (ORG in g_targets or targets <= g_targets)

    missing = sorted(p for p in needed if not covered(p))
    if missing:
        who = "the whole organisation" if ORG in targets else ", ".join(sorted(targets))
        raise PolicyError(
            f"Access refused: {', '.join(missing)} on {who or 'this data'} is outside "
            "your permissions. Call access_request with the task, these permissions, "
            "these targets and a reason. Pass the grant it returns in the `grant` argument.")


# ---------------------------------------------------------------------------
# Requests and grants
# ---------------------------------------------------------------------------

def _clean(perms: Iterable[str], targets: Iterable[str]) -> tuple:
    perms = sorted({str(p).strip().lower() for p in perms or []})
    targets = sorted({str(t).strip().lower() for t in targets or []})
    if not perms:
        raise PolicyError("List at least one permission.")
    bad = [p for p in perms if p not in READ_PERMS]
    if bad:
        raise PolicyError(
            f"These cannot be granted: {', '.join(bad)}. Grants cover read permissions "
            f"only: {', '.join(sorted(READ_PERMS))}.")
    if not targets or "all" in targets:
        targets = [ORG]
    for t in targets:
        if t != ORG and auth.role_for(t) is None:
            raise PolicyError(f"'{t}' is not an account in this organisation.")
    if len(targets) > 50:
        raise PolicyError("Name 50 accounts at most, or ask for the whole organisation.")
    return perms, targets


def mint_grant(email: str, perms: List[str], targets: List[str], task: str,
               ttl: int, approver: str) -> str:
    return auth.sign("grant", min(ttl, GRANT_TTL_MAX), sub=email, perms=perms,
                     targets=targets, task=task[:120], by=approver)


async def request_access(claims: Dict[str, Any], task: str, perms: List[str],
                         targets: List[str], reason: str) -> Dict[str, Any]:
    """Issue a grant when the request matches a task profile, else ask an admin."""
    email = claims["sub"]
    if claims.get("role") == auth.ROLE_ADMIN:
        return {"status": "not_needed", "detail": "Administrators already hold every permission."}
    task, reason = (task or "").strip(), (reason or "").strip()
    if not task or len(reason) < 10:
        raise PolicyError("Give the task and a reason of at least 10 characters.")
    perms, targets = _clean(perms, targets)

    profile = load_profiles().get(task)
    if profile:
        p_targets = set(profile["targets"])
        if set(perms) <= set(profile["perms"]) and (
            ORG in p_targets or set(targets) <= p_targets
        ):
            return {
                "status": "granted",
                "grant": mint_grant(email, perms, targets, task, profile["ttl"],
                                    f"profile:{task}"),
                "expires_in_seconds": profile["ttl"],
                "use": "Pass this value in the `grant` argument of each tool call.",
            }

    if not auth.ADMIN_EMAILS:
        raise PolicyError("No administrator is configured to approve requests.")
    token = auth.sign("access-request", REQUEST_TTL, sub=email, perms=perms,
                      targets=targets, task=task[:120], reason=reason[:500])
    link = f"{auth.PUBLIC_URL}/access/review?rt={token}"
    body = (
        f"{email} asks for read access through Workspace Cloud MCP.\n\n"
        f"Task:        {task[:120]}\n"
        f"Permissions: {', '.join(perms)}\n"
        f"Accounts:    {'the whole organisation' if ORG in targets else ', '.join(targets)}\n"
        f"Reason:      {reason[:500]}\n\n"
        f"Review, then approve or deny (Google sign-in required, link valid 24 hours):\n"
        f"{link}\n\n"
        "An approved grant is read-only and expires 8 hours after approval.\n"
    )
    import workspace_write
    for admin in sorted(auth.ADMIN_EMAILS):
        await workspace_write.send_system_mail(admin, f"Access request from {email}", body)
    return {
        "status": "pending_approval",
        "detail": "An administrator received the request by email. After approval "
                  "the grant arrives in your inbox. Pass it in the `grant` argument.",
        "profiles_that_need_no_approval": {
            k: {"perms": v["perms"], "description": v["description"]}
            for k, v in load_profiles().items()
        },
    }


def whoami(claims: Dict[str, Any], grant: Optional[str]) -> Dict[str, Any]:
    email, role = claims["sub"], claims.get("role")
    out: Dict[str, Any] = {"email": email, "role": role}
    if role == auth.ROLE_ADMIN:
        out["permissions"] = "Every tool on every account: read, write and delete."
        return out
    out["without_a_grant"] = {
        "any_account": sorted(BASE_PERMS),
        "own_account_only": sorted(SELF_PERMS),
    }
    out["task_profiles"] = {
        k: {"perms": v["perms"], "targets": v["targets"], "description": v["description"]}
        for k, v in load_profiles().items()
    }
    if grant:
        g = _grant_claims(grant, email)
        out["grant"] = {k: g.get(k) for k in ("perms", "targets", "task", "by", "exp")}
    return out


# ---------------------------------------------------------------------------
# Approval pages. The approver signs in with Google first (auth.callback sends
# them here), so a mail scanner that opens the link cannot approve anything.
# ---------------------------------------------------------------------------

async def review(request: Request) -> Any:
    rt = request.query_params.get("rt", "")
    try:
        auth.unsign(rt, "access-request")
    except auth.AuthError as exc:
        return HTMLResponse(auth.page(html.escape(exc.description)), status_code=400)
    return auth.start_approver_sign_in(rt)


async def approval_page(rt: str, email: str, role: str) -> HTMLResponse:
    if role != auth.ROLE_ADMIN:
        return HTMLResponse(
            auth.page("Only an administrator can decide access requests."), status_code=403)
    try:
        req = auth.unsign(rt, "access-request")
    except auth.AuthError as exc:
        return HTMLResponse(auth.page(html.escape(exc.description)), status_code=400)
    approver = auth.sign("approver", auth.APPROVER_TTL, sub=email, rt_jti=req["jti"])
    e = html.escape
    targets = "the whole organisation" if ORG in req["targets"] else ", ".join(req["targets"])
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;color:#6b7280'>{k}</td><td>{e(str(v))}</td></tr>"
        for k, v in (("Person", req["sub"]), ("Task", req["task"]),
                     ("Permissions", ", ".join(req["perms"])), ("Accounts", targets),
                     ("Reason", req["reason"]))
    )
    button = ("padding:10px 18px;border:0;border-radius:6px;color:#fff;font-size:14px;"
              "cursor:pointer;margin-right:8px")
    form = (
        f"<table style='margin:0 0 18px;font-size:14px'>{rows}</table>"
        "<form method='post' action='/access/decide'>"
        f"<input type='hidden' name='rt' value='{e(rt)}'>"
        f"<input type='hidden' name='approver' value='{e(approver)}'>"
        f"<button name='decision' value='approve' style='{button}background:#1b2a4e'>"
        "Approve for 8 hours</button>"
        f"<button name='decision' value='deny' style='{button}background:#c8102e'>Deny</button>"
        "</form><p style='color:#6b7280;font-size:12px'>Read-only. Signed in as "
        f"{e(email)}.</p>"
    )
    return HTMLResponse(auth.page(form))


async def decide(request: Request) -> HTMLResponse:
    form = await request.form()
    try:
        req = auth.unsign(str(form.get("rt", "")), "access-request")
        approver = auth.unsign(str(form.get("approver", "")), "approver")
    except auth.AuthError as exc:
        return HTMLResponse(auth.page(html.escape(exc.description)), status_code=400)
    if approver.get("rt_jti") != req["jti"] or auth.role_for(approver["sub"]) != auth.ROLE_ADMIN:
        return HTMLResponse(auth.page("This approval does not match the request."),
                            status_code=403)

    import workspace_write
    person = req["sub"]
    if form.get("decision") != "approve":
        await workspace_write.send_system_mail(
            person, "Access request denied",
            f"Your request for {', '.join(req['perms'])} (task: {req['task']}) was denied "
            f"by {approver['sub']}.\n")
        print(json.dumps({"audit": "access_denied", "person": person,
                          "by": approver["sub"], "perms": req["perms"]}), flush=True)
        return HTMLResponse(auth.page(f"Denied. {html.escape(person)} was told by email."))

    grant = mint_grant(person, req["perms"], req["targets"], req["task"],
                       GRANT_TTL_DEFAULT, approver["sub"])
    await workspace_write.send_system_mail(
        person, "Access request approved",
        f"{approver['sub']} approved your request.\n\n"
        f"Task:        {req['task']}\n"
        f"Permissions: {', '.join(req['perms'])}\n"
        f"Valid:       8 hours, read-only\n\n"
        "Give this grant to Claude. Say: use this grant for Workspace Cloud MCP.\n\n"
        f"{grant}\n")
    print(json.dumps({"audit": "access_approved", "person": person, "by": approver["sub"],
                      "perms": req["perms"], "targets": req["targets"]}), flush=True)
    return HTMLResponse(auth.page(
        f"Approved. The grant was emailed to {html.escape(person)}. It expires in 8 hours."))
