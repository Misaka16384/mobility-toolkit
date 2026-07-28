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
    stdout = completed.stdout.strip()
    output = json.loads(stdout) if stdout else None
    return completed, output


def _request(operation, input_data=None):
    return {
        "schema": "mobility_toolkit.service_request.v1",
        "schema_version": "1",
        "operation": operation,
        "input_data": {} if input_data is None else input_data,
        "requested_certificate_level": "standard",
        "assumptions": [],
    }


def test_capabilities_are_json_serializable():
    operation = "boundary.halfspace.capabilities"
    completed, output = _run(_request(operation))

    assert completed.returncode == 0
    assert output["schema"] == "mobility_toolkit.service_execution.v1"
    assert output["request"]["operation"] == operation
    assert output["capability"]["operation"] == operation
    assert output["capability"]["supported"] is True
    assert output["result"]["operation"] == operation
    result = output["result"]["value"]
    assert result["halfspace"]["schema"].startswith(
        "mobility_toolkit.halfspace_capability_report."
    )
    assert (
        result["boundary_module"]["generic_full_boundary_module"]
        == "unsupported"
    )


def test_geometry_retains_orientation_and_offset():
    operation = "boundary.halfspace.geometry"
    completed, output = _run(
        _request(
            operation,
            {
                "normal": [2, 2, -2],
                "boundary_offset": 3,
            },
        )
    )

    assert completed.returncode == 0
    assert output["request"]["input_data"]["normal"] == [2, 2, -2]
    assert output["result"]["operation"] == operation
    assert output["result"]["exactness"] == "certified_exact"
    result = output["result"]["value"]
    half_space = result["half_space"]
    assert half_space["normal"]["components"] == [1, 1, -1]
    assert half_space["boundary_offset"] == 3
    assert result["basis_change"]["certificate"]["verified"] is True


def test_orientation_comparison_is_not_lost_in_adapter():
    operation = "boundary.halfspace.compare_orientations"
    completed, output = _run(
        _request(
            operation,
            {
                "left_normal": [0, 0, 1],
                "right_normal": [0, 0, -7],
            },
        )
    )

    assert completed.returncode == 0
    assert output["request"]["operation"] == operation
    assert output["result"]["operation"] == operation
    assert output["result"]["value"] == "opposite"
    assert output["result"]["certificate"] == "opposite"


def test_source_locked_toric2d_benchmark_runs_through_skill():
    operation = "boundary.halfspace.toric2d"
    completed, output = _run(_request(operation))

    assert completed.returncode == 0
    assert output["request"]["operation"] == operation
    assert output["result"]["operation"] == operation
    assert output["result"]["theorem_scope"]
    result = output["result"]["value"]
    assert result["certificate"]["no_secondary_operators"] is True
    assert result["boundary_to_bulk_map"]["is_isomorphism"] is True


def test_invalid_operation_has_machine_readable_failure():
    operation = "boundary.halfspace.periodic_normal_quotient"
    completed, output = _run(_request(operation))

    assert completed.returncode != 0
    if output is None:
        assert operation in completed.stderr
    else:
        assert output["status"] == "error"
        assert operation in output["error"]
