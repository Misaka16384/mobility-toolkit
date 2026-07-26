import json
from pathlib import Path
import subprocess
import sys


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "mobility_toolkit"
    / "skills"
    / "mt-halfspace"
    / "scripts"
    / "mt-halfspace.py"
)


def _run(payload):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        check=False,
        text=True,
    )
    output = json.loads(completed.stdout)
    return completed, output


def test_capabilities_are_json_serializable():
    completed, output = _run({"operation": "capabilities"})

    assert completed.returncode == 0
    assert output["status"] == "success"
    assert output["result"]["halfspace"]["schema"].startswith(
        "mobility_toolkit.halfspace_capability_report."
    )
    assert (
        output["result"]["boundary_module"]["generic_full_boundary_module"]
        == "unsupported"
    )


def test_geometry_retains_orientation_and_offset():
    completed, output = _run(
        {
            "operation": "geometry",
            "normal": [2, 2, -2],
            "boundary_offset": 3,
        }
    )

    assert completed.returncode == 0
    assert output["status"] == "success"
    half_space = output["result"]["half_space"]
    assert half_space["normal"]["components"] == [1, 1, -1]
    assert half_space["boundary_offset"] == 3
    assert output["result"]["basis_change"]["certificate"]["verified"] is True


def test_orientation_comparison_is_not_lost_in_adapter():
    completed, output = _run(
        {
            "operation": "compare-orientations",
            "left_normal": [0, 0, 1],
            "right_normal": [0, 0, -7],
        }
    )

    assert completed.returncode == 0
    assert output == {"result": "opposite", "status": "success"}


def test_source_locked_toric2d_benchmark_runs_through_skill():
    completed, output = _run({"operation": "toric2d"})

    assert completed.returncode == 0
    assert output["status"] == "success"
    result = output["result"]["value"]
    assert result["certificate"]["no_secondary_operators"] is True
    assert result["boundary_to_bulk_map"]["is_isomorphism"] is True


def test_invalid_operation_has_machine_readable_failure():
    completed, output = _run({"operation": "periodic-normal-quotient"})

    assert completed.returncode == 1
    assert output["status"] == "error"
    assert output["error"].startswith("ValueError:")
