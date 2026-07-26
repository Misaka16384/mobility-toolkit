import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("flint")


SCRIPT = (
    Path(__file__).parents[1]
    / "mobility_toolkit"
    / "skills"
    / "mt-gapped-boundary-2d"
    / "scripts"
    / "mt-gapped-boundary-2d.py"
)


def _run(request):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def _request(operation, input_data=None, certificate_level="full"):
    return {
        "schema": "mobility_toolkit.service_request.v1",
        "schema_version": "1",
        "operation": operation,
        "input_data": {} if input_data is None else input_data,
        "requested_certificate_level": certificate_level,
    }


def _assert_execution(response, operation):
    assert response["schema"] == "mobility_toolkit.service_execution.v1"
    assert response["capability"]["operation"] == operation
    assert response["capability"]["supported"]
    assert response["request"]["schema"] == "mobility_toolkit.service_request.v1"
    assert response["request"]["operation"] == operation
    assert response["result"]["schema"] == "mobility_toolkit.computation_result.v1"
    assert response["result"]["operation"] == operation
    assert (
        response["result"]["canonical_input_hash"]
        == response["request"]["canonical_input_hash"]
    )
    return response["result"]


def test_skill_reports_honest_capabilities():
    response = _run(
        _request(
            "boundary.completion2d.capabilities",
            certificate_level="standard",
        )
    )
    result = _assert_execution(
        response, "boundary.completion2d.capabilities"
    )
    value = result["value"]
    assert result["exactness"] == "certified_exact"
    assert value["metric_group_condensation"] == "certified_exact"
    assert value["finite_local_completion"] == "bounded_exact"
    assert value["automatic_stabilizer_anyon_extraction"] == "unsupported"
    assert value["thermodynamic_gap_proof"] == "unsupported"
    assert "no gapped-boundary theorem" in result["theorem_scope"].lower()


def test_skill_enumerates_double_semion_lagrangian():
    response = _run(
        _request(
            "boundary.completion2d.enumerate",
            {"model": "double-semion"},
        )
    )
    result = _assert_execution(response, "boundary.completion2d.enumerate")
    value = result["value"]
    assert result["exactness"] == "certified_exact"
    assert value["next_checkpoint"] is None
    assert sum(item["lagrangian"] for item in value["candidates"]) == 1
    assert result["certificate"]["lagrangian_subgroups"] == 1
    assert dict(result["verification"])["output_complete"]
    assert "raw bosonic subgroups" in result["theorem_scope"]
    assert any(
        "No microscopic completion" in warning
        for warning in result["warnings"]
    )


@pytest.mark.parametrize("model", ("z2-toric", "z4-toric"))
@pytest.mark.parametrize("boundary_kind", ("rough", "smooth"))
def test_skill_runs_source_locked_toric_completion(model, boundary_kind):
    modulus = 2 if model == "z2-toric" else 4
    response = _run(
        _request(
            "boundary.completion2d.toric_cut",
            {
                "modulus": modulus,
                "boundary_kind": boundary_kind,
            },
        )
    )
    result = _assert_execution(response, "boundary.completion2d.toric_cut")
    value = result["value"]
    assert result["exactness"] == "bounded_exact"
    assert value["anyon_fusion_invariant_factors"] == [modulus, modulus]
    assert value["condensate_invariant_factors"] == [modulus]
    assert value["certificate"]["termination_verified"]
    assert dict(result["verification"])["short_string_termination_verified"]
    assert "finite 2d patch" in result["theorem_scope"].lower()
    assert any(
        "no completeness claim" in warning
        for warning in result["warnings"]
    )


def test_skill_parses_and_verifies_explicit_uniform_composite_completion():
    response = _run(
        _request(
            "boundary.completion2d.verify",
            {
                "model": "z4-toric",
                "sites": [
                    {
                        "site_id": "remote",
                        "dimension": 4,
                        "coordinate": [0, 0],
                        "depth": 1,
                    },
                    {
                        "site_id": "boundary",
                        "dimension": 4,
                        "coordinate": [1, 0],
                        "depth": 0,
                    },
                ],
                "bulk_terms": [
                    {
                        "term_id": "bulk:remote",
                        "terms": [{"site_id": "remote", "x": 1}],
                    }
                ],
                "boundary_terms": [
                    {
                        "term_id": "boundary:pin",
                        "terms": [{"site_id": "boundary", "z": 1}],
                    }
                ],
                "string_lifts": [
                    {
                        "label": "electric",
                        "anyon": [1, 0],
                        "operator": {
                            "terms": [{"site_id": "remote", "z": 1}]
                        },
                        "remote_excitation_term_ids": ["bulk:remote"],
                    }
                ],
                "locality": {
                    "window_label": "explicit-z4-two-site-test",
                    "boundary_site_ids": ["boundary"],
                    "max_completion_depth": 1,
                    "max_boundary_term_sites": 1,
                    "max_boundary_term_diameter": 0,
                    "max_short_string_sites": 1,
                },
                "source_scope": "explicit parser regression",
            },
        )
    )
    result = _assert_execution(response, "boundary.completion2d.verify")
    value = result["value"]
    assert result["exactness"] == "bounded_exact"
    assert value["codespace_dimension"] == 1
    assert value["certificate"]["termination_witnesses"][0][
        "exact_remote_syndrome_verified"
    ]
    assert dict(result["verification"])["short_string_termination_verified"]
    assert "does not prove a thermodynamic spectral gap" in result[
        "theorem_scope"
    ].lower()
    assert any(
        "no completeness claim" in warning
        for warning in result["warnings"]
    )
