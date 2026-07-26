import json
from unittest.mock import patch

import pytest

from mobility_toolkit.__main__ import main


def _stdout_json(mock_stdout):
    return json.loads(
        "".join(call.args[0] for call in mock_stdout.write.call_args_list)
    )


def test_cli_executes_one_canonical_service_request():
    request = {
        "schema": "mobility_toolkit.service_request.v1",
        "operation": "finite.code.capabilities",
        "input_data": {},
        "requested_certificate_level": "standard",
    }
    argv = ["mobility-toolkit", "service", "--request", json.dumps(request)]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 0
    response = _stdout_json(stdout)
    assert response["schema"] == "mobility_toolkit.service_execution.v1"
    assert response["request"]["operation"] == "finite.code.capabilities"
    assert response["result"]["exactness"] == "certified_exact"


def test_cli_service_reads_request_from_stdin():
    request = {
        "operation": "boundary.halfspace.capabilities",
        "input_data": {},
        "requested_certificate_level": "standard",
    }
    argv = ["mobility-toolkit", "service", "--request", "-"]
    with patch("sys.argv", argv), patch(
        "sys.stdin.read", return_value=json.dumps(request)
    ), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 0
    response = _stdout_json(stdout)
    assert response["request"]["operation"] == (
        "boundary.halfspace.capabilities"
    )


def test_cli_catalog_contains_only_native_canonical_adapters():
    argv = ["mobility-toolkit", "service-catalog"]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 0
    catalog = _stdout_json(stdout)
    entries = {
        item["operation"]["operation"]: item for item in catalog["operations"]
    }
    assert "periodic.ext" in entries
    assert "finite.code.analyze" in entries
    assert "boundary.gauge.algorithm1" not in entries
    assert {
        item["operation"]["adapter_kind"] for item in catalog["operations"]
    } == {"native"}


@pytest.mark.parametrize(
    "removed_command",
    (
        "homology",
        "mobility",
        "classify",
        "grobner",
        "fusion-interference",
        "sset-fusion",
        "annihilator-fusion",
        "search",
        "boundary-gauge",
    ),
)
def test_cli_rejects_removed_computational_convenience_commands(
    removed_command,
):
    argv = ["mobility-toolkit", removed_command]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 1
    payload = _stdout_json(stdout)
    assert payload["status"] == "error"
    assert "invalid choice" in payload["error"]


def test_cli_db_remains_an_explicit_administrative_action():
    argv = ["mobility-toolkit", "db", "init"]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 0
    assert _stdout_json(stdout)["status"] == "success"


def test_cli_rejects_malformed_service_request():
    argv = ["mobility-toolkit", "service", "--request", "{}"]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 1
    payload = _stdout_json(stdout)
    assert payload["status"] == "error"
    assert "operation" in payload["error"]
