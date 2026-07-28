import json
from unittest.mock import patch

import pytest

pytest.importorskip("flint")

from mobility_toolkit.__main__ import main
from mobility_toolkit.services import stream_service_payload


_FINGERPRINT = {
    "backend": "python-flint",
    "version": "",
    "algorithm_family": "finite-integer",
}


def _condensate_request(checkpoint=None):
    input_data = {
        "model": "z2-toric",
        "budget": {
            "max_work_units": 1,
            "max_results": 100,
            "max_elements": 100,
            "max_subgroups": 100,
        },
    }
    if checkpoint is not None:
        input_data["checkpoint"] = checkpoint
    return {
        "operation": "boundary.completion2d.enumerate",
        "input_data": input_data,
        "requested_certificate_level": "full",
        "backend_fingerprint": _FINGERPRINT,
    }


def test_stream_pages_can_be_interrupted_and_resumed_from_sealed_checkpoint():
    first_page = next(stream_service_payload(_condensate_request(), max_pages=1))
    checkpoint = first_page["result"]["value"]["next_checkpoint"]
    assert checkpoint is not None
    assert first_page["request"]["input_data"]["max_pages"] == 1

    resumed = list(
        stream_service_payload(
            _condensate_request(checkpoint),
            max_pages=100,
        )
    )
    assert resumed
    assert resumed[0]["request"]["input_data"]["checkpoint"] == checkpoint
    assert resumed[-1]["result"]["value"]["next_checkpoint"] is None
    assert resumed[-1]["result"]["exactness"] == "certified_exact"
    assert all(
        page["schema"] == "mobility_toolkit.service_execution.v1"
        for page in resumed
    )


def test_stream_page_ceiling_preserves_a_resumable_prefix():
    pages = list(stream_service_payload(_condensate_request(), max_pages=2))
    assert len(pages) == 2
    assert pages[-1]["result"]["value"]["next_checkpoint"] is not None


def test_nonstreamable_operation_is_rejected_explicitly():
    with pytest.raises(ValueError, match="not streamable"):
        list(
            stream_service_payload(
                {
                    "operation": "finite.code.capabilities",
                    "input_data": {},
                }
            )
        )


def test_cli_service_stream_emits_one_execution_envelope_per_json_line():
    request = _condensate_request()
    argv = [
        "mobility-toolkit",
        "service-stream",
        "--request",
        json.dumps(request),
        "--max-pages",
        "2",
    ]
    with patch("sys.argv", argv), patch("sys.stdout") as stdout:
        with pytest.raises(SystemExit) as exit_info:
            main()
    assert exit_info.value.code == 0
    encoded = "".join(
        call.args[0] for call in stdout.write.call_args_list
    )
    pages = [json.loads(line) for line in encoded.splitlines() if line]
    assert len(pages) == 2
    assert all(
        page["schema"] == "mobility_toolkit.service_execution.v1"
        for page in pages
    )
    assert pages[-1]["result"]["value"]["next_checkpoint"] is not None
