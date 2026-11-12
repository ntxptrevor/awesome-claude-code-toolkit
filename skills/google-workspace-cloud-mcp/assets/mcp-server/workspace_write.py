#!/usr/bin/env python3
"""
workspace_write.py: the admin write functions.

Only the admin role reaches this file. policy.py refuses every other caller
before dispatch. The read functions stay in workspace.py and keep read-only
scopes, so a reader's request never mints a token that can change anything.

Deletes are soft where Google offers a soft delete: Gmail and Drive move items
to Trash (30 days), and a deleted user can be restored for 20 days.
"""

from __future__ import annotations

import base64
import secrets
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from workspace import (
    W_CAL, W_DIR_GROUP, W_DIR_USER, W_DRIVE, W_GMAIL, W_GMAIL_SEND,
    WorkspaceError, _admin, _run, _svc, is_internal,
)


def _mime(sender: str, to: List[str], subject: str, body: str,
          cc: Optional[List[str]] = None) -> Dict[str, str]:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, ", ".join(to), subject
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.set_content(body)
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}


async def send_system_mail(to: str, subject: str, body: str) -> None:
    """Mail from the server itself: access requests and decisions."""
    sender = _admin()

    def call():
        svc = _svc("gmail", "v1", [W_GMAIL_SEND], sender)
        svc.users().messages().send(
            userId="me", body=_mime(sender, [to], subject, body)).execute()
    await _run(call)


# -- Gmail ------------------------------------------------------------------

async def gmail_send(user_email: str, to: List[str], subject: str, body: str,
                     cc: Optional[List[str]] = None) -> Dict:
    def call():
        svc = _svc("gmail", "v1", [W_GMAIL], user_email)
        sent = svc.users().messages().send(
            userId="me", body=_mime(user_email, to, subject, body, cc)).execute()
        return {"sent": True, "id": sent["id"], "thread_id": sent.get("threadId"),
                "mailbox": user_email}
    return await _run(call)


async def gmail_create_draft(user_email: str, to: List[str], subject: str, body: str,
                             cc: Optional[List[str]] = None) -> Dict:
    def call():
        svc = _svc("gmail", "v1", [W_GMAIL], user_email)
        d = svc.users().drafts().create(
            userId="me", body={"message": _mime(user_email, to, subject, body, cc)}).execute()
        return {"draft_id": d["id"], "mailbox": user_email}
    return await _run(call)


async def gmail_modify_labels(user_email: str, message_id: str,
                              add: Optional[List[str]] = None,
                              remove: Optional[List[str]] = None) -> Dict:
    def call():
        svc = _svc("gmail", "v1", [W_GMAIL], user_email)
        m = svc.users().messages().modify(
            userId="me", id=message_id,
            body={"addLabelIds": add or [], "removeLabelIds": remove or []}).execute()
        return {"id": m["id"], "labels": m.get("labelIds", [])}
    return await _run(call)


async def gmail_trash(user_email: str, message_id: str, restore: bool = False) -> Dict:
    def call():
        msgs = _svc("gmail", "v1", [W_GMAIL], user_email).users().messages()
        m = (msgs.untrash if restore else msgs.trash)(userId="me", id=message_id).execute()
        return {"id": m["id"], "in_trash": not restore, "mailbox": user_email}
    return await _run(call)


# -- Calendar ---------------------------------------------------------------

def _when(value: str, tz: Optional[str]) -> Dict[str, str]:
    """'2026-11-20' is an all-day date. Anything longer is a date-time."""
    if len(value) == 10:
        return {"date": value}
    out = {"dateTime": value}
    if tz:
        out["timeZone"] = tz
    return out


async def calendar_create_event(user_email: str, summary: str, start: str, end: str,
                                attendees: Optional[List[str]] = None,
                                description: Optional[str] = None,
                                location: Optional[str] = None,
                                time_zone: Optional[str] = None,
                                notify: bool = False) -> Dict:
    def call():
        body: Dict[str, Any] = {
            "summary": summary, "start": _when(start, time_zone), "end": _when(end, time_zone)}
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        ev = _svc("calendar", "v3", [W_CAL], user_email).events().insert(
            calendarId="primary", body=body,
            sendUpdates="all" if notify else "none").execute()
        return {"event_id": ev["id"], "link": ev.get("htmlLink"), "calendar": user_email}
    return await _run(call)


async def calendar_update_event(user_email: str, event_id: str, changes: Dict[str, Any],
                                time_zone: Optional[str] = None,
                                notify: bool = False) -> Dict:
    def call():
        body: Dict[str, Any] = {}
        for k in ("summary", "description", "location"):
            if k in changes:
                body[k] = changes[k]
        for k in ("start", "end"):
            if k in changes:
                body[k] = _when(changes[k], time_zone)
        if "attendees" in changes:
            body["attendees"] = [{"email": a} for a in changes["attendees"]]
        if not body:
            raise WorkspaceError(
                "No supported change. Use summary, description, location, start, "
                "end or attendees.")
        ev = _svc("calendar", "v3", [W_CAL], user_email).events().patch(
            calendarId="primary", eventId=event_id, body=body,
            sendUpdates="all" if notify else "none").execute()
        return {"event_id": ev["id"], "updated": sorted(body), "calendar": user_email}
    return await _run(call)


async def calendar_delete_event(user_email: str, event_id: str, notify: bool = False) -> Dict:
    def call():
        _svc("calendar", "v3", [W_CAL], user_email).events().delete(
            calendarId="primary", eventId=event_id,
            sendUpdates="all" if notify else "none").execute()
        return {"event_id": event_id, "deleted": True, "calendar": user_email}
    return await _run(call)


# -- Drive ------------------------------------------------------------------

_ALL_DRIVES = {"supportsAllDrives": True}


