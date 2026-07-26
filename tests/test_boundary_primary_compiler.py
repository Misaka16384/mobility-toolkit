import pytest

pytest.importorskip("flint")

from mobility_toolkit.boundary import (
    BoundaryOperatorKind,
    CutStabilizerProjection,
    ProjectionPolicy,
    compile_and_analyze_finite_boundary,
    compile_projected_primary_image,
    support_window_from_sites,
)
from mobility_toolkit.core import Exactness, LocalPauliTerm, PauliModule
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _two_qubit_cut_fixture(backend):
    module = PauliModule.from_dimensions((2, 2), ("a", "b"))
    source = module.operator(
        (
            LocalPauliTerm.cyclic("a", x=1),
            LocalPauliTerm.cyclic("b", x=1),
        )
    )
    retained = analyze_finite_stabilizer(module, (), backend)
    window = support_window_from_sites(retained, ("a",), backend, "left-cut")
    projected = module.operator((LocalPauliTerm.cyclic("a", x=1),))
    return module, source, retained, window, projected


def test_explicit_site_restriction_compiles_primary_image_exactly(backend):
    _, source, retained, window, projected = _two_qubit_cut_fixture(backend)
    spec = CutStabilizerProjection(
        "cut-xx",
        source,
        projected,
        ProjectionPolicy.EXPLICIT_SITE_RESTRICTION,
        ("b",),
    )
    result = compile_and_analyze_finite_boundary(
        retained,
        window,
        (source,),
        (spec,),
        backend,
        source_description="explicit Bell-pair cut projection",
    )
    assert result.compilation.certificate.exactness is Exactness.BOUNDED_EXACT
    assert result.compilation.image.order(backend) == 2
    assert result.compilation.certificate.records[0].dropped_site_ids == ("b",)
    vector = retained.coordinates.vector(projected)
    assert result.algebra.classify(vector, backend).kind is BoundaryOperatorKind.PRIMARY_CANDIDATE


def test_ambiguous_or_inexact_dropped_support_is_rejected(backend):
    _, source, retained, window, projected = _two_qubit_cut_fixture(backend)
    full_support = CutStabilizerProjection(
        "ambiguous-full",
        source,
        projected,
        ProjectionPolicy.REQUIRE_FULL_SUPPORT,
    )
    with pytest.raises(ValueError, match="drops support"):
        compile_projected_primary_image(
            retained,
            window,
            (source,),
            (full_support,),
            backend,
            source_description="invalid full-support projection",
        )

    wrong_declaration = CutStabilizerProjection(
        "wrong-drop",
        source,
        projected,
        ProjectionPolicy.EXPLICIT_SITE_RESTRICTION,
        (),
    )
    with pytest.raises(ValueError, match="declaration is not exact"):
        compile_projected_primary_image(
            retained,
            window,
            (source,),
            (wrong_declaration,),
            backend,
            source_description="invalid drop declaration",
        )


def test_projection_is_phase_aware_for_source_and_target(backend):
    _, source, retained, window, projected = _two_qubit_cut_fixture(backend)
    wrong_source = source.with_phase(2)
    wrong_source_projection = CutStabilizerProjection(
        "wrong-source-phase",
        wrong_source,
        projected.with_phase(2),
        ProjectionPolicy.EXPLICIT_SITE_RESTRICTION,
        ("b",),
    )
    with pytest.raises(ValueError, match="wrong stabilizer phase"):
        compile_projected_primary_image(
            retained,
            window,
            (source,),
            (wrong_source_projection,),
            backend,
            source_description="wrong phase source",
        )

    wrong_target = CutStabilizerProjection(
        "wrong-target-phase",
        source,
        projected.with_phase(2),
        ProjectionPolicy.EXPLICIT_SITE_RESTRICTION,
        ("b",),
    )
    with pytest.raises(ValueError, match="literal phase-aware restriction"):
        compile_projected_primary_image(
            retained,
            window,
            (source,),
            (wrong_target,),
            backend,
            source_description="wrong phase target",
        )


def test_projected_operator_must_commute_with_retained_bulk(backend):
    module = PauliModule.from_dimensions((2, 2), ("a", "b"))
    source = module.operator(
        (
            LocalPauliTerm.cyclic("a", x=1),
            LocalPauliTerm.cyclic("b", x=1),
        )
    )
    retained_z = module.operator((LocalPauliTerm.cyclic("a", z=1),))
    retained = analyze_finite_stabilizer(module, (retained_z,), backend)
    window = support_window_from_sites(retained, ("a",), backend)
    projected = module.operator((LocalPauliTerm.cyclic("a", x=1),))
    spec = CutStabilizerProjection(
        "noncentral-projection",
        source,
        projected,
        ProjectionPolicy.EXPLICIT_SITE_RESTRICTION,
        ("b",),
    )
    with pytest.raises(ValueError, match="does not commute with retained bulk"):
        compile_projected_primary_image(
            retained,
            window,
            (source,),
            (spec,),
            backend,
            source_description="noncentral test projection",
        )
