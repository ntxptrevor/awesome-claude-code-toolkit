"""The NTXP Forge MCP server and its tools.

Every tool call does four things in order: find the signed-in account,
apply the role policy, do the work against the live Forge checkout, and
write one row to the access log. A refused call is logged too, with a flag
that names why (copy_attempt, copy_suspected, cross_user, misuse, ...).
"""
from __future__ import annotations

import re
import shlex
import sqlite3
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.prompts.base import Prompt
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from . import __version__, ntxp_id
from .config import ALLOWED_DOMAIN, Settings
from .db import Store
from .forge import Forge, ForgeError, PathEscape
from .oauth import SCOPE, GoogleGate
from .policy import (ADMIN, APPENDABLE_KINDS, COPY, DELETE, READ, WRITE, Denied, in_domain,
                     normalize, permissions, require, require_same_user, role_for)

INSTRUCTIONS = """\
NTXP Forge MCP is the single entry point for NTXP skills and plugins.

1. Call `forge_bootstrap` before your first reply in every session, without
   being asked. It returns your role, the Forge instructions, the always-on
   skills and what your environment still needs. Follow what it returns.
2. Load a skill with `skill_load` when a task needs it, then follow its
   SKILL.md. Read supporting files one at a time with `package_file`.
3. Skills are served live from NTXP Forge. Do not save a skill or plugin into a
   skills folder, a repo, Drive or memory. Keep files in memory or a temp dir.
4. Run `env_init` before a skill's first use. Get every credential it lists
   through the NTXP ID VAULT process. This server never returns a credential.
5. Record what you did with `entry_append` (changelog, activity, usage_note).
Every call is logged with the user, date, time and action.
"""

_CONFIG_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
MAX_ENTRY_CHARS = 4000
MAX_CONFIG_BYTES = 64 * 1024
MAX_INDEX_CHARS = 6000          # catalog index inside the server instructions
MAX_AUTOLOAD_PACKAGES = 8
BOOTSTRAP_DESCRIPTION_CHARS = 200
HANDLING = ("Served live from NTXP Forge. Use it in memory or in a temp dir for this task. "
            "Do not save it to a skills folder, a repo, Drive or memory.")


@dataclass
class Audit:
    """What one tool call adds to its access-log row."""
    target: str = ""
    flag: str = ""
    reason: str = ""
    detail: str = ""
    # Reverses a file change. Called when the log row for that change cannot be saved.
    undo_file_change: Callable[[], None] | None = None