async def drive_create_folder(user_email: str, name: str,
                              parent_id: Optional[str] = None) -> Dict:
    def call():
        body: Dict[str, Any] = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            body["parents"] = [parent_id]
        return _svc("drive", "v3", [W_DRIVE], user_email).files().create(
            body=body, fields="id,name,webViewLink", **_ALL_DRIVES).execute()
    return await _run(call)


async def drive_update_file(user_email: str, file_id: str, name: Optional[str] = None,
                            move_to_folder_id: Optional[str] = None) -> Dict:
    def call():
        files = _svc("drive", "v3", [W_DRIVE], user_email).files()
        kwargs: Dict[str, Any] = {}
        if move_to_folder_id:
            current = files.get(fileId=file_id, fields="parents", **_ALL_DRIVES).execute()
            kwargs["addParents"] = move_to_folder_id
            kwargs["removeParents"] = ",".join(current.get("parents", []))
        if not name and not kwargs:
            raise WorkspaceError("Give a new name, a destination folder, or both.")
        return files.update(
            fileId=file_id, body={"name": name} if name else {},
            fields="id,name,parents,webViewLink", **kwargs, **_ALL_DRIVES).execute()
    return await _run(call)


async def drive_trash(user_email: str, file_id: str, restore: bool = False) -> Dict:
    def call():
        return _svc("drive", "v3", [W_DRIVE], user_email).files().update(
            fileId=file_id, body={"trashed": not restore},
            fields="id,name,trashed", **_ALL_DRIVES).execute()
    return await _run(call)


async def drive_share(user_email: str, file_id: str, share_with: str, role: str = "reader",
                      notify: bool = False) -> Dict:
    if role not in ("reader", "commenter", "writer"):
        raise WorkspaceError("role must be reader, commenter or writer.")

    def call():
        p = _svc("drive", "v3", [W_DRIVE], user_email).permissions().create(
            fileId=file_id, body={"type": "user", "role": role, "emailAddress": share_with},
            sendNotificationEmail=notify, fields="id,role", **_ALL_DRIVES).execute()
        return {"file_id": file_id, "permission_id": p["id"], "role": p["role"],
                "shared_with": share_with, "external": not is_internal(share_with)}
    return await _run(call)


async def drive_unshare(user_email: str, file_id: str, permission_id: str) -> Dict:
    def call():
        _svc("drive", "v3", [W_DRIVE], user_email).permissions().delete(
            fileId=file_id, permissionId=permission_id, **_ALL_DRIVES).execute()
        return {"file_id": file_id, "permission_id": permission_id, "removed": True}
    return await _run(call)


# -- Directory --------------------------------------------------------------

def _dir(scope: str):
    return _svc("admin", "directory_v1", [scope], _admin())


async def directory_create_user(email: str, given_name: str, family_name: str,
                                org_unit_path: Optional[str] = None) -> Dict:
    def call():
        body: Dict[str, Any] = {
            "primaryEmail": email,
            "name": {"givenName": given_name, "familyName": family_name},
            # A random value nobody sees. The person sets their own at first
            # sign-in through a reset sent from the Admin console.
            "password": secrets.token_urlsafe(24),
            "changePasswordAtNextLogin": True,
        }
        if org_unit_path:
            body["orgUnitPath"] = org_unit_path
        u = _dir(W_DIR_USER).users().insert(body=body).execute()
        return {"created": u["primaryEmail"], "id": u["id"],
                "next_step": "Send the person a password reset from the Admin console."}
    return await _run(call)


async def directory_update_user(user_email: str, changes: Dict[str, Any]) -> Dict:
    def call():
        body: Dict[str, Any] = {}
        if "suspended" in changes:
            body["suspended"] = bool(changes["suspended"])
        if "org_unit_path" in changes:
            body["orgUnitPath"] = changes["org_unit_path"]
        name = {new: changes[old] for old, new in
                (("given_name", "givenName"), ("family_name", "familyName"))
                if old in changes}
        if name:
            body["name"] = name
        if "title" in changes:
            body["organizations"] = [{"title": changes["title"], "primary": True}]
        if not body:
            raise WorkspaceError(
                "No supported change. Use suspended, org_unit_path, given_name, "
                "family_name or title.")
        u = _dir(W_DIR_USER).users().patch(userKey=user_email, body=body).execute()
        return {"user": u["primaryEmail"], "updated": sorted(body),
                "suspended": u.get("suspended", False)}
    return await _run(call)


async def directory_delete_user(user_email: str) -> Dict:
    def call():
        _dir(W_DIR_USER).users().delete(userKey=user_email).execute()
        return {"deleted": user_email,
                "note": "Restore is possible for 20 days in the Admin console."}
    return await _run(call)


async def directory_create_group(email: str, name: str,
                                 description: Optional[str] = None) -> Dict:
    def call():
        g = _dir(W_DIR_GROUP).groups().insert(
            body={"email": email, "name": name, "description": description or ""}).execute()
        return {"created": g["email"], "id": g["id"]}
    return await _run(call)


async def directory_delete_group(group_email: str) -> Dict:
    def call():
        _dir(W_DIR_GROUP).groups().delete(groupKey=group_email).execute()
        return {"deleted": group_email}
    return await _run(call)


async def directory_group_member(group_email: str, member_email: str,
                                 remove: bool = False, role: str = "MEMBER") -> Dict:
    def call():
        members = _dir(W_DIR_GROUP).members()
        if remove:
            members.delete(groupKey=group_email, memberKey=member_email).execute()
            return {"group": group_email, "removed": member_email}
        m = members.insert(groupKey=group_email,
                           body={"email": member_email, "role": role}).execute()
        return {"group": group_email, "added": m["email"], "role": m["role"]}
    return await _run(call)
