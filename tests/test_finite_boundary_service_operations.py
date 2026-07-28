import pytest

pytest.importorskip("flint")

from mobility_toolkit.services import (
    ServiceExecutor,
    ServiceRequest,
    default_service_catalog,
    execute_service_payload,
)


def _mixed_code():
    return {
        "sites": [
            {"site_id": "q2", "dimension": 2},
            {"site_id": "q4", "dimension": 4},
        ],
        "generators": [
            {
                "phase": 0,
                "terms": [
                    {"site_id": "q2", "x": 0, "z": 1},
                    {"site_id": "q4", "x": 0, "z": 2},
                ],
            }
        ],
    }


def _ququart_window():
    return {
        "sites": [
            {"site_id": "q2", "dimension": 2},
            {"site_id": "q4", "dimension": 4},
        ],
        "generators": [
            {
                "phase": 0,
                "terms": [{"site_id": "q2", "x": 0, "z": 1}],
            }
        ],
        "window": {
            "window_id": "ququart-boundary-window",
            "site_ids": ["q4"],
            "search_extent": [{"name": "depth", "value": 0}],
        },
    }


def test_catalog_registers_actual_finite_boundary_and_bounded_search_operations():
    catalog = default_service_catalog()
    entries = {
        item["operation"]["operation"]: item for item in catalog["operations"]
    }
    assert {
        "finite.code.analyze",
        "boundary.finite.analyze",
        "boundary.finite.enumerate_e1",
        "boundary.finite.e2.reference_z2_swap",
    } <= set(entries)
    finite_schema = entries["finite.code.analyze"]["operation"]["input_schema"]
    encoded = repr(finite_schema)
    assert "dimension" in encoded
    assert "phase" in encoded
    assert "qudit_dim" not in encoded
    assert "prime_bypass" not in encoded
    assert (
        entries["boundary.finite.e2.reference_z2_swap"]["capability"][
            "maximum_exactness"
        ]
        == "bounded_exact"
    )
    finite_capability = execute_service_payload(
        {"operation": "finite.code.capabilities", "input_data": {}}
    )
    assert finite_capability["result"]["value"]["registered_operations"] == [
        "finite.code.analyze"
    ]
    boundary_capability = execute_service_payload(
        {"operation": "boundary.finite.capabilities", "input_data": {}}
    )
    assert boundary_capability["result"]["value"]["generic_e2_transport_decoder"] is False


def test_finite_code_analyze_supports_mixed_and_composite_dimensions():
    response = execute_service_payload(
        {"operation": "finite.code.analyze", "input_data": _mixed_code()}
    )
    result = response["result"]
    assert result["exactness"] == "certified_exact"
    assert result["certificate_level"] == "full"
    assert result["value"]["codespace_dimension"] == 4
    assert result["value"]["module"]["phase_modulus"] == 8
    verification = dict(result["verification"])
    assert verification["mixed_local_dimensions"] is True
    assert verification["generator_relations_scalar_free"] is True
    assert verification["stabilizer_validation_valid"] is True
    assert response["cache"]["hit"] is False


def test_phase_aware_decoder_rejects_scalar_generating_relation():
    bad = {
        "sites": [{"site_id": "q", "dimension": 2}],
        "generators": [
            {
                "phase": 1,
                "terms": [{"site_id": "q", "x": 1, "z": 0}],
            }
        ],
    }
    with pytest.raises(ValueError, match="nontrivial scalar"):
        execute_service_payload(
            {"operation": "finite.code.analyze", "input_data": bad}
        )


@pytest.mark.parametrize("removed_name", ("qudit_dim", "prime_bypass"))
def test_finite_decoder_rejects_removed_uniform_prime_compatibility_fields(
    removed_name,
):
    payload = _mixed_code()
    payload[removed_name] = 2 if removed_name == "qudit_dim" else True
    with pytest.raises(ValueError, match=removed_name):
        execute_service_payload(
            {"operation": "finite.code.analyze", "input_data": payload}
        )


def test_strict_nested_pauli_decoder_rejects_unknown_and_duplicate_local_terms():
    unknown = _mixed_code()
    unknown["sites"][0]["label"] = "legacy-coordinate-zero"
    with pytest.raises(ValueError, match="label"):
        execute_service_payload(
            {"operation": "finite.code.analyze", "input_data": unknown}
        )

    duplicate = {
        "sites": [{"site_id": "q", "dimension": 4}],
        "generators": [
            {
                "phase": 0,
                "terms": [
                    {"site_id": "q", "x": 1, "z": 0},
                    {"site_id": "q", "x": 0, "z": 1},
                ],
            }
        ],
    }
    with pytest.raises(ValueError, match="repeats local site"):
        execute_service_payload(
            {"operation": "finite.code.analyze", "input_data": duplicate}
        )


def test_finite_boundary_analyze_computes_exact_ququart_paired_window():
    response = execute_service_payload(
        {"operation": "boundary.finite.analyze", "input_data": _ququart_window()}
    )
    result = response["result"]
    assert result["exactness"] == "bounded_exact"
    assert result["certificate_level"] == "standard"
    assert result["value"]["invariant_factors"] == [4, 4]
    assert result["value"]["order"] == 16
    assert result["value"]["window"]["site_ids"] == ["q4"]
    assert result["value"]["window"]["search_extent"] == [["depth", 0]]
    verification = dict(result["verification"])
    assert verification["finite_window_only"] is True
    assert verification["thermodynamic_completeness"] is False


def test_e1_service_is_complete_only_when_its_certificate_says_so():
    finite_window = {
        "sites": [{"site_id": "q", "dimension": 2}],
        "generators": [],
        "window": {"window_id": "one-qubit-window", "site_ids": ["q"]},
    }
    complete = execute_service_payload(
        {
            "operation": "boundary.finite.enumerate_e1",
            "input_data": finite_window,
        }
    )
    assert complete["result"]["exactness"] == "certified_exact"
    assert complete["result"]["certificate"]["certified_complete"] is True
    assert len(complete["result"]["value"]["candidates"]) == 4

    bounded = dict(finite_window)
    bounded["budget"] = {"max_elements": 1}
    incomplete = execute_service_payload(
        {
            "operation": "boundary.finite.enumerate_e1",
            "input_data": bounded,
        }
    )
    assert incomplete["result"]["exactness"] == "experimental"
    assert incomplete["result"]["certificate"]["certified_complete"] is False
    assert incomplete["result"]["value"]["checkpoint"] is not None


def test_e2_transport_is_source_locked_and_bounded_complete_for_its_fixed_domain():
    response = execute_service_payload(
        {
            "operation": "boundary.finite.e2.reference_z2_swap",
            "input_data": {},
        }
    )
    result = response["result"]
    assert result["exactness"] == "bounded_exact"
    assert result["certificate_level"] == "full"
    assert result["certificate"]["bounded_complete"] is True
    assert result["certificate"]["termination"] == "exhausted"
    assert dict(result["verification"]) == {
        "bounded_complete": True,
        "source_locked_reference": True,
        "thermodynamic_completeness": False,
    }
    assert any("not an automatically extracted" in item for item in result["warnings"])


def test_external_backend_results_are_not_cached_without_a_fingerprint():
    executor = ServiceExecutor()
    request = ServiceRequest("finite.code.analyze", _mixed_code())
    assert executor.execute(request).cache_hit is False
    assert executor.execute(request).cache_hit is False
