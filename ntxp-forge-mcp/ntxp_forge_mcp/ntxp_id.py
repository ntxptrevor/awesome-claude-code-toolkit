"""The NTXP ID dependency.

Every credential this server or a served skill needs at first use goes
through the NTXP ID VAULT process (the `ntxp-id` plugin in NTXP Forge). This
module never reads the vault and never returns a credential value. It does
three jobs:

1. Names the four credentials the server itself needs, by vault title.
2. Writes the `NTXP ID VAULT REQUEST` block for each missing credential, so
   the agent can file it with the Chief of Staff agent.
3. Refuses any write that contains a credential-shaped string.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .config import ENV_PREFIX, Settings

VAULT_SHEET_TITLE = "NTXP ID VAULT"
PROCESS_SKILL = "ntxp-id"


@dataclass(frozen=True)
class Credential:
    env: str            # environment variable the value is read from
    vault_title: str    # "Tool / Service" title on the Vault tab
    scope: str
    reason: str
    lane: str = "key"


SERVER_CREDENTIALS = (
    Credential(ENV_PREFIX + "GOOGLE_CLIENT_ID", "NTXP Forge MCP Google OAuth client id",
               "sign-in", "Identifies this server to Google sign-in."),
    Credential(ENV_PREFIX + "GOOGLE_CLIENT_SECRET", "NTXP Forge MCP Google OAuth client",
               "sign-in", "Exchanges the Google sign-in code for the user's identity."),
    Credential(ENV_PREFIX + "SIGNING_KEY", "NTXP Forge MCP signing key",
               "token signing", "Signs the access tokens this server issues."),
    Credential(ENV_PREFIX + "GITHUB_TOKEN", "NTXP Forge read token (GitHub)",
               "read-only, contents", "Fetches the private NTXP Forge repo."),
)

_FIELD = {
    ENV_PREFIX + "GOOGLE_CLIENT_ID": "google_client_id",
    ENV_PREFIX + "GOOGLE_CLIENT_SECRET": "google_client_secret",
    ENV_PREFIX + "SIGNING_KEY": "signing_key",
    ENV_PREFIX + "GITHUB_TOKEN": "github_token",
}

# Names that mark an environment variable as a credential.
_SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE)", re.I)

# Shapes of real credentials. A write that matches any of these is refused.
_SECRET_SHAPES = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
)


def is_secret_name(name: str) -> bool:
    return bool(_SECRET_NAME.search(name))


def contains_secret(text: str) -> bool:
    return any(p.search(text or "") for p in _SECRET_SHAPES)


def missing_server_credentials(settings: Settings, *, http: bool = True) -> list[Credential]:
    """Server credentials that are not set. A local checkout needs no GitHub token."""
    out = []
    for cred in SERVER_CREDENTIALS:
        if cred.env.endswith("GITHUB_TOKEN") and settings.forge_local:
            continue
        if not http and not cred.env.endswith("GITHUB_TOKEN"):
            continue  # stdio has no sign-in, so it needs no OAuth or signing values
        if not getattr(settings, _FIELD[cred.env]):
            out.append(cred)
    return out


def request_block(title: str, *, scope: str, task: str, reason: str, requester: str,
                  consumer: str, lane: str = "key", duration: str = "this session") -> str:
    """The exact block the NTXP ID VAULT process expects. It never holds a value."""
    return "\n".join([
        "NTXP ID VAULT REQUEST",
        f"key:        {title}",
        f"lane:       {lane}",
        f"scope:      {scope}",
        f"task:       {task}",
        f"reason:     {reason}",
        f"requester:  {requester}",
        f"consumer:   {consumer}",
        f"duration:   {duration}",
    ])


def server_requests(missing: list[Credential], requester: str = "ntxp-forge-mcp deploy") -> list[dict]:
    return [{
        "env": c.env,
        "vault_title": c.vault_title,
        "request": request_block(
            c.vault_title, scope=c.scope, task="First start of the NTXP Forge MCP server",
            reason=c.reason, requester=requester, lane=c.lane,
            consumer=f"server environment variable {c.env}", duration="one-time"),
    } for c in missing]


def status(settings: Settings, *, http: bool = True) -> dict:
    missing = missing_server_credentials(settings, http=http)
    return {
        "vault": VAULT_SHEET_TITLE,
        "process": f"the `{PROCESS_SKILL}` plugin in NTXP Forge",
        "ready": not missing,
        "missing": [c.env for c in missing],
        "requests": server_requests(missing),
        "rule": ("This server never returns a credential value. File each request with the "
                 "Chief of Staff agent, then set the value where the work runs."),
    }


class NtxpIdRequired(RuntimeError):
    """Raised at first start when a required credential is not set."""

    def __init__(self, missing: list[Credential]):
        self.missing = missing
        blocks = "\n\n".join(r["request"] for r in server_requests(missing))
        super().__init__(
            "NTXP Forge MCP cannot start. These credentials are not set: "
            + ", ".join(c.env for c in missing)
            + ".\nGet each one through the NTXP ID VAULT process:\n\n" + blocks)


def require_first_run(settings: Settings, *, http: bool = True) -> None:
    missing = missing_server_credentials(settings, http=http)
    if missing:
        raise NtxpIdRequired(missing)
