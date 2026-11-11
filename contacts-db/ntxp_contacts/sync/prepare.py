"""Clean one raw source record before it is reconciled (shared by the live sync and bulk loads)."""
from __future__ import annotations

import re

_PHONE_ONLY = re.compile(r"[\d\s().+\-]{7,}")
_TEST_ORGS = {"test", "bidforge smoke test"}


def prepare(d: dict) -> dict | None:
    """-> cleaned payload, or None when the record is not a real person/company."""
    d = dict(d)
    co = (d.get("company") or "").strip()
    if co and _PHONE_ONLY.fullmatch(co):
        d["company"] = None                     # a phone number typed into the company field
    if co.lower() in _TEST_ORGS:
        return None
    emails = [e for e in (d.get("emails") or ([d["email"]] if d.get("email") else [])) if e]
    phones = [x for x in (d.get("phones") or ([d["phone"]] if d.get("phone") else [])) if x]
    d["emails"], d["phones"] = emails, phones
    if not (d.get("firstName") or d.get("lastName") or d.get("first_name") or d.get("last_name") or d.get("name")) and emails:
        local = emails[0].split("@")[0]
        toks = [t for t in re.split(r"[._\-+0-9]+", local) if t]
        if not toks:
            return None                          # numeric local part: an SMS/voicemail gateway, not a person
        d["firstName"] = toks[0].title()
        d["lastName"] = " ".join(toks[1:]).title() or None
    return d
