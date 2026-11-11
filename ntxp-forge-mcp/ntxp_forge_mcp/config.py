"""Settings for the NTXP Forge MCP.

The domain and the admin account are constants in this file on purpose. No
environment variable, config file, or tool call can widen them.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Hard coded. Only a Google Workspace account in this domain can sign in.
ALLOWED_DOMAIN = "ntxpllc.com"
# Hard coded. The only account with read, write and delete rights.
ADMIN_EMAIL = "trevor@ntxpllc.com"

ENV_PREFIX = "NTXP_FORGE_MCP_"


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(ENV_PREFIX + name) or default).strip()


@dataclass
class Settings:
    data_dir: Path
    public_url: str = "http://localhost:8765"
    host: str = "127.0.0.1"
    port: int = 8765
    # Forge source
    forge_repo: str = "NTXP-TX/ntxp-forge"
    forge_ref: str = "main"
    forge_local: str = ""          # use an existing checkout and never fetch (tests, dev)
    sync_ttl: int = 300            # seconds a checkout stays fresh before the next fetch
    # Credentials. All four come from NTXP ID at first use; see ntxp_id.py.
    google_client_id: str = ""
    google_client_secret: str = ""
    signing_key: str = ""
    github_token: str = ""
    # Copy guard: distinct files one non-admin user may read inside the window.
    copy_window: int = 900
    copy_max_per_package: int = 12
    copy_max_total: int = 40
    max_file_bytes: int = 512 * 1024
    max_export_bytes: int = 5 * 1024 * 1024
    # stdio only: the identity for a local process that has no HTTP sign-in.
    dev_user: str = ""
    # Hosts an OAuth client may use as its redirect. Blocks a rogue client that
    # registers its own redirect and then sends an NTXP user through sign-in.
    redirect_hosts: tuple[str, ...] = ("claude.ai", "claude.com", "localhost", "127.0.0.1")

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(_env("DATA_DIR", "~/.ntxp/forge-mcp")).expanduser()
        return cls(
            data_dir=data_dir,
            public_url=_env("PUBLIC_URL", "http://localhost:8765").rstrip("/"),
            host=_env("HOST", "127.0.0.1"),
            port=int(_env("PORT", "8765")),
            forge_repo=_env("REPO", "NTXP-TX/ntxp-forge"),
            forge_ref=_env("REF", "main"),
            forge_local=_env("LOCAL_PATH"),
            sync_ttl=int(_env("SYNC_TTL", "300")),
            google_client_id=_env("GOOGLE_CLIENT_ID"),
            google_client_secret=_env("GOOGLE_CLIENT_SECRET"),
            signing_key=_env("SIGNING_KEY"),
            github_token=_env("GITHUB_TOKEN"),
            copy_window=int(_env("COPY_WINDOW", "900")),
            copy_max_per_package=int(_env("COPY_MAX_PER_PACKAGE", "12")),
            copy_max_total=int(_env("COPY_MAX_TOTAL", "40")),
            dev_user=_env("DEV_USER").lower(),
            redirect_hosts=tuple(
                h.strip().lower() for h in
                _env("REDIRECT_HOSTS", "claude.ai,claude.com,localhost,127.0.0.1").split(",")
                if h.strip()),
        )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "forge-mcp.db"

    @property
    def forge_dir(self) -> Path:
        return Path(self.forge_local).expanduser() if self.forge_local else self.data_dir / "forge"

    @property
    def user_config_dir(self) -> Path:
        return self.data_dir / "user-config"

    @property
    def resource_url(self) -> str:
        return self.public_url + "/mcp"

    @property
    def google_redirect_uri(self) -> str:
        return self.public_url + "/oauth/google/callback"
