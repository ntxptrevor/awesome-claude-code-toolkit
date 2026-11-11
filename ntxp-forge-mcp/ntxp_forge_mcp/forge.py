"""NTXP Forge as the back end.

The server keeps one shallow checkout of the private Forge repo and refreshes
it when the checkout is older than `sync_ttl`. Skills and plugins are read
from that checkout on every call, so a merge to Forge `main` reaches every
user at the next refresh and nothing is copied into a user's environment.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import threading
import time
from pathlib import Path

import yaml

from . import ntxp_id
from .config import Settings

KINDS = {"skill": "skills", "plugin": "plugins"}
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".in_use", ".venv"}
_ENV_REF = re.compile(r"\$\{([A-Z][A-Z0-9_]{2,})(?::-[^}]*)?\}")
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
INIT_FILE = "mcp-init.json"
MAX_INSTRUCTION_CHARS = 20_000


class ForgeError(Exception):
    """A Forge request that cannot be served (unknown package, no checkout)."""


class PathEscape(ForgeError):
    """A file path that points outside its package. Logged as misuse."""


class Forge:
    def __init__(self, settings: Settings):
        self.s = settings
        self.root = settings.forge_dir
        self._lock = threading.RLock()
        self._sha = ""
        self._synced_at = 0.0
        self._checked_at = 0.0
        self._error = ""
        self._catalog: tuple[str, float, list[dict]] | None = None

    # -- sync ----------------------------------------------------------------
    def _git(self, *args: str, auth: bool = False) -> str:
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        if auth and self.s.github_token:
            # The token goes to git through the environment. It is never written
            # to .git/config and never appears in the process arguments.
            basic = base64.b64encode(f"x-access-token:{self.s.github_token}".encode()).decode()
            env.update(GIT_CONFIG_COUNT="1",
                       GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                       GIT_CONFIG_VALUE_0=f"AUTHORIZATION: basic {basic}")
        proc = subprocess.run(["git", "-C", str(self.root), *args], env=env,
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise ForgeError(f"git {args[0]} failed: {proc.stderr.strip()[-300:]}")
        return proc.stdout.strip()

    def _has_checkout(self) -> bool:
        return (self.root / "skills").is_dir() or (self.root / "plugins").is_dir()

    def sync(self, force: bool = False) -> dict:
        """Refresh the checkout if it is stale. Keeps the last good copy on failure."""
        with self._lock:
            now = time.time()
            if self.s.forge_local:
                if not self._has_checkout():
                    raise ForgeError(f"No Forge checkout at {self.root}")
                if not self._sha or force:
                    try:
                        self._sha = self._git("rev-parse", "HEAD")
                    except (ForgeError, OSError, subprocess.SubprocessError):
                        self._sha = "local"
                    self._synced_at = now
                return self.status()
            due = now - self._checked_at >= self.s.sync_ttl
            if self._has_checkout() and self._sha and not force and not due:
                return self.status()
            self._checked_at = now
            try:
                self.root.mkdir(parents=True, exist_ok=True)
                if not (self.root / ".git").is_dir():
                    self._git("init", "-q")
                    self._git("remote", "add", "origin",
                              f"https://github.com/{self.s.forge_repo}.git")
                self._git("fetch", "-q", "--depth", "1", "origin", self.s.forge_ref, auth=True)
                self._git("checkout", "-q", "-f", "--detach", "FETCH_HEAD")
                self._git("clean", "-q", "-fdx")
                sha = self._git("rev-parse", "HEAD")
                if sha != self._sha:
                    self._catalog = None
                self._sha, self._synced_at, self._error = sha, now, ""
            except (ForgeError, OSError, subprocess.SubprocessError) as exc:
                self._error = str(exc)
                if not self._has_checkout():
                    raise ForgeError(
                        "NTXP Forge is not reachable and no checkout exists. "
                        "Check the Forge read token through NTXP ID.") from exc
                if not self._sha:
                    self._sha = "unknown"
            return self.status()

    def status(self) -> dict:
        return {
            "repo": self.s.forge_local or self.s.forge_repo,
            "ref": self.s.forge_ref,
            "commit": self._sha,
            "synced_at": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._synced_at))
                          if self._synced_at else None),
            "stale": bool(self._error),
            "error": self._error or None,
        }

    # -- packages ------------------------------------------------------------
    def package_root(self, kind: str, name: str) -> Path:
        if kind not in KINDS:
            raise ForgeError("kind must be 'skill' or 'plugin'")
        if not _NAME.match(name or ""):
            raise PathEscape(f"Not a valid {kind} name: {name!r}")
        root = self.root / KINDS[kind] / name
        if not root.is_dir() or root.is_symlink():
            raise ForgeError(f"No {kind} named {name!r} in NTXP Forge")
        return root

    def files(self, kind: str, name: str) -> list[dict]:
        root = self.package_root(kind, name)
        real_root = root.resolve()
        out = []
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
            for fn in sorted(filenames):
                p = Path(dirpath) / fn
                try:
                    if not p.resolve().is_relative_to(real_root) or not p.is_file():
                        continue
                    out.append({"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size})
                except OSError:
                    continue
        return out

    def read_file(self, kind: str, name: str, relpath: str) -> dict:
        root = self.package_root(kind, name)
        rel = (relpath or "").strip()
        if not rel or rel.startswith(("/", "\\")) or "\x00" in rel:
            raise PathEscape(f"Not a valid file path: {relpath!r}")
        target = (root / rel).resolve()
        if not target.is_relative_to(root.resolve()):
            raise PathEscape(f"Path leaves the {kind}: {relpath!r}")
        if set(target.relative_to(root.resolve()).parts) & _SKIP_DIRS:
            raise PathEscape(f"Path is not served: {relpath!r}")
        if target.name == ".env" or not target.is_file():
            raise ForgeError(f"No file {relpath!r} in {kind} {name!r}")
        size = target.stat().st_size
        if size > self.s.max_file_bytes:
            raise ForgeError(f"{relpath} is {size} bytes. The limit is {self.s.max_file_bytes}.")
        data = target.read_bytes()
        try:
            return {"path": rel, "bytes": size, "encoding": "utf-8", "content": data.decode("utf-8")}
        except UnicodeDecodeError:
            return {"path": rel, "bytes": size, "encoding": "base64",
                    "content": base64.b64encode(data).decode()}

    def _digest(self, kind: str, name: str, files: list[dict]) -> str:
        if self._sha and self._sha not in ("local", "unknown"):
            try:
                return self._git("rev-parse", f"HEAD:{KINDS[kind]}/{name}")[:12]
            except (ForgeError, OSError, subprocess.SubprocessError):
                pass
        h = hashlib.sha256()
        for f in files:
            h.update(f"{f['path']}:{f['bytes']}\n".encode())
        return h.hexdigest()[:12]

    @staticmethod
    def _frontmatter(text: str) -> dict:
        m = _FRONTMATTER.match(text)
        if not m:
            return {}
        try:
            data = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            return {}
        return data if isinstance(data, dict) else {}

    def _plugin_manifest(self, root: Path) -> dict:
        for rel in (".claude-plugin/plugin.json", "plugin.json"):
            p = root / rel
            if p.is_file():
                try:
                    data = json.loads(p.read_text("utf-8"))
                    return data if isinstance(data, dict) else {}
                except (OSError, ValueError):
                    return {}
        return {}

    def describe(self, kind: str, name: str) -> dict:
        root = self.package_root(kind, name)
        files = self.files(kind, name)
        meta: dict = {}
        if kind == "skill":
            skill_md = root / "SKILL.md"
            if skill_md.is_file():
                meta = self._frontmatter(skill_md.read_text("utf-8", errors="replace"))
        else:
            meta = self._plugin_manifest(root)
        version = meta.get("version") or (meta.get("metadata") or {}).get("version") or ""
        return {
            "kind": kind,
            "name": name,
            "description": " ".join(str(meta.get("description") or "").split())[:400],
            "version": str(version),
            "files": len(files),
            "bytes": sum(f["bytes"] for f in files),
            "digest": self._digest(kind, name, files),
        }

    def catalog(self) -> list[dict]:
        with self._lock:
            now = time.time()
            if self._catalog and self._catalog[0] == self._sha and (
                    self._sha != "local" or now - self._catalog[1] < 30):
                return self._catalog[2]
            items = []
            for kind, folder in KINDS.items():
                base = self.root / folder
                if not base.is_dir():
                    continue
                for child in sorted(base.iterdir(), key=lambda p: p.name.lower()):
                    if child.is_dir() and not child.is_symlink() and _NAME.match(child.name):
                        if kind == "skill" and not (child / "SKILL.md").is_file():
                            continue
                        items.append(self.describe(kind, child.name))
            self._catalog = (self._sha, now, items)
            return items

    def load(self, kind: str, name: str) -> dict:
        """The entry document of a package plus its file index."""
        root = self.package_root(kind, name)
        info = self.describe(kind, name)
        files = self.files(kind, name)
        paths = {f["path"] for f in files}
        if kind == "skill":
            entry = "SKILL.md"
        else:
            entry = next((p for p in ("README.md", ".claude-plugin/plugin.json", "plugin.json")
                          if p in paths), "")
            info["components"] = {
                "skills": sorted(p.split("/")[1] for p in paths
                                 if p.startswith("skills/") and p.endswith("/SKILL.md")),
                "commands": sorted(p for p in paths if p.startswith("commands/")),
                "agents": sorted(p for p in paths if p.startswith("agents/")),
                "manifest": self._plugin_manifest(root),
            }
        info["entry"] = self.read_file(kind, name, entry) if entry in paths else None
        info["file_index"] = files
        return info

    def instructions(self) -> dict:
        out = {}
        for fn in ("CLAUDE.md", "AGENTS.md"):
            p = self.root / fn
            if p.is_file() and not p.is_symlink():
                out[fn] = p.read_text("utf-8", errors="replace")[:MAX_INSTRUCTION_CHARS]
        return out

    # -- environment and workflow initialization ------------------------------
    def init_plan(self, kind: str, name: str) -> dict:
        """What a user's environment needs before this package runs.

        Sources, in order: the package's optional `mcp-init.json`, every
        `${VAR}` reference in its MCP config, and its frontmatter `requires`.
        A credential variable never carries a value here. It carries the
        NTXP ID vault title to request.
        """
        root = self.package_root(kind, name)
        env: dict[str, dict] = {}
        workflows: list[dict] = []
        requires: dict = {}

        declared: dict = {}
        init_path = root / INIT_FILE
        if init_path.is_file():
            try:
                loaded = json.loads(init_path.read_text("utf-8"))
                declared = loaded if isinstance(loaded, dict) else {}
            except (OSError, ValueError):
                declared = {}
        for var, spec in (declared.get("env") or {}).items():
            spec = spec if isinstance(spec, dict) else {"value": spec}
            env[var] = {
                "required": bool(spec.get("required", True)),
                "secret": bool(spec.get("secret", ntxp_id.is_secret_name(var))),
                "value": spec.get("value"),
                "vault_title": spec.get("vault_title"),
                "source": INIT_FILE,
            }
        for wf in declared.get("workflows") or []:
            if isinstance(wf, dict) and wf.get("run"):
                workflows.append({"name": str(wf.get("name") or "setup"), "run": str(wf["run"])})

        for f in self.files(kind, name):
            if Path(f["path"]).name in (".mcp.json", "mcp.json") and f["bytes"] < 200_000:
                text = (root / f["path"]).read_text("utf-8", errors="replace")
                for var in _ENV_REF.findall(text):
                    env.setdefault(var, {"required": True, "secret": ntxp_id.is_secret_name(var),
                                         "value": None, "vault_title": None, "source": f["path"]})

        if kind == "skill" and (root / "SKILL.md").is_file():
            fm = self._frontmatter((root / "SKILL.md").read_text("utf-8", errors="replace"))
            if isinstance(fm.get("requires"), dict):
                requires = fm["requires"]

        for var, spec in env.items():
            value = spec.get("value")
            if spec["secret"] or (isinstance(value, str) and ntxp_id.contains_secret(value)):
                spec["secret"] = True
                spec["value"] = None
                spec["vault_title"] = spec.get("vault_title") or f"{name} ({var})"
        return {"kind": kind, "name": name, "env": env, "workflows": workflows,
                "requires": requires}

    # -- owner-only export ----------------------------------------------------
    def export(self, kind: str, name: str) -> dict:
        root = self.package_root(kind, name)
        files = self.files(kind, name)
        total = sum(f["bytes"] for f in files)
        if total > self.s.max_export_bytes:
            raise ForgeError(f"{name} is {total} bytes. Export limit is "
                             f"{self.s.max_export_bytes}. Clone NTXP Forge for this package.")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for f in files:
                tar.add(root / f["path"], arcname=f"{name}/{f['path']}", recursive=False)
        return {"kind": kind, "name": name, "files": len(files), "bytes": total,
                "commit": self._sha, "format": "tar.gz", "encoding": "base64",
                "archive": base64.b64encode(buf.getvalue()).decode()}
