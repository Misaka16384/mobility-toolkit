import pytest

pytest.importorskip("flint")

from mobility_toolkit.boundary import (
    BoundaryOperatorKind,
    SupportWindow,
    TangentTranslationSpec,
    analyze_finite_boundary_algebra,
    scan_finite_window_stability,
    support_window_from_sites,
)
from mobility_toolkit.core import Exactness, LocalPauliTerm, PauliModule, SparseIntMatrix
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _single_qubit_algebra(backend, primary=None, source=""):
    module = PauliModule.from_dimensions((2,), ("q",))
    analysis = analyze_finite_stabilizer(module, (), backend)
    window = support_window_from_sites(analysis, ("q",), backend, "w1")
    return analyze_finite_boundary_algebra(
        analysis,
        window,
        backend,
        projected_primary_image=primary,
        primary_source_description=source,
    )


def test_exact_support_window_algebra_and_radical_are_separate(backend):
    algebra = _single_qubit_algebra(backend)
    assert algebra.exactness is Exactness.BOUNDED_EXACT
    assert algebra.invariant_factors == (2, 2)
    assert algebra.radical_invariant_factors == ()
    assert algebra.order == 4
    assert len(algebra.presentation_generator_lifts) == 2

    x = algebra.analysis.coordinates.vector(
        algebra.analysis.module.operator((LocalPauliTerm.cyclic("q", x=1),))
    )
    classified = algebra.classify(x, backend)
    assert classified.kind is BoundaryOperatorKind.UNCLASSIFIED_NONTRIVIAL
    assert "primary/secondary is undefined" in classified.criterion


def test_arbitrary_projective_support_subgroup_is_a_valid_window(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    analysis = analyze_finite_stabilizer(module, (), backend)
    x_only = analysis.ambient_projective_paulis.subgroup(
        SparseIntMatrix(2, 1, ((0, 0, 1),)), backend
    )
    algebra = analyze_finite_boundary_algebra(
        analysis, SupportWindow("x-only", x_only), backend
    )
    assert algebra.invariant_factors == (2,)
    assert algebra.radical_invariant_factors == (2,)


def test_primary_secondary_requires_explicit_projected_image(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    analysis = analyze_finite_stabilizer(module, (), backend)
    x_vector = analysis.coordinates.vector(
        module.operator((LocalPauliTerm.cyclic("q", x=1),))
    )
    x_image = analysis.ambient_projective_paulis.subgroup(
        SparseIntMatrix(2, 1, ((0, 0, 1),)), backend
    )
    window = support_window_from_sites(analysis, ("q",), backend)
    algebra = analyze_finite_boundary_algebra(
        analysis,
        window,
        backend,
        projected_primary_image=x_image,
        primary_source_description="explicit projected cut-stabilizer test image",
    )
    z_vector = analysis.coordinates.vector(
        module.operator((LocalPauliTerm.cyclic("q", z=1),))
    )
    assert algebra.classify(x_vector, backend).kind is BoundaryOperatorKind.PRIMARY_CANDIDATE
    assert algebra.classify(z_vector, backend).kind is BoundaryOperatorKind.SECONDARY_CANDIDATE
    # Secondary is intentionally not exposed as a subgroup; radical remains independent.
    assert algebra.radical_invariant_factors == ()


def test_bulk_trivial_classification_precedes_primary_data(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    z = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    analysis = analyze_finite_stabilizer(module, (z,), backend)
    window = support_window_from_sites(analysis, ("q",), backend)
    algebra = analyze_finite_boundary_algebra(analysis, window, backend)
    assert algebra.classify(analysis.coordinates.vector(z), backend).kind is BoundaryOperatorKind.BULK_TRIVIAL
    assert algebra.invariant_factors == ()


def test_explicit_tangent_action_is_retained_without_translation_pruning(backend):
    module = PauliModule.from_dimensions((2, 2), ("a", "b"))
    analysis = analyze_finite_stabilizer(module, (), backend)
    window = support_window_from_sites(analysis, ("a", "b"), backend, "full")
    swap = SparseIntMatrix.from_rows(
        (
            (0, 0, 1, 0),
            (0, 0, 0, 1),
            (1, 0, 0, 0),
            (0, 1, 0, 0),
        )
    )
    algebra = analyze_finite_boundary_algebra(
        analysis,
        window,
        backend,
        tangent_translations=(TangentTranslationSpec("tangent-step", swap),),
    )
    assert algebra.invariant_factors == (2, 2, 2, 2)
    assert algebra.order == 16
    action = algebra.tangent_translations[0]
    assert action.name == "tangent-step"
    assert action.quotient_action.verify_first_isomorphism_order(backend)


def test_window_stability_is_never_promoted_to_thermodynamic_exactness(backend):
    algebra = _single_qubit_algebra(backend)
    scan = scan_finite_window_stability((algebra, algebra, algebra))
    assert scan.stabilized
    assert scan.stable_tail_length == 3
    assert scan.exactness is Exactness.STABILIZED_EMPIRICALLY
    assert "thermodynamic" in scan.theorem_scope


def test_rejects_primary_image_outside_local_centralizer(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    z = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    analysis = analyze_finite_stabilizer(module, (z,), backend)
    x_image = analysis.ambient_projective_paulis.subgroup(
        SparseIntMatrix(2, 1, ((0, 0, 1),)), backend
    )
    window = support_window_from_sites(analysis, ("q",), backend)
    with pytest.raises(ValueError, match="not contained in C_W"):
        analyze_finite_boundary_algebra(
            analysis,
            window,
            backend,
            projected_primary_image=x_image,
            primary_source_description="invalid test image",
        )