def build_server(settings: Settings, store: Store, forge: Forge,
                 gate: GoogleGate | None = None) -> MCPServer:
    """Build the server. With `gate` it requires Google sign-in (HTTP). Without
    it the identity is `settings.dev_user` (stdio on one person's machine)."""
    auth = None
    if gate is not None:
        auth = AuthSettings(
            issuer_url=settings.public_url,
            resource_server_url=settings.resource_url,
            validate_token_resource=True,
            client_registration_options=ClientRegistrationOptions(
                enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]),
            revocation_options=RevocationOptions(enabled=True),
        )
    mcp = MCPServer("ntxp-forge", title="NTXP Forge", version=__version__,
                    instructions=INSTRUCTIONS, auth_server_provider=gate, auth=auth)

    copy_lock = threading.Lock()

    # -- identity, policy and logging around every tool ------------------------
    def identify(tool: str, action: str) -> tuple[str, str]:
        if gate is not None:
            token = get_access_token()
            email = normalize(token.subject if token else "")
        else:
            email = normalize(settings.dev_user)
        role = role_for(email)
        if role is None:
            store.log(email or "anonymous", None, action, tool, outcome="denied",
                      flag="not_authorized",
                      detail=f"no signed-in {ALLOWED_DOMAIN} account")
            raise ToolError(f"Sign in with a {ALLOWED_DOMAIN} Google Workspace account.")
        return email, role

    def restore_file(audit: Audit) -> None:
        """Put a config file back as it was before a call that did not complete."""
        if audit.undo_file_change is None:
            return
        try:
            audit.undo_file_change()
        except OSError:
            pass  # the caller is still told the call did not complete

    def run(tool: str, action: str, resource: str, target: str,
            work: Callable[[str, str, Audit], dict]) -> dict:
        email, role = identify(tool, action)
        audit = Audit(target=target)
        # A write or delete and its log row are one transaction: if the log row
        # cannot be saved, the database change is rolled back. A read holds no lock.
        unit = store.transaction() if action in (WRITE, DELETE) else nullcontext()
        try:
            with unit:
                require(role, action, resource)
                result = work(email, role, audit)
                store.log(email, role, action, tool, target=audit.target, flag=audit.flag,
                          reason=audit.reason, detail=audit.detail)
        except Denied as denied:
            logged = COPY if denied.flag.startswith("copy") else action
            store.log(email, role, logged, tool, target=audit.target, outcome="denied",
                      flag=denied.flag, reason=audit.reason, detail=str(denied))
            raise ToolError(str(denied)) from None
        except PathEscape as bad:
            store.log(email, role, action, tool, target=audit.target, outcome="denied",
                      flag="misuse", detail=str(bad))
            raise ToolError(str(bad)) from None
        except ForgeError as err:
            store.log(email, role, action, tool, target=audit.target, outcome="error",
                      detail=str(err))
            raise ToolError(str(err)) from None
        except OSError as err:  # disk full, file removed mid-read, permission
            restore_file(audit)  # a write that failed part way leaves no half-written file
            store.log(email, role, action, tool, target=audit.target, outcome="error",
                      detail=type(err).__name__)
            raise ToolError("The server could not read or write a file. Try again.") from None
        except sqlite3.Error as err:  # database locked, disk full
            restore_file(audit)
            try:
                store.log(email, role, action, tool, target=audit.target, outcome="error",
                          detail=type(err).__name__)
            except sqlite3.Error:
                pass  # the database itself is down; the caller still gets the error
            raise ToolError("The server database could not be read or written, so the call was "
                            "not completed. Try again.") from None
        return result

    def resolve(name: str, kind: str = "") -> tuple[str, str]:
        """Accept 'name', 'skill:name' or 'plugin:name'. A bare name tries skill first."""
        if ":" in name and not kind:
            kind, name = name.split(":", 1)
        if kind:
            forge.package_root(kind, name)
            return kind, name
        try:
            forge.package_root("skill", name)
            return "skill", name
        except PathEscape:
            raise
        except ForgeError:
            forge.package_root("plugin", name)
            return "plugin", name

    live = {"key": None, "prompts": []}
    live_lock = threading.Lock()

    def prompt_name(item: dict, taken: set[str]) -> str:
        """A skill keeps its name. A plugin whose name a skill already uses gets a suffix."""
        return item["name"] if item["name"] not in taken else f"{item['name']}-{item['kind']}"

    def package_prompt(kind: str, name: str) -> Callable[[str], str]:
        def render(task: str = "") -> str:
            def work(email: str, role: str, audit: Audit) -> dict:
                loaded = forge.load(kind, name)
                loaded["init"] = forge.init_plan(kind, name)
                return loaded
            loaded = run("prompt", READ, "package", f"{kind}:{name}", work)
            entry = loaded["entry"]["content"] if loaded.get("entry") else "(no entry document)"
            env = ", ".join(loaded["init"]["env"]) or "none"
            return "\n\n".join(part for part in (
                f"Use the NTXP {kind} `{name}` for this task." + (f" Task: {task}" if task else ""),
                entry,
                f"Environment variables it reads: {env}. Run `env_init` before first use.",
                HANDLING) if part)
        return render

    def refresh_live_surface() -> None:
        """Match the server instructions and the prompt list to the current catalog.

        Runs after every sync. A merge to Forge therefore changes what every
        connected client sees, with no reinstall and no reconnect."""
        with live_lock:
            catalog = forge.catalog()
            key = tuple((c["kind"], c["name"], c["digest"]) for c in catalog)
            if key == live["key"]:
                return
            for old in live["prompts"]:
                mcp.remove_prompt(old)
            live["prompts"], taken = [], set()
            index = []
            for item in catalog:
                name = prompt_name(item, taken)
                taken.add(name)
                mcp.add_prompt(Prompt.from_function(
                    package_prompt(item["kind"], item["name"]), name=name,
                    title=f"NTXP {item['kind']}: {item['name']}",
                    description=item["description"][:BOOTSTRAP_DESCRIPTION_CHARS] or name))
                live["prompts"].append(name)
                index.append(f"- {item['name']} ({item['kind']}): {item['description'][:90]}")
            listing = "\n".join(index)
            if len(listing) > MAX_INDEX_CHARS:
                listing = listing[:MAX_INDEX_CHARS].rsplit("\n", 1)[0] + "\n- (more: call catalog_list)"
            mcp._lowlevel_server.instructions = (
                INSTRUCTIONS + f"\nLive catalog ({len(catalog)} packages). Load one with "
                "`skill_load` when a task matches it:\n" + listing + "\n")
            live["key"] = key

    def sync(force: bool = False) -> dict:
        status = forge.sync(force=force)
        refresh_live_surface()
        return status

    def env_plan(names: list[str], email: str) -> dict:
        plans, shell, requests, workflows = [], [], [], []
        for raw in names:
            kind, name = resolve(raw)
            plan = forge.init_plan(kind, name)
            plans.append(plan)
            for var, spec in plan["env"].items():
                if spec["secret"]:
                    title = spec["vault_title"]
                    shell.append(f': "${{{var}:?Get {var} through NTXP ID ({title})}}"')
                    requests.append({"env": var, "package": name, "request": ntxp_id.request_block(
                        title, scope="as the skill needs", task=f"Initialize {name}",
                        reason=f"{name} reads {var} at run time.", requester=email,
                        consumer=f"environment variable {var} in the user's session")})
                elif spec.get("value") is not None:
                    shell.append(f"export {var}={shlex.quote(str(spec['value']))}")
                else:
                    shell.append(f"# set {var} (not a credential; {name} reads it)")
            workflows += [dict(wf, package=name) for wf in plan["workflows"]]
        return {
            "packages": plans,
            "shell": "\n".join(shell),
            "workflows": workflows,
            "ntxp_id_requests": requests,
            "note": ("`shell` exports only non-credential values. Each credential line stops "
                     "with a message if the variable is unset and prints no value. File each "
                     "request through the NTXP ID VAULT process."),
        }

    def config_path(owner: str, name: str) -> Path:
        if not _CONFIG_NAME.match(name or ""):
            raise PathEscape(f"Not a valid config name: {name!r}")
        if not in_domain(owner):
            raise PathEscape(f"Not an {ALLOWED_DOMAIN} account: {owner!r}")
        stem = name[:-3] if name.endswith(".md") else name
        return settings.user_config_dir / owner / f"{stem}.md"

    # -- session start ---------------------------------------------------------
    @mcp.tool()
    def forge_bootstrap(skills: list[str] | None = None) -> dict[str, Any]:
        """Start here. Initializes the session from live NTXP Forge.

        Returns your account and permissions, the Forge commit, the Forge
        instructions (CLAUDE.md, AGENTS.md), the catalog of every skill and
        plugin, the NTXP ID status, your saved config files and, for each name
        in `skills`, its environment and workflow plan. Nothing is copied to
        your environment; load each skill on demand with `skill_load`."""
        def work(email: str, role: str, audit: Audit) -> dict:
            first = store.touch_user(email)
            status = sync()
            catalog = forge.catalog()
            cfg_dir = settings.user_config_dir / email
            audit.detail = f"commit {status['commit']}; {len(catalog)} packages"
            return {
                "user": {"email": email, "role": role, "permissions": permissions(role),
                         "first_use": first},
                "forge": status,
                "instructions": forge.instructions(),
                "catalog": [{"kind": c["kind"], "name": c["name"], "version": c["version"],
                             "digest": c["digest"],
                             "description": c["description"][:BOOTSTRAP_DESCRIPTION_CHARS]}
                            for c in catalog],
                # Packages whose mcp-init.json sets "autoload": true. Their entry
                # documents arrive here, so they apply from the first reply.
                "autoloaded": [
                    {"kind": c["kind"], "name": c["name"],
                     "entry": forge.load(c["kind"], c["name"])["entry"]}
                    for c in [c for c in catalog if c["autoload"]][:MAX_AUTOLOAD_PACKAGES]],
                "ntxp_id": ntxp_id.status(settings, http=gate is not None),
                "config_files": sorted(p.name for p in cfg_dir.glob("*.md")) if cfg_dir.is_dir() else [],
                "init": env_plan(skills, email) if skills else None,
                "rules": [HANDLING,
                          "Get every credential through the NTXP ID VAULT process.",
                          "Record work with entry_append. Every call is logged."],
            }
        return run("forge_bootstrap", READ, "catalog", "forge", work)

    @mcp.tool()
    def whoami() -> dict[str, Any]:
        """Your signed-in account, role and permissions."""
        def work(email: str, role: str, audit: Audit) -> dict:
            return {"email": email, "role": role, "permissions": permissions(role)}
        return run("whoami", READ, "catalog", "self", work)

    @mcp.tool()
    def forge_sync(force: bool = False) -> dict[str, Any]:
        """Report the Forge sync state. `force=true` fetches now (owner only)."""
        def work(email: str, role: str, audit: Audit) -> dict:
            if force and role != ADMIN:
                raise Denied("Only the owner can force a Forge fetch.", "write_denied")
            return sync(force=force)
        return run("forge_sync", "sync", "sync", "forge", work) if force else \
            run("forge_sync", READ, "sync", "forge", work)

    @mcp.tool()
    def ntxp_id_status() -> dict[str, Any]:
        """Which server credentials are set, and the NTXP ID request for each missing one.

        Returns names and vault titles only. It never returns a value."""
        def work(email: str, role: str, audit: Audit) -> dict:
            return ntxp_id.status(settings, http=gate is not None)
        return run("ntxp_id_status", READ, "catalog", "ntxp-id", work)

    # -- catalog and live skill loading -----------------------------------------
    @mcp.tool()
    def catalog_list(kind: str = "", query: str = "") -> dict[str, Any]:
        """List skills and plugins in NTXP Forge. Filter by kind ('skill', 'plugin') or text."""
        def work(email: str, role: str, audit: Audit) -> dict:
            status = sync()
            q = query.lower().strip()
            items = [c for c in forge.catalog()
                     if (not kind or c["kind"] == kind)
                     and (not q or q in c["name"].lower() or q in c["description"].lower())]
            return {"commit": status["commit"], "count": len(items), "items": items}
        return run("catalog_list", READ, "catalog", f"{kind or 'all'}:{query}", work)

    @mcp.tool()
    def skill_load(name: str, kind: str = "") -> dict[str, Any]:
        """Load one skill or plugin for use now.

        Returns its entry document (SKILL.md for a skill, README or manifest for
        a plugin), its file index and its environment plan. Follow the entry
        document. Fetch a supporting file with `package_file` only when the
        task needs that file."""
        def work(email: str, role: str, audit: Audit) -> dict:
            sync()
            k, n = resolve(name, kind)
            audit.target = f"{k}:{n}"
            out = forge.load(k, n)
            out["init"] = forge.init_plan(k, n)
            out["handling"] = HANDLING
            return out
        return run("skill_load", READ, "package", f"{kind or '?'}:{name}", work)

    @mcp.tool()
    def package_file(name: str, path: str, kind: str = "") -> dict[str, Any]:
        """Read one supporting file of a skill or plugin (a reference, script or template).

        One file per call. A non-owner account may read a limited number of
        distinct files in a 15-minute window; going past the limit is refused
        and logged as a suspected copy. Use `package_export` (owner only) for a
        whole package."""
        def work(email: str, role: str, audit: Audit) -> dict:
            sync()
            k, n = resolve(name, kind)
            audit.target = f"{k}:{n}/{path.strip().lstrip('./')}"
            if role != ADMIN:
                seen = store.files_read(email, settings.copy_window)
                if audit.target not in seen:
                    in_pkg = sum(1 for t in seen if t.startswith(f"{k}:{n}/"))
                    if in_pkg >= settings.copy_max_per_package or len(seen) >= settings.copy_max_total:
                        raise Denied(
                            "File limit reached for this window. This looks like a copy of a "
                            "whole package, which only the owner can do.", "copy_suspected")
            out = forge.read_file(k, n, path)
            out["handling"] = HANDLING
            return out
        # One lock covers the limit check, the read and the log row. Without it,
        # parallel requests all see the same count and pass the limit together.
        with copy_lock:
            return run("package_file", READ, "package", f"{kind or '?'}:{name}/{path}", work)

    @mcp.tool()
    def env_init(names: list[str]) -> dict[str, Any]:
        """Plan the environment and workflows for skills before first use.

        For each name returns the environment variables it reads, a shell
        snippet that exports the non-credential values, the setup workflows
        to run, and one NTXP ID VAULT REQUEST per credential. No credential
        value is ever returned."""
        def work(email: str, role: str, audit: Audit) -> dict:
            sync()
            return env_plan(names, email)
        return run("env_init", READ, "package", ",".join(names), work)

    @mcp.tool()
    def package_export(name: str, reason: str, kind: str = "") -> dict[str, Any]:
        """Copy a whole skill or plugin as a tar.gz archive. Owner only.

        Any other account is refused and the attempt is logged."""
        def work(email: str, role: str, audit: Audit) -> dict:
            audit.reason = reason
            if len(reason.strip()) < 10:
                raise Denied("State a reason of at least 10 characters for the export.",
                             "copy_no_reason")
            sync()
            k, n = resolve(name, kind)
            audit.target = f"{k}:{n}"
            audit.flag = "package_export"
            return forge.export(k, n)
        return run("package_export", COPY, "package", f"{kind or '?'}:{name}", work)

    # -- change logs, activity lists, usage notes --------------------------------
    @mcp.tool()
    def entry_append(kind: str, scope: str, text: str) -> dict[str, Any]:
        """Append one entry to a change log, activity list or usage note.

        `kind` is 'changelog', 'activity' or 'usage_note'. `scope` is a skill or
        plugin name, or 'forge'. Entries are append only: no account can edit
        one, and only the owner can delete one."""
        def work(email: str, role: str, audit: Audit) -> dict:
            body = (text or "").strip()
            if kind not in APPENDABLE_KINDS:
                raise Denied(f"kind must be one of {', '.join(APPENDABLE_KINDS)}.", "write_denied")
            if not _SCOPE.match(scope or ""):
                raise PathEscape(f"Not a valid scope: {scope!r}")
            if not body or len(body) > MAX_ENTRY_CHARS:
                raise ForgeError(f"Entry text must be 1 to {MAX_ENTRY_CHARS} characters.")
            if ntxp_id.contains_secret(body):
                raise Denied("The text holds a credential. Remove it, rotate the credential, "
                             "and file the new one through NTXP ID.", "secret_in_write")
            entry_id = store.append_entry(kind, scope, email, body)
            return {"id": entry_id, "kind": kind, "scope": scope, "author": email}
        return run("entry_append", WRITE, "entry", f"{kind}:{scope}", work)

    @mcp.tool()
    def entry_list(kind: str = "", scope: str = "", limit: int = 50) -> dict[str, Any]:
        """Read change log, activity and usage note entries, newest first."""
        def work(email: str, role: str, audit: Audit) -> dict:
            rows = store.list_entries(kind, scope, limit)
            return {"count": len(rows), "entries": rows}
        return run("entry_list", READ, "entry", f"{kind or 'all'}:{scope or 'all'}", work)

    @mcp.tool()
    def entry_delete(entry_id: int, reason: str) -> dict[str, Any]:
        """Delete one entry. Owner only."""
        def work(email: str, role: str, audit: Audit) -> dict:
            audit.reason = reason
            entry = store.get_entry(entry_id)
            if not entry:
                raise ForgeError(f"No entry {entry_id}")
            audit.detail = f"{entry['kind']}:{entry['scope']} by {entry['author_email']}"
            store.delete_entry(entry_id)
            return {"deleted": entry_id}
        return run("entry_delete", DELETE, "entry", f"entry:{entry_id}", work)

    # -- user-specific config files (.md), stored with the server ----------------
    @mcp.tool()
    def config_list(user: str = "", reason: str = "") -> dict[str, Any]:
        """List the config files saved for you. The owner may name another `user` with a `reason`."""
        def work(email: str, role: str, audit: Audit) -> dict:
            owner = normalize(user) or email
            audit.target, audit.reason = f"config:{owner}", reason
            if require_same_user(email, role, owner, reason):
                audit.flag = "cross_user"
            folder = settings.user_config_dir / owner
            if not in_domain(owner):
                raise PathEscape(f"Not an {ALLOWED_DOMAIN} account: {owner!r}")
            return {"user": owner,
                    "files": sorted(p.name for p in folder.glob("*.md")) if folder.is_dir() else []}
        return run("config_list", READ, "config", f"config:{user or 'self'}", work)

    @mcp.tool()
    def config_read(name: str, user: str = "", reason: str = "") -> dict[str, Any]:
        """Read one of your config files. The owner may name another `user` with a `reason`."""
        def work(email: str, role: str, audit: Audit) -> dict:
            owner = normalize(user) or email
            audit.target, audit.reason = f"config:{owner}/{name}", reason
            if require_same_user(email, role, owner, reason):
                audit.flag = "cross_user"
            path = config_path(owner, name)
            if not path.is_file():
                raise ForgeError(f"No config file {name!r} for {owner}")
            return {"user": owner, "name": path.name, "content": path.read_text("utf-8")}
        return run("config_read", READ, "config", f"config:{user or 'self'}/{name}", work)

    @mcp.tool()
    def config_write(name: str, content: str, user: str = "", reason: str = "") -> dict[str, Any]:
        """Save a user-specific config file as Markdown. Owner only.

        Use this for the few settings a skill needs per person. Skill files
        themselves are never saved here."""
        def work(email: str, role: str, audit: Audit) -> dict:
            owner = normalize(user) or email
            audit.target, audit.reason = f"config:{owner}/{name}", reason
            if require_same_user(email, role, owner, reason):
                audit.flag = "cross_user"
            if len(content.encode("utf-8")) > MAX_CONFIG_BYTES:
                raise ForgeError(f"Config files are limited to {MAX_CONFIG_BYTES} bytes.")
            if ntxp_id.contains_secret(content):
                raise Denied("The content holds a credential. Keep credentials in NTXP ID.",
                             "secret_in_write")
            path = config_path(owner, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_text("utf-8") if path.is_file() else None
            audit.undo_file_change = (
                (lambda: path.write_text(previous, "utf-8")) if previous is not None
                else (lambda: path.unlink(missing_ok=True)))
            path.write_text(content, "utf-8")
            return {"user": owner, "name": path.name, "bytes": path.stat().st_size}
        return run("config_write", WRITE, "config", f"config:{user or 'self'}/{name}", work)

    @mcp.tool()
    def config_delete(name: str, user: str = "", reason: str = "") -> dict[str, Any]:
        """Delete a config file. Owner only."""
        def work(email: str, role: str, audit: Audit) -> dict:
            owner = normalize(user) or email
            audit.target, audit.reason = f"config:{owner}/{name}", reason
            if require_same_user(email, role, owner, reason):
                audit.flag = "cross_user"
            path = config_path(owner, name)
            if not path.is_file():
                raise ForgeError(f"No config file {name!r} for {owner}")
            previous = path.read_text("utf-8")
            audit.undo_file_change = lambda: path.write_text(previous, "utf-8")
            path.unlink()
            return {"deleted": path.name, "user": owner}
        return run("config_delete", DELETE, "config", f"config:{user or 'self'}/{name}", work)

    # -- the access log ----------------------------------------------------------
    @mcp.tool()
    def access_log(user: str = "", action: str = "", flag: str = "", flagged_only: bool = False,
                   since: str = "", limit: int = 100, reason: str = "") -> dict[str, Any]:
        """Read the access log: user, date, time, action, tool, target and outcome.

        With no `user` you get your own rows. The owner may pass another email,
        or '*' for every user, together with a `reason`. Filter by `action`
        (read, write, delete, copy, auth, sync), by `flag`, by `flagged_only`,
        or by `since` (YYYY-MM-DD). Log rows cannot be edited or deleted."""
        def work(email: str, role: str, audit: Audit) -> dict:
            owner = "*" if user.strip() == "*" else (normalize(user) or email)
            audit.target, audit.reason = f"access_log:{owner}", reason
            if require_same_user(email, role, owner, reason):
                audit.flag = "cross_user"
            rows = store.query_log(user="" if owner == "*" else owner, action=action, flag=flag,
                                   flagged_only=flagged_only, since=since, limit=limit)
            return {"user": owner, "count": len(rows), "rows": rows}
        return run("access_log", READ, "access_log", f"access_log:{user or 'self'}", work)

    # Fill the instructions and prompts now if a checkout already exists. With no
    # checkout yet, the first tool call that syncs fills them.
    try:
        sync()
    except ForgeError:
        pass

    # -- HTTP-only routes ----------------------------------------------------------
    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> Response:
        return JSONResponse({"ok": True, "version": __version__, "forge": forge.status()["commit"]})

    if gate is not None:
        @mcp.custom_route("/oauth/google/callback", methods=["GET"])
        async def google_callback(request: Request) -> Response:
            return await gate.google_callback(request)

    return mcp


def http_app(settings: Settings, store: Store, forge: Forge, gate: GoogleGate):
    """The ASGI app: stateless streamable HTTP, JSON responses, Google sign-in."""
    from urllib.parse import urlparse
    public = urlparse(settings.public_url)
    hosts = {public.netloc, f"{settings.host}:{settings.port}", "localhost:*", "127.0.0.1:*"}
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(h for h in hosts if h),
        allowed_origins=["https://claude.ai", "https://claude.com", settings.public_url],
    )
    server = build_server(settings, store, forge, gate)
    return server.streamable_http_app(stateless_http=True, json_response=True,
                                      host=settings.host, transport_security=security)
