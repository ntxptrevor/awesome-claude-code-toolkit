"""Roles and permissions.

Two roles exist. `admin` is one hard-coded account and may read, write and
delete. Every other account in the domain is `user`: read only, plus append
to the three append-only lists (change logs, activity lists, usage notes).
A user can never delete, never copy a whole package, and never read another
user's records.
"""
from __future__ import annotations

from .config import ADMIN_EMAIL, ALLOWED_DOMAIN

ADMIN = "admin"
USER = "user"

READ, WRITE, DELETE, COPY = "read", "write", "delete", "copy"

# The only things a `user` may write to. Append only.
APPENDABLE_KINDS = ("changelog", "activity", "usage_note")

MIN_REASON_CHARS = 10


class Denied(Exception):
    """A request the policy refuses. `flag` names the kind for the access log."""

    def __init__(self, message: str, flag: str = "denied"):
        super().__init__(message)
        self.flag = flag


def normalize(email: str | None) -> str:
    return (email or "").strip().lower()


def in_domain(email: str | None) -> bool:
    e = normalize(email)
    local, sep, domain = e.rpartition("@")
    return bool(sep and local and domain == ALLOWED_DOMAIN)


def role_for(email: str | None) -> str | None:
    """Role for an email, or None if the account may not use the server."""
    e = normalize(email)
    if not in_domain(e):
        return None
    return ADMIN if e == ADMIN_EMAIL else USER


def permissions(role: str) -> dict:
    is_admin = role == ADMIN
    return {"read": True, "write": is_admin, "delete": is_admin,
            "copy_packages": is_admin, "append": list(APPENDABLE_KINDS)}


def require(role: str, action: str, resource: str) -> None:
    """Raise Denied unless `role` may do `action` on `resource`.

    `resource` is one of: catalog, package, entry, config, access_log, sync.
    """
    if role == ADMIN:
        return
    if action == READ:
        return
    if action == WRITE and resource == "entry":
        return  # append to a change log, activity list or usage note
    if action == COPY:
        raise Denied("Only the owner can copy a whole skill or plugin.", "copy_attempt")
    raise Denied(f"Your account is read only. It cannot {action} {resource} records.",
                 "write_denied")


def require_same_user(actor: str, role: str, owner: str, reason: str = "") -> bool:
    """Gate access to another user's records. Returns True for cross-user access.

    A user can never read another user's records. The admin can, but only
    with a stated reason, which the caller writes to the access log.
    """
    actor, owner = normalize(actor), normalize(owner)
    if not owner or owner == actor:
        return False
    if role != ADMIN:
        raise Denied("You can only read your own records.", "cross_user")
    if len((reason or "").strip()) < MIN_REASON_CHARS:
        raise Denied(
            "Reading another user's records needs a reason of at least "
            f"{MIN_REASON_CHARS} characters.", "cross_user_no_reason")
    return True
