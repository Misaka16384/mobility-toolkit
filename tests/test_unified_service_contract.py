import json

import pytest

from mobility_toolkit.core import CertificateLevel
from mobility_toolkit.services import (
    ServiceExecutor,
    ServiceRequest,
    build_default_registry,
    default_service_catalog,
    execute_service_payload,
)


def test_transport_request_is_strict_versioned_and_json_roundtrippable():
    payload = {
        "schema": ServiceRequest.SCHEMA_ID,
        "schema_version": "1",
        "operation": "boundary.halfspace.capabilities",
        "input_data": {},
        "requested_certificate_level": "standard",
        "assumptions": ["flat rational half-space"],
    }
    request = ServiceRequest.from_transport_dict(payload)
    assert request.requested_certificate_level is CertificateLevel.STANDARD
    encoded = request.to_transport_dict()
    assert encoded["schema"] == ServiceRequest.SCHEMA_ID
    assert encoded["requested_certificate_level"] == "standard"
    json.dumps(encoded)

    with pytest.raises(ValueError, match="prime_bypass"):
        ServiceRequest.from_transport_dict(
            {
                "operation": "homology.ext",
                "input_data": {},
                "prime_bypass": True,
            }
        )
    with pytest.raises(ValueError, match="unsupported service request schema"):
        ServiceRequest.from_transport_dict(
            {
                "schema": "mobility_toolkit.service_request.v999",
                "operation": "homology.ext",
                "input_data": {},
            }
        )


def test_default_catalog_is_machine_readable_and_honest_about_adapters():
    catalog = default_service_catalog()
    assert catalog["schema"] == "mobility_toolkit.service_catalog.v2"
    assert catalog["service_api_version"] == "2"
    by_name = {
        item["operation"]["operation"]: item for item in catalog["operations"]
    }
    assert {
        "periodic.presentation",
        "periodic.ext",
        "periodic.charge_module",
        "boundary.halfspace.toric2d",
        "boundary.halfspace.toric3d_primary",
        "boundary.halfspace.xcube_orientation",
        "boundary.completion2d.toric_cut",
        "finite.code.capabilities",
        "boundary.finite.capabilities",
        "topology.relative_homology",
        "defects.capabilities",
        "defects.cheshire.classify_abelian",
        "defects.cheshire.toric2d_reference",
        "defects.cheshire.fuse",
        "defects.cheshire.realize_toric2d",
        "defects.cheshire.circuit_toric2d",
        "defects.cheshire.toric3d_finite_reference",
        "defects.cheshire.xcube_candidates",
    } <= set(by_name)
    assert (
        by_name["boundary.halfspace.toric2d"]["operation"]["adapter_kind"]
        == "native"
    )
    assert {
        item["operation"]["adapter_kind"] for item in catalog["operations"]
    } == {"native"}
    encoded = json.dumps(catalog, sort_keys=True)
    assert "prime_bypass" not in encoded
    assert "legacy_dict_adapter" not in encoded
    assert "boundary.gauge.algorithm1" not in encoded
    assert "homology.ext" not in encoded
    assert "maximum_exactness" in encoded
    assert "input_schema" in encoded


def test_relative_homology_service_decodes_and_certifies_an_explicit_pair():
    pytest.importorskip("flint")
    response = execute_service_payload(
        {
            "operation": "topology.relative_homology",
            "input_data": {
                "ambient": {
                    "cell_ids_by_dimension": [["v0", "v1"], ["e01"]],
                    "boundary_maps": [
                        {"nrows": 0, "ncols": 2, "entries": []},
                        {
                            "nrows": 2,
                            "ncols": 1,
                            "entries": [[0, 0, -1], [1, 0, 1]],
                        },
                    ],
                    "assumptions": ["oriented unit interval"],
                },
                "subcomplex_cell_ids_by_dimension": [["v0", "v1"], []],
                "degree": 1,
                "coefficient_modulus": 4,
            },
        }
    )
    assert response["result"]["exactness"] == "certified_exact"
    assert response["result"]["certificate_level"] == "full"
    assert response["result"]["value"]["homology"]["invariant_factors"] == [4]
    assert response["result"]["value"]["homology"]["order"] == 4
    assert response["capability"]["maximum_exactness"] == "certified_exact"


def test_executor_cache_revalidates_full_request_and_backend_sensitive_rules():
    executor = ServiceExecutor()
    request = ServiceRequest(
        "boundary.halfspace.capabilities",
        {},
        requested_certificate_level=CertificateLevel.STANDARD,
        assumptions=("software capability declaration",),
    )
    first = executor.execute(request)
    second = executor.execute(request)
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert first.result == second.result

    changed = ServiceRequest(
        request.operation,
        request.input_data,
        request.requested_certificate_level,
        ("different assumption",),
    )
    assert executor.execute(changed).cache_hit is False
    assert build_default_registry().is_cacheable("periodic.ext") is False


@pytest.mark.parametrize(
    "operation",
    (
        "homology.ext",
        "mobility.classify",
        "periodic.gsd",
        "fusion.interference",
        "boundary.gauge.algorithm1",
    ),
)
def test_removed_legacy_operations_are_not_registered(operation):
    with pytest.raises(KeyError, match="unknown service operation"):
        execute_service_payload({"operation": operation, "input_data": {}})


def test_native_boundary_adapter_preserves_exactness_and_full_certificate():
    response = execute_service_payload(
        {"operation": "boundary.halfspace.toric2d", "input_data": {}}
    )
    assert response["result"]["exactness"] == "certified_exact"
    assert response["result"]["certificate_level"] == "full"
    assert response["result"]["certificate"] is not None
    assert response["capability"]["maximum_certificate_level"] == "full"
