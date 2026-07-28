import copy
import json
from pathlib import Path

from tools.phase10_verify_dashboard import (
    LAYER_NAMES,
    load_dashboard,
    validate_dashboard,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("phase10_capabilities.json")


def _dashboard():
    return load_dashboard(MANIFEST)


def test_committed_dashboard_passes_release_policy_and_file_checks():
    assert validate_dashboard(_dashboard(), ROOT) == []


def test_every_production_claim_has_all_four_independent_release_layers():
    dashboard = _dashboard()
    evidence_layers = {
        item["id"]: item["layer"] for item in dashboard["evidence"]
    }
    required = set(LAYER_NAMES)
    for capability in dashboard["capabilities"]:
        if capability["status"] != "production":
            continue
        actual = {
            evidence_layers[evidence_id]
            for evidence_id in capability["evidence"]
        }
        assert actual == required, capability["id"]


def test_verifier_rejects_production_promotion_without_cross_backend_evidence():
    dashboard = copy.deepcopy(_dashboard())
    claim = next(
        item
        for item in dashboard["capabilities"]
        if item["id"] == "finite_boundary_e1"
    )
    evidence_by_id = {
        item["id"]: item for item in dashboard["evidence"]
    }
    claim["evidence"] = [
        evidence_id
        for evidence_id in claim["evidence"]
        if evidence_by_id[evidence_id]["layer"] != "cross_backend"
    ]
    errors = validate_dashboard(dashboard, ROOT)
    assert any(
        "finite_boundary_e1 lacks evidence layers: cross_backend" in error
        for error in errors
    )


def test_verifier_rejects_missing_or_fictitious_pytest_nodeid():
    dashboard = copy.deepcopy(_dashboard())
    dashboard["evidence"][0][
        "nodeid"
    ] = "tests/test_finite_stabilizer.py::test_not_a_real_gate"
    errors = validate_dashboard(dashboard, ROOT)
    assert any("test function is not present" in error for error in errors)


def test_bounded_ci_layer_commands_do_not_require_macaulay2():
    dashboard = _dashboard()
    for layer_name in LAYER_NAMES:
        command = dashboard["ci_layers"][layer_name]["smoke_command"]
        command_text = " ".join(command).lower()
        assert "pytest" in command_text
        assert "macaulay" not in command_text
        assert " m2 " not in " %s " % command_text


def test_manifest_is_stable_json_and_docs_name_every_capability():
    dashboard = _dashboard()
    serialized = json.dumps(
        dashboard,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert json.loads(serialized) == dashboard
    documentation = (ROOT / "docs" / "CAPABILITY_DASHBOARD.md").read_text(
        encoding="utf-8"
    )
    for capability in dashboard["capabilities"]:
        assert "`%s`" % capability["id"] in documentation
