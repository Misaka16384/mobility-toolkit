import json
import subprocess
import sys
from pathlib import Path


def _script():
    return (
        Path(__file__).parents[1]
        / "mobility_toolkit"
        / "skills"
        / "mt-cheshire"
        / "scripts"
        / "mt-cheshire.py"
    )


def _run(request, timeout=180):
    completed = subprocess.run(
        [sys.executable, str(_script())],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 0, payload
    return payload


def test_mt_cheshire_skill_open_segment_smoke():
    request = {
        "operation": "static",
        "shape": [2, 1, 1],
        "periodic_axes": [],
        "defects": [
            {
                "defect_id": "gamma",
                "topology": "open_segment",
                "cube_bases": [[0, 0, 0], [1, 0, 0]],
            }
        ],
    }
    payload = _run(request)
    assert payload["status"] == "success"
    assert payload["operation"] == "static"
    assert payload["exactness"] == "certified_exact"
    assert payload["bulk"]["codespace_dimension"] == 1
    assert payload["local_hamiltonian"]["codespace_dimension"] == 2
    assert payload["fixed_charge_sectors"]["codespace_dimension"] == 1
    assert payload["representations"]["deleted_tube_matches_direct_line"]
    assert payload["defects"][0]["eq8_construction_verified"]


def test_mt_cheshire_v2_capabilities_separate_static_and_dynamic_scope():
    payload = _run({"operation": "capabilities"}, timeout=30)

    assert payload["static_fusion"].startswith("certified_exact")
    assert payload["xcube_axial_reference"].startswith("experimental")
    assert payload["finite_depth_circuit"] == "unsupported"
    assert payload["phase_equivalence"] == "unsupported"


def test_mt_cheshire_v2_xcube_reference_is_machine_readable_experimental():
    payload = _run(
        {
            "operation": "fracton-reference",
            "line_length_lattice_steps": 1,
        },
        timeout=60,
    )

    result = payload["result"]
    assert result["exactness"] == "experimental"
    assert dict(result["verification"])["thermodynamic_claim"] is False
    assert result["value"]["certificate"]["verified"]
