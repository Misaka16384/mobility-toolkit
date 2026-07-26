import json
from unittest.mock import patch

import pytest

from mobility_toolkit.__main__ import main
from mobility_toolkit.mcp_server import service as mcp_service
from mobility_toolkit.services import execute_service_payload


def _without_runtime_cache(response):
    copy = dict(response)
    copy.pop("cache")
    return copy


def test_python_cli_and_mcp_share_the_same_service_schema_and_execute_function():
    request = {
        "schema": "mobility_toolkit.service_request.v1",
        "operation": "boundary.halfspace.capabilities",
        "input_data": {},
        "requested_certificate_level": "standard",
    }
    python_response = execute_service_payload(request)
    mcp_response = mcp_service(request)

    argv = ["mobility-toolkit", "service", "--request", json.dumps(request)]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 0
    cli_response = json.loads(
        "".join(call.args[0] for call in stdout.write.call_args_list)
    )

    assert _without_runtime_cache(python_response) == _without_runtime_cache(
        mcp_response
    )
    assert _without_runtime_cache(python_response) == _without_runtime_cache(
        cli_response
    )
    for response in (python_response, mcp_response, cli_response):
        assert response["schema"] == "mobility_toolkit.service_execution.v1"
        assert response["request"]["schema"] == "mobility_toolkit.service_request.v1"
        assert response["result"]["schema"] == "mobility_toolkit.computation_result.v1"
        assert (
            response["capability"]["schema"]
            == "mobility_toolkit.service_capability.v1"
        )


def test_cli_rejects_removed_homology_convenience_command():
    argv = [
        "mobility-toolkit",
        "homology",
        "--stabilizer",
        '[["1", "0"]]',
        "--qudit-dim",
        "2",
        "--prime-bypass",
    ]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 1
    payload = json.loads(
        "".join(call.args[0] for call in stdout.write.call_args_list)
    )
    assert payload["status"] == "error"
    assert "invalid choice" in payload["error"]


def test_cli_rejects_removed_classify_convenience_command():
    argv = [
        "mobility-toolkit",
        "classify",
        "--krull-dim",
        "0",
        "--spatial-dim",
        "3",
    ]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 1
    payload = json.loads(
        "".join(call.args[0] for call in stdout.write.call_args_list)
    )
    assert payload["status"] == "error"
    assert "invalid choice" in payload["error"]


def test_mcp_surface_exposes_only_generic_service_tools():
    import mobility_toolkit.mcp_server as server

    assert callable(server.service)
    assert callable(server.service_catalog)
    assert not hasattr(server, "compute_boundary_gauge")
    assert not hasattr(server, "compute_homology")
