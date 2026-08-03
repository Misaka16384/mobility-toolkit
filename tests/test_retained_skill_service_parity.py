import importlib.util
from pathlib import Path

import pytest

from mobility_toolkit.services import (
    build_default_registry,
    default_service_catalog,
    execute_service_payload,
)


ROOT = Path(__file__).resolve().parents[1]


def _load_skill_script(skill):
    path = (
        ROOT
        / "mobility_toolkit"
        / "skills"
        / skill
        / "scripts"
        / f"{skill}.py"
    )
    spec = importlib.util.spec_from_file_location(
        "retained_skill_" + skill.replace("-", "_"), path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _without_cache(response):
    result = dict(response)
    result.pop("cache", None)
    return result


@pytest.mark.parametrize(
    "skill,operation",
    (
        ("mt-halfspace", "boundary.halfspace.capabilities"),
        ("mt-gapped-boundary-2d", "boundary.completion2d.capabilities"),
        ("mt-gapped-boundary-3d", "boundary.symbolic3d.capabilities"),
        ("mt-cheshire", "defects.cheshire.capabilities"),
    ),
)
def test_retained_skill_scripts_are_thin_service_shims(skill, operation):
    request = {
        "schema": "mobility_toolkit.service_request.v1",
        "schema_version": "1",
        "operation": operation,
        "input_data": {},
        "requested_certificate_level": "standard",
    }
    expected = execute_service_payload(request)
    actual = _load_skill_script(skill).run(request)
    assert _without_cache(actual) == _without_cache(expected)
    assert actual["schema"] == "mobility_toolkit.service_execution.v1"


def test_retained_operations_are_all_registered_without_losing_finite_services():
    operations = set(build_default_registry().operations)
    retained = {
        "boundary.halfspace.capabilities",
        "boundary.halfspace.geometry",
        "boundary.halfspace.compare_orientations",
        "boundary.halfspace.contract",
        "boundary.halfspace.primary",
        "boundary.halfspace.free_pairing",
        "boundary.halfspace.toric2d",
        "boundary.halfspace.toric3d_primary",
        "boundary.halfspace.secondary_example",
        "boundary.halfspace.xcube_orientation",
        "boundary.completion2d.capabilities",
        "boundary.completion2d.metric",
        "boundary.completion2d.enumerate",
        "boundary.completion2d.fold",
        "boundary.completion2d.toric_cut",
        "boundary.completion2d.verify",
        "boundary.symbolic3d.capabilities",
        "boundary.symbolic3d.enumerate",
        "boundary.symbolic3d.toric_primary_preflight",
        "boundary.symbolic3d.xcube_preflight",
        "defects.cheshire.capabilities",
        "defects.cheshire.classify_abelian",
        "defects.cheshire.toric2d_reference",
        "defects.cheshire.fuse",
        "defects.cheshire.realize_toric2d",
        "defects.cheshire.circuit_toric2d",
        "defects.cheshire.toric3d_finite_reference",
        "defects.cheshire.xcube_candidates",
    }
    assert retained <= operations
    assert {
        "defects.cheshire.static_toric",
        "defects.cheshire.synthesize_toric",
        "defects.cheshire.enumerate_toric",
        "defects.cheshire.fuse_toric_static",
        "defects.cheshire.xcube_axial_reference",
    }.isdisjoint(operations)
    assert {
        "finite.code.analyze",
        "boundary.finite.analyze",
        "boundary.finite.enumerate_e1",
        "boundary.finite.e2.reference_z2_swap",
    } <= operations

    catalog = default_service_catalog()
    by_name = {
        item["operation"]["operation"]: item for item in catalog["operations"]
    }
    assert by_name["boundary.halfspace.contract"]["capability"]["constraints"] == [
        ["requires_macaulay2", True],
        ["uniform_prime_coefficient_field", True],
    ]
    assert by_name["boundary.completion2d.verify"]["capability"]["constraints"] == [
        ["requires_python_flint", True]
    ]
    assert (
        by_name["boundary.symbolic3d.enumerate"]["capability"][
            "maximum_exactness"
        ]
        == "bounded_exact"
    )


def test_small_halfspace_and_symbolic3d_operations_use_canonical_envelopes():
    geometry = execute_service_payload(
        {
            "operation": "boundary.halfspace.geometry",
            "input_data": {"normal": [1, 1, 0], "boundary_offset": 0},
            "requested_certificate_level": "standard",
        }
    )
    assert geometry["result"]["exactness"] == "certified_exact"
    assert geometry["result"]["value"]["half_space"]["normal"]["components"] == [
        1,
        1,
        0,
    ]

    symbolic = execute_service_payload(
        {
            "operation": "boundary.symbolic3d.enumerate",
            "input_data": {
                "full_boundary_module_supplied": True,
                "coefficient_modulus": 3,
                "normal": [0, 0, 1],
                "pairing_matrix": [
                    [[], [{"coefficient": 1, "exponents": [0, 0]}]],
                    [[{"coefficient": 2, "exponents": [0, 0]}], []],
                ],
                "exponent_bounds": [[0, 0], [0, 0]],
                "max_generators": 1,
                "include_zero_submodule": False,
                "budget": {
                    "max_seed_presentations": 1000,
                    "max_output_candidates": 1000,
                },
                "max_pages": 10,
            },
            "requested_certificate_level": "full",
        }
    )
    assert symbolic["result"]["exactness"] == "bounded_exact"
    assert len(symbolic["result"]["value"]["candidates"]) == 4
    assert dict(symbolic["result"]["verification"])["bounded_domain_complete"]


def test_small_metric_and_cheshire_static_service_smokes():
    pytest.importorskip("flint")
    fingerprint = {
        "backend": "python-flint",
        "version": "",
        "algorithm_family": "finite-integer",
    }
    metric = execute_service_payload(
        {
            "operation": "boundary.completion2d.metric",
            "input_data": {"model": "z2-toric"},
            "requested_certificate_level": "full",
            "backend_fingerprint": fingerprint,
        }
    )
    assert metric["result"]["exactness"] == "certified_exact"
    assert metric["result"]["value"]["group_order"] == 4

    cheshire = execute_service_payload(
        {
            "operation": "defects.cheshire.toric3d_finite_reference",
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
            "backend_fingerprint": fingerprint,
        }
    )
    assert cheshire["result"]["exactness"] == "certified_exact"
    assert len(cheshire["result"]["value"]["defect_reports"]) == 1


def test_completion2d_checkpoint_resumes_and_rejects_tampering():
    pytest.importorskip("flint")
    fingerprint = {
        "backend": "python-flint",
        "version": "",
        "algorithm_family": "finite-integer",
    }
    first_input = {
        "model": "z2-toric",
        "max_pages": 1,
        "budget": {
            "max_work_units": 1,
            "max_results": 100,
            "max_elements": 100,
            "max_subgroups": 100,
        },
    }
    first = execute_service_payload(
        {
            "operation": "boundary.completion2d.enumerate",
            "input_data": first_input,
            "requested_certificate_level": "full",
            "backend_fingerprint": fingerprint,
        }
    )
    checkpoint = first["result"]["value"]["next_checkpoint"]
    assert first["result"]["exactness"] == "experimental"
    assert checkpoint is not None

    resumed_input = dict(first_input)
    resumed_input["max_pages"] = 100
    resumed_input["budget"] = {
        "max_work_units": 10000,
        "max_results": 100,
        "max_elements": 100,
        "max_subgroups": 100,
    }
    resumed_input["checkpoint"] = checkpoint
    resumed = execute_service_payload(
        {
            "operation": "boundary.completion2d.enumerate",
            "input_data": resumed_input,
            "requested_certificate_level": "full",
            "backend_fingerprint": fingerprint,
        }
    )
    assert resumed["result"]["exactness"] == "certified_exact"
    assert resumed["result"]["value"]["next_checkpoint"] is None

    tampered = dict(checkpoint)
    tampered["metric_hash"] = "0" * 64
    bad_input = dict(resumed_input)
    bad_input["checkpoint"] = tampered
    with pytest.raises(ValueError, match="different metric group"):
        execute_service_payload(
            {
                "operation": "boundary.completion2d.enumerate",
                "input_data": bad_input,
                "backend_fingerprint": fingerprint,
            }
        )


def test_symbolic3d_checkpoint_resumes_and_rejects_tampering():
    base = {
        "full_boundary_module_supplied": True,
        "coefficient_modulus": 3,
        "normal": [0, 0, 1],
        "pairing_matrix": [
            [[], [{"coefficient": 1, "exponents": [0, 0]}]],
            [[{"coefficient": 2, "exponents": [0, 0]}], []],
        ],
        "exponent_bounds": [[0, 0], [0, 0]],
        "max_generators": 1,
        "include_zero_submodule": False,
        "budget": {
            "max_seed_presentations": 1,
            "max_output_candidates": 1000,
        },
        "max_pages": 1,
    }
    first = execute_service_payload(
        {
            "operation": "boundary.symbolic3d.enumerate",
            "input_data": base,
            "requested_certificate_level": "full",
        }
    )
    checkpoint = first["result"]["value"]["next_checkpoint"]
    assert first["result"]["exactness"] == "experimental"
    assert checkpoint is not None

    resumed_input = dict(base)
    resumed_input["budget"] = {
        "max_seed_presentations": 1000,
        "max_output_candidates": 1000,
    }
    resumed_input["max_pages"] = 10
    resumed_input["checkpoint"] = checkpoint
    resumed = execute_service_payload(
        {
            "operation": "boundary.symbolic3d.enumerate",
            "input_data": resumed_input,
            "requested_certificate_level": "full",
        }
    )
    assert resumed["result"]["exactness"] == "bounded_exact"
    assert resumed["result"]["value"]["next_checkpoint"] is None

    tampered = dict(checkpoint)
    tampered["checkpoint_hash"] = "0" * 64
    bad_input = dict(resumed_input)
    bad_input["checkpoint"] = tampered
    with pytest.raises(ValueError, match="structural verification"):
        execute_service_payload(
            {
                "operation": "boundary.symbolic3d.enumerate",
                "input_data": bad_input,
            }
        )
