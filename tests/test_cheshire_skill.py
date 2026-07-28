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
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    return payload


def test_mt_cheshire_skill_open_segment_smoke():
    request = {
        "operation": "defects.cheshire.static_toric",
        "input_data": {
            "shape": [2, 1, 1],
            "periodic_axes": [],
            "defects": [
                {
                    "defect_id": "gamma",
                    "topology": "open_segment",
                    "cube_bases": [[0, 0, 0], [1, 0, 0]],
                }
            ],
        },
        "requested_certificate_level": "standard",
    }
    payload = _run(request)
    assert payload["schema"] == "mobility_toolkit.service_execution.v1"
    result = payload["result"]
    value = result["value"]
    assert result["operation"] == "defects.cheshire.static_toric"
    assert result["exactness"] == "certified_exact"
    assert value["bulk_analysis"]["codespace_dimension"] == 1
    assert value["local_analysis"]["codespace_dimension"] == 2
    assert value["fixed_sector_analysis"]["codespace_dimension"] == 1
    assert value["pinned_elimination_certificate"]["verified"]
    transformation = value["defect_reports"][0]["transformation_certificate"]
    assert transformation["product_identity_verified"]
    assert transformation["local_commutation_verified"]


def test_mt_cheshire_v2_capabilities_separate_static_and_dynamic_scope():
    payload = _run(
        {
            "operation": "defects.cheshire.capabilities",
            "input_data": {},
        },
        timeout=30,
    )
    capabilities = payload["result"]["value"]

    assert capabilities["static_fusion"].startswith("certified_exact")
    assert capabilities["xcube_axial_reference"].startswith("experimental")
    assert capabilities["finite_depth_circuit"] == "unsupported"
    assert capabilities["phase_equivalence"] == "unsupported"


def test_mt_cheshire_v2_xcube_reference_is_machine_readable_experimental():
    payload = _run(
        {
            "operation": "defects.cheshire.xcube_axial_reference",
            "input_data": {
                "line_length_lattice_steps": 1,
            },
            "requested_certificate_level": "standard",
        },
        timeout=60,
    )

    result = payload["result"]
    assert result["exactness"] == "experimental"
    assert dict(result["verification"])["thermodynamic_claim"] is False
    assert result["value"]["certificate"]["verified"]
