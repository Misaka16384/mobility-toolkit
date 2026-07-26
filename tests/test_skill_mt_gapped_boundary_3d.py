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
    return completed, json.loads(completed.stdout)


def _constant_pairing_request():
    return {
        "operation": "symbolic",
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
    }


def test_capabilities_do_not_claim_completion_or_thermodynamic_e3():
    completed, output = _run({"operation": "capabilities"})

    assert completed.returncode == 0
    result = output["result"]
    assert result["e1_finite_isotropic_subgroups"].startswith("certified_exact")
    assert result["e2_local_completions"] == "unsupported"
    assert result["e3_thermodynamic_classification"] == "unsupported"


def test_symbolic_adapter_exhausts_small_odd_prime_seed_domain():
    completed, output = _run(_constant_pairing_request())

    assert completed.returncode == 0
    result = output["result"]
    assert result["exactness"] == "bounded_exact"
    assert len(result["candidate_hashes"]) == 4
    assert result["next_checkpoint"] is None
    assert result["final_certificate"]["bounded_complete"] is True
    assert all(
        item["phase_assignment_machine_verified"] is False
        for item in result["candidates"]
    )


def test_symbolic_adapter_requires_explicit_full_boundary_assertion():
    request = _constant_pairing_request()
    request["full_boundary_module_supplied"] = False
    completed, output = _run(request)

    assert completed.returncode == 1
    assert output["status"] == "error"
    assert "primary-only input is insufficient" in output["error"]


def test_toric_primary_preflight_remains_unsupported_for_e3():
    completed, output = _run({"operation": "toric3d-primary-preflight"})

    assert completed.returncode == 0
    result = output["result"]
    assert result["exactness"] == "unsupported"
    assert result["value"]["source_verified"] is True
    assert result["value"]["symbolic_search_supported"] is False


def test_xcube_preflight_preserves_orientation_without_running_e3():
    _, axial = _run(
        {"operation": "xcube-preflight", "normal": [0, 0, 1]}
    )
    _, diagonal = _run(
        {"operation": "xcube-preflight", "normal": [1, 1, 1]}
    )

    assert axial["result"]["value"]["orientation_behavior"] == "not_surjective"
    assert diagonal["result"]["value"]["orientation_behavior"] == "isomorphism"
    assert axial["result"]["exactness"] == "unsupported"
    assert diagonal["result"]["exactness"] == "unsupported"
