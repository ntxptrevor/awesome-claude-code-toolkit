"""Forge sync: live updates from a git remote, and the last good copy on failure."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from conftest import make_forge
from ntxp_forge_mcp.config import Settings
from ntxp_forge_mcp.forge import Forge, ForgeError


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@ntxpllc.com",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    src = make_forge(tmp_path / "remote")
    git(src, "init", "-q", "-b", "main")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "first")
    return src


class RemoteForge(Forge):
    """Forge that fetches from a local git repo in place of github.com."""

    def __init__(self, settings: Settings, remote: Path):
        super().__init__(settings)
        self.remote = remote

    def _git(self, *args: str, auth: bool = False) -> str:
        if args[:3] == ("remote", "add", "origin"):
            args = ("remote", "add", "origin", str(self.remote))
        return super()._git(*args, auth=auth)


def test_merge_to_forge_reaches_the_server_on_the_next_sync(tmp_path, remote):
    forge = RemoteForge(Settings(data_dir=tmp_path / "data", sync_ttl=0), remote)
    first = forge.sync()
    assert first["commit"] == git(remote, "rev-parse", "HEAD") and not first["stale"]
    assert forge.describe("skill", "demo-skill")["version"] == "1.2.3"

    skill_md = remote / "skills" / "demo-skill" / "SKILL.md"
    skill_md.write_text(skill_md.read_text().replace("1.2.3", "2.0.0"))
    (remote / "skills" / "new-skill").mkdir()
    (remote / "skills" / "new-skill" / "SKILL.md").write_text("---\nname: new-skill\n---\nNew.\n")
    git(remote, "add", "-A")
    git(remote, "commit", "-q", "-m", "second")

    second = forge.sync()
    assert second["commit"] != first["commit"]
    names = {c["name"]: c for c in forge.catalog()}
    assert names["demo-skill"]["version"] == "2.0.0" and "new-skill" in names


def test_fresh_checkout_is_not_fetched_again_inside_the_ttl(tmp_path, remote):
    forge = RemoteForge(Settings(data_dir=tmp_path / "data", sync_ttl=3600), remote)
    first = forge.sync()
    (remote / "x.txt").write_text("x")
    git(remote, "add", "-A")
    git(remote, "commit", "-q", "-m", "second")
    assert forge.sync()["commit"] == first["commit"]
    assert forge.sync(force=True)["commit"] != first["commit"]


def test_failed_fetch_keeps_the_last_good_copy(tmp_path, remote):
    forge = RemoteForge(Settings(data_dir=tmp_path / "data", sync_ttl=0), remote)
    good = forge.sync()
    git(forge.root, "remote", "set-url", "origin", str(tmp_path / "gone"))
    status = forge.sync()
    assert status["stale"] and status["commit"] == good["commit"]
    assert forge.load("skill", "demo-skill")["entry"]["path"] == "SKILL.md"


def test_no_checkout_and_no_remote_is_an_error(tmp_path):
    forge = RemoteForge(Settings(data_dir=tmp_path / "data"), tmp_path / "gone")
    with pytest.raises(ForgeError):
        forge.sync()


def test_token_is_never_written_to_the_checkout(tmp_path, remote):
    marker = "tok-for-this-test-only"
    forge = RemoteForge(Settings(data_dir=tmp_path / "data", github_token=marker), remote)
    forge.sync()
    assert marker not in (forge.root / ".git" / "config").read_text()


@pytest.mark.parametrize("name", ["", ".", "..", "no-such-skill"])
def test_empty_or_unknown_package_name_is_an_error(forge, name):
    forge.sync()
    with pytest.raises(ForgeError):
        forge.load("skill", name)


def test_forge_with_no_packages_has_an_empty_catalog(tmp_path):
    (tmp_path / "f" / "skills").mkdir(parents=True)
    forge = Forge(Settings(data_dir=tmp_path / "d", forge_local=str(tmp_path / "f")))
    forge.sync()
    assert forge.catalog() == []


def test_symlink_out_of_a_package_is_not_served(settings, forge):
    link = Path(settings.forge_local) / "skills" / "demo-skill" / "leak.txt"
    link.symlink_to(Path(settings.forge_local) / "outside.txt")
    forge.sync()
    assert "leak.txt" not in {f["path"] for f in forge.files("skill", "demo-skill")}
    with pytest.raises(ForgeError):
        forge.read_file("skill", "demo-skill", "leak.txt")
