import json
from pathlib import Path
import subprocess
import sys


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "mobility_toolkit"
    / "skills"
    / "mt-gapped-boundary-3d"
    / "scripts"
    / "mt-gapped-boundary-3d.py"
)


def _run(payload):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        check=False,
        text=True,
    )
    output = json.loads(completed.stdout) if completed.stdout else None
    return completed, output


def _service_request(
    operation,
    input_data=None,
    *,
    certificate_level="standard",
    equivalence_relation="raw",
):
    return {
        "schema": "mobility_toolkit.service_request.v1",
        "schema_version": "1",
        "operation": operation,
        "input_data": input_data or {},
        "requested_certificate_level": certificate_level,
        "equivalence_relation": equivalence_relation,
    }


def _successful_result(completed, output, operation):
    assert completed.returncode == 0, completed.stderr
    assert output["schema"] == "mobility_toolkit.service_execution.v1"
    assert output["request"]["schema"] == "mobility_toolkit.service_request.v1"
    assert output["request"]["operation"] == operation
    assert output["capability"]["operation"] == operation
    assert output["result"]["operation"] == operation
    return output["result"]


def _constant_pairing_request():
    return _service_request(
        "boundary.symbolic3d.enumerate",
        {
            "full_boundary_module_supplied": True,
            "coefficient_modulus": 3,
            "normal": [0, 0, 1],
            "generator_labels": ["e", "m"],
            "pairing_matrix": [
                [[], [{"coefficient": 1, "exponents": [0, 0]}]],
                [[{"coefficient": 2, "exponents": [0, 0]}], []],
            ],
            "exponent_bounds": [[0, 0], [0, 0]],
            "max_generators": 2,
            "equivalence": "raw_constant_generator_change",
            "max_pages": 1,
        },
        certificate_level="full",
        equivalence_relation="raw_constant_generator_change",
    )


def test_capabilities_do_not_claim_completion_or_thermodynamic_e3():
    operation = "boundary.symbolic3d.capabilities"
    completed, output = _run(_service_request(operation))

    result = _successful_result(completed, output, operation)
    assert result["exactness"] == "certified_exact"
    value = result["value"]
    assert value["e1_finite_isotropic_subgroups"].startswith(
        "python_api_certified_exact"
    )
    assert value["e2_local_completions"] == "unsupported"
    assert value["e3_thermodynamic_classification"] == "unsupported"
    assert "no thermodynamic 3D boundary classification" in result["theorem_scope"]


def test_symbolic_adapter_exhausts_small_odd_prime_seed_domain():
    completed, output = _run(_constant_pairing_request())

    result = _successful_result(
        completed, output, "boundary.symbolic3d.enumerate"
    )
    assert result["exactness"] == "bounded_exact"
    value = result["value"]
    assert len(value["candidate_hashes"]) == 4
    assert value["next_checkpoint"] is None
    assert result["certificate"]["bounded_complete"] is True
    assert result["certificate"]["thermodynamic_completeness_claimed"] is False
    assert all(
        item["phase_assignment_machine_verified"] is False
        for item in value["candidates"]
    )
    assert all(
        item["saturation_status"] == "unsupported"
        and item["anomaly_status"] == "unsupported"
        and item["local_completion_status"] == "unsupported"
        and item["thermodynamic_gapped_boundary_claimed"] is False
        for item in value["candidates"]
    )


def test_symbolic_adapter_reports_an_experimental_prefix_when_budget_stops():
    request = _constant_pairing_request()
    request["input_data"]["budget"] = {
        "max_seed_presentations": 1,
        "max_output_candidates": 100,
    }
    completed, output = _run(request)

    result = _successful_result(
        completed, output, "boundary.symbolic3d.enumerate"
    )
    assert result["exactness"] == "experimental"
    assert result["value"]["next_checkpoint"] is not None
    assert result["certificate"]["bounded_complete"] is False
    assert result["certificate"]["thermodynamic_completeness_claimed"] is False
    assert "recorded Laurent exponent box" in result["theorem_scope"]


def test_symbolic_adapter_requires_explicit_full_boundary_assertion():
    request = _constant_pairing_request()
    request["input_data"]["full_boundary_module_supplied"] = False
    completed, output = _run(request)

    assert completed.returncode == 1
    assert output is None
    assert "primary-only input is insufficient" in completed.stderr


def test_toric_primary_preflight_remains_unsupported_for_e3():
    operation = "boundary.symbolic3d.toric_primary_preflight"
    completed, output = _run(_service_request(operation))

    result = _successful_result(completed, output, operation)
    assert result["exactness"] == "unsupported"
    assert result["value"]["source_verified"] is True
    assert result["value"]["free_full_boundary_module_available"] is False
    assert result["value"]["symbolic_search_supported"] is False
    assert "no symbolic candidate enumeration" in result["theorem_scope"]


def test_xcube_preflight_preserves_orientation_without_running_e3():
    operation = "boundary.symbolic3d.xcube_preflight"
    axial_completed, axial = _run(
        _service_request(operation, {"normal": [0, 0, 1]})
    )
    diagonal_completed, diagonal = _run(
        _service_request(operation, {"normal": [1, 1, 1]})
    )

    axial_result = _successful_result(axial_completed, axial, operation)
    diagonal_result = _successful_result(
        diagonal_completed, diagonal, operation
    )
    assert axial_result["value"]["orientation_behavior"] == "not_surjective"
    assert diagonal_result["value"]["orientation_behavior"] == "isomorphism"
    assert axial_result["exactness"] == "unsupported"
    assert diagonal_result["exactness"] == "unsupported"
    assert axial_result["value"]["free_full_boundary_module_available"] is False
    assert diagonal_result["value"]["symbolic_search_supported"] is False
