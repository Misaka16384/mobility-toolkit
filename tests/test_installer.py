"""Filesystem-level tests for the multi-agent project installer.

Pure filesystem; no Macaulay2 backend required.
"""
import json
import types

import mobility_toolkit.installer as inst
from mobility_toolkit.installer import (
    run_install,
    run_uninstall,
    run_status,
    run_self_update,
    detect_install_mode,
    _update_command,
    GIT_URL,
    SKILL_NAMES,
    MCP_NAME,
    _BOOTSTRAP_MARKER,
)

_QUIET = lambda *a, **k: None  # noqa: E731

_ALL = ["claude", "codex", "opencode", "antigravity"]
_MCP_FILES = [".mcp.json", "opencode.json", ".codex/config.toml", ".agents/mcp_config.json"]


def test_install_skills_only_by_default(tmp_path):
    """Default install writes skills (+ AGENTS.md) but NO MCP config."""
    assert run_install(targets=_ALL, project_dir=str(tmp_path), log=_QUIET)

    # skills copied into each agent's directory
    assert (tmp_path / ".claude" / "skills" / "translate_to_algebra" / "SKILL.md").exists()
    assert (tmp_path / ".agents" / "skills" / "compute_homology_and_mobility" / "SKILL.md").exists()
    assert (tmp_path / ".opencode" / "skills" / "query_vector_db" / "SKILL.md").exists()
    for name in SKILL_NAMES:
        assert (tmp_path / ".claude" / "skills" / name).is_dir()

    # bootstrap injected so the copied script can import the core
    script = tmp_path / ".claude" / "skills" / "translate_to_algebra" / "scripts" / "translate_to_algebra.py"
    assert _BOOTSTRAP_MARKER in script.read_text(encoding="utf-8")

    # AGENTS.md managed block present
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "mobility-toolkit:start" in agents and "mobility-toolkit:end" in agents

    # MCP is opt-in: none of the MCP config files should exist
    for rel in _MCP_FILES:
        assert not (tmp_path / rel).exists(), f"unexpected MCP file written: {rel}"


def test_install_with_mcp_writes_configs(tmp_path):
    """`--mcp` (with_mcp=True) writes each agent's MCP config in its native shape."""
    assert run_install(targets=_ALL, project_dir=str(tmp_path), with_mcp=True, log=_QUIET)

    mcp = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp["mcpServers"][MCP_NAME]["args"] == ["-m", "mobility_toolkit.mcp_server"]

    oc = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert oc["mcp"][MCP_NAME]["type"] == "local"
    assert oc["mcp"][MCP_NAME]["command"][-2:] == ["-m", "mobility_toolkit.mcp_server"]

    toml_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert f"[mcp_servers.{MCP_NAME}]" in toml_text

    ag = json.loads((tmp_path / ".agents" / "mcp_config.json").read_text(encoding="utf-8"))
    assert MCP_NAME in ag["mcpServers"]


def test_install_is_idempotent(tmp_path):
    proj = str(tmp_path)
    run_install(targets=["codex"], project_dir=proj, with_mcp=True, log=_QUIET)
    run_install(targets=["codex"], project_dir=proj, with_mcp=True, log=_QUIET)

    toml_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert toml_text.count(f"[mcp_servers.{MCP_NAME}]") == 1

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.count("mobility-toolkit:start") == 1


def test_status_reflects_install(tmp_path):
    proj = str(tmp_path)
    before = run_status(project_dir=proj, log=_QUIET)
    assert before["claude"] == {"skills": False, "mcp": False}

    # skills-only install -> skills present, mcp absent
    run_install(targets=["claude"], project_dir=proj, log=_QUIET)
    mid = run_status(project_dir=proj, log=_QUIET)
    assert mid["claude"] == {"skills": True, "mcp": False}

    # add MCP -> both present
    run_install(targets=["claude"], project_dir=proj, with_mcp=True, log=_QUIET)
    after = run_status(project_dir=proj, log=_QUIET)
    assert after["claude"] == {"skills": True, "mcp": True}


def test_uninstall_removes_entries(tmp_path):
    proj = str(tmp_path)
    run_install(targets=["claude", "codex", "opencode"], project_dir=proj, with_mcp=True, log=_QUIET)
    run_uninstall(targets=["claude", "codex", "opencode"], project_dir=proj, log=_QUIET)

    assert not (tmp_path / ".claude" / "skills" / "translate_to_algebra").exists()
    mcp = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert MCP_NAME not in mcp.get("mcpServers", {})
    toml_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert f"[mcp_servers.{MCP_NAME}]" not in toml_text


# --- self-update -----------------------------------------------------------
def test_update_command_shapes():
    """git mode pulls; wheel mode reinstalls our package only, from the git URL."""
    git_cmd = _update_command("git")
    assert git_cmd[0] == "git" and git_cmd[-2:] == ["pull", "--ff-only"]

    wheel_cmd = _update_command("wheel")
    assert wheel_cmd[1:4] == ["-m", "pip", "install"]
    # force-reinstall is required (static version) and --no-deps keeps it to us
    assert "--force-reinstall" in wheel_cmd and "--no-deps" in wheel_cmd
    assert wheel_cmd[-1] == GIT_URL


def test_detect_install_mode_is_stable():
    # Whatever the test environment, the result must be one of the two known modes.
    assert detect_install_mode() in {"git", "wheel"}


def test_self_update_dry_run_changes_nothing(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(inst.subprocess, "run",
                        lambda *a, **k: calls.append(a) or types.SimpleNamespace(returncode=0))
    assert run_self_update(project_dir=str(tmp_path), dry_run=True, log=_QUIET)
    assert calls == []                                   # no package update launched
    assert not (tmp_path / ".claude").exists()           # no project files written


def test_self_update_refreshes_only_installed_agents(tmp_path, monkeypatch):
    proj = str(tmp_path)
    # project starts with a skills-only Claude install
    run_install(targets=["claude"], project_dir=proj, log=_QUIET)

    # fake a successful package update (no real pip/git call)
    monkeypatch.setattr(inst.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(returncode=0))
    assert run_self_update(project_dir=proj, log=_QUIET)

    # claude refreshed; the other agents were NOT introduced
    assert (tmp_path / ".claude" / "skills" / "translate_to_algebra" / "SKILL.md").exists()
    assert not (tmp_path / ".opencode").exists()
    assert not (tmp_path / ".agents").exists()
    # MCP setup preserved (was off) -> still off
    assert not (tmp_path / ".mcp.json").exists()


def test_self_update_aborts_when_package_update_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(inst.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(returncode=1))
    # should report failure and never reach the project refresh
    assert run_self_update(project_dir=str(tmp_path), log=_QUIET) is False
    assert not (tmp_path / ".claude").exists()
