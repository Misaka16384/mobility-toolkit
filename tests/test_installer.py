"""Filesystem-level tests for the multi-agent project installer.

Pure filesystem; no Macaulay2 backend required.
"""
import json

from mobility_toolkit.installer import (
    run_install,
    run_uninstall,
    run_status,
    SKILL_NAMES,
    MCP_NAME,
    _BOOTSTRAP_MARKER,
)

_QUIET = lambda *a, **k: None  # noqa: E731


def test_install_project_level_all_agents(tmp_path):
    proj = str(tmp_path)
    assert run_install(targets=["claude", "codex", "opencode", "antigravity"], project_dir=proj, log=_QUIET)

    # skills copied into each agent's directory
    assert (tmp_path / ".claude" / "skills" / "translate_to_algebra" / "SKILL.md").exists()
    assert (tmp_path / ".agents" / "skills" / "compute_homology_and_mobility" / "SKILL.md").exists()
    assert (tmp_path / ".opencode" / "skills" / "query_vector_db" / "SKILL.md").exists()
    for name in SKILL_NAMES:
        assert (tmp_path / ".claude" / "skills" / name).is_dir()

    # antigravity 2.0 is project-level: .agents/skills (shared w/ codex) + .agents/mcp_config.json
    ag = json.loads((tmp_path / ".agents" / "mcp_config.json").read_text(encoding="utf-8"))
    assert MCP_NAME in ag["mcpServers"]

    # bootstrap injected into copied scripts
    script = tmp_path / ".claude" / "skills" / "translate_to_algebra" / "scripts" / "translate_to_algebra.py"
    assert _BOOTSTRAP_MARKER in script.read_text(encoding="utf-8")

    # claude MCP
    mcp = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert MCP_NAME in mcp["mcpServers"]
    assert mcp["mcpServers"][MCP_NAME]["args"] == ["-m", "mobility_toolkit.mcp_server"]

    # opencode MCP (local type, command as list)
    oc = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert oc["mcp"][MCP_NAME]["type"] == "local"
    assert oc["mcp"][MCP_NAME]["command"][-2:] == ["-m", "mobility_toolkit.mcp_server"]

    # codex MCP (TOML block)
    toml_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert f"[mcp_servers.{MCP_NAME}]" in toml_text

    # AGENTS.md managed block
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "mobility-toolkit:start" in agents and "mobility-toolkit:end" in agents


def test_install_is_idempotent(tmp_path):
    proj = str(tmp_path)
    run_install(targets=["codex"], project_dir=proj, log=_QUIET)
    run_install(targets=["codex"], project_dir=proj, log=_QUIET)

    toml_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert toml_text.count(f"[mcp_servers.{MCP_NAME}]") == 1

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.count("mobility-toolkit:start") == 1


def test_status_reflects_install(tmp_path):
    proj = str(tmp_path)
    before = run_status(project_dir=proj, log=_QUIET)
    assert before["claude"] == {"skills": False, "mcp": False}

    run_install(targets=["claude"], project_dir=proj, log=_QUIET)
    after = run_status(project_dir=proj, log=_QUIET)
    assert after["claude"] == {"skills": True, "mcp": True}


def test_uninstall_removes_entries(tmp_path):
    proj = str(tmp_path)
    run_install(targets=["claude", "codex", "opencode"], project_dir=proj, log=_QUIET)
    run_uninstall(targets=["claude", "codex", "opencode"], project_dir=proj, log=_QUIET)

    assert not (tmp_path / ".claude" / "skills" / "translate_to_algebra").exists()
    mcp = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert MCP_NAME not in mcp.get("mcpServers", {})
    toml_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert f"[mcp_servers.{MCP_NAME}]" not in toml_text
