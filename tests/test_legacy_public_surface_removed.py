import inspect

import pytest

import mobility_toolkit
from mobility_toolkit import fusion, homology, mobility, translate
from mobility_toolkit.boundary_gauge.boundary import pipeline
from mobility_toolkit.services import ServiceCatalogEntry, build_default_registry


_REMOVED_ROOT_NAMES = (
    "run_m2_script",
    "run_macaulay2",
    "translate_stabilizers",
    "translate_to_algebra",
    "compute_ext_krull",
    "compute_homology_and_mobility",
    "compute_translation_lattice",
    "compute_true_mobility_dimension",
    "analyze_fusion_interference",
    "compute_gsd_and_periodicity",
    "classify_mobility",
    "ModelRegistry",
    "query_vector_db",
)

_REMOVED_OPERATIONS = (
    "homology.ext",
    "mobility.translation_lattice",
    "mobility.classify",
    "periodic.gsd",
    "fusion.interference",
    "fusion.sset",
    "fusion.annihilator",
    "models.search",
    "boundary.gauge.algorithm1",
)


def test_package_root_exposes_only_versioned_service_entry_points():
    assert not any(
        hasattr(mobility_toolkit, name) for name in _REMOVED_ROOT_NAMES
    )
    assert {
        "ServiceExecutor",
        "ServiceExecution",
        "ServiceRequest",
        "default_service_catalog",
        "execute_service_payload",
        "execute_service_request",
        "stream_service_payload",
        "streamable_operations",
    } <= set(mobility_toolkit.__all__)


def test_removed_service_operations_and_legacy_adapter_kind_cannot_return():
    operations = set(build_default_registry().operations)
    assert not (set(_REMOVED_OPERATIONS) & operations)
    with pytest.raises(ValueError, match="adapter_kind must be native"):
        ServiceCatalogEntry(
            operation="removed.example",
            summary="removed compatibility adapter",
            input_schema={},
            adapter_kind="legacy_dict_adapter",
        )


def test_dimension_specific_algorithm1_tuple_wrappers_are_fixture_private():
    assert pipeline.__all__ == []
    assert not hasattr(pipeline, "run_algorithm_1_boundary_ops_2d")
    assert not hasattr(pipeline, "run_algorithm_1_boundary_ops_3d")
    assert callable(pipeline._run_algorithm_1_boundary_ops_2d)
    assert callable(pipeline._run_algorithm_1_boundary_ops_3d)


def test_runtime_algorithms_have_no_prime_bypass_or_deleted_aliases():
    for function in (
        translate.translate_stabilizers,
        homology.compute_ext_krull,
        fusion.solve_sset_fusion,
        fusion.analyze_annihilator_fusion,
    ):
        assert "prime_bypass" not in inspect.signature(function).parameters
    assert not hasattr(translate, "translate_to_algebra")
    assert not hasattr(homology, "compute_homology_and_mobility")
    assert not hasattr(mobility, "compute_true_mobility_dimension")
