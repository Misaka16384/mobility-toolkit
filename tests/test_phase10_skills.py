"""Phase-10 skills are thin adapters over the unified service contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from mobility_toolkit.installer import SKILL_NAMES


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "mt-finite-code": "finite.code.capabilities",
    "mt-boundary-algebra": "boundary.finite.capabilities",
    "mt-relative-homology": "topology.relative_homology",
    "mt-defect": "defects.capabilities",
}


def _load_script(skill_name):
    path = (
        ROOT
        / "mobility_toolkit"
        / "skills"
        / skill_name
        / "scripts"
        / f"{skill_name}.py"
    )
    spec = importlib.util.spec_from_file_location(
        "phase10_" + skill_name.replace("-", "_"), path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_phase10_skill_structure_and_inventory():
    for skill_name, operation in SKILLS.items():
        root = ROOT / "mobility_toolkit" / "skills" / skill_name
        assert skill_name in SKILL_NAMES
        assert (root / "SKILL.md").is_file()
        assert (root / "agents" / "openai.yaml").is_file()
        assert (root / "scripts" / f"{skill_name}.py").is_file()
        assert operation in (root / "SKILL.md").read_text(encoding="utf-8")


def test_phase10_scripts_delegate_canonical_request_without_rewriting(monkeypatch):
    for skill_name, operation in SKILLS.items():
        module = _load_script(skill_name)
        request = {
            "schema": "mobility_toolkit.service_request.v1",
            "schema_version": "1",
            "operation": operation,
            "input_data": {},
            "requested_certificate_level": "standard",
            "assumptions": ["test assumption"],
        }
        sentinel = {"schema": "mobility_toolkit.service_execution.v1"}
        calls = []

        def fake_execute(payload):
            calls.append(payload)
            return sentinel

        monkeypatch.setattr(
            module.services, "execute_service_payload", fake_execute
        )
        assert module.run(request) is sentinel
        assert calls == [request]
