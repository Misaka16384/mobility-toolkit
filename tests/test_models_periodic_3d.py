import pytest

pytest.importorskip("flint")

from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer
from mobility_toolkit.geometry import (
    CrossingPolicy,
    SupportAliasPolicy,
    compile_periodic_code,
    rectangular_region,
)
from mobility_toolkit.models import (
    z2_haah_cubic_code_a_model,
    z2_xcube_model,
    zd_3d_toric_model,
)
from mobility_toolkit.periodic import QuasiFreePauliModulePresentation


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _periodic_compile(model, lengths, backend):
    region = rectangular_region(
        lengths,
        model.code.species,
        periodic_axes=tuple(range(len(lengths))),
    )
    return compile_periodic_code(
        model.code,
        region,
        crossing_policy=CrossingPolicy.ERROR_ON_CROSSING,
        support_alias_policy=SupportAliasPolicy.NORMAL_FORM_PUSHFORWARD,
        backend=backend,
    )


def test_xcube_literal_rows_match_ruba_yang_eq140():
    model = z2_xcube_model()
    rows = QuasiFreePauliModulePresentation.from_periodic_code(
        model.code
    ).to_legacy_generator_rows()
    assert frozenset(rows) == frozenset((
        (
            "t1*t2 + t1 + t2 + 1",
            "t2*t3 + t2 + t3 + 1",
            "t1*t3 + t1 + t3 + 1",
            "0",
            "0",
            "0",
        ),
        ("0", "0", "0", "1 + x3", "1 + x1", "0"),
        ("0", "0", "0", "0", "1 + x1", "1 + x2"),
    ))
    assert "Eq. (140)" in model.source_equations


def test_xcube_two_by_two_by_two_gsd_matches_known_formula(backend):
    model = z2_xcube_model()
    compiled = _periodic_compile(model, (2, 2, 2), backend)
    assert compiled.validation.valid
    analysis = analyze_finite_stabilizer(
        compiled.pauli_module, compiled.generators, backend
    )
    # X-cube on Lx x Ly x Lz has log_2 GSD = 2(Lx+Ly+Lz)-3.
    assert analysis.codespace_dimension == 2**9
    assert analysis.logical_projective_order == 2**18


@pytest.mark.parametrize("dimension", (2, 4))
def test_3d_toric_periodic_cell_has_three_logical_qudits(
    dimension, backend
):
    model = zd_3d_toric_model(dimension)
    # The composite FGA path for a 2^3 Z4 torus is a scale benchmark rather
    # than a unit-test-sized calculation.  The 1^3 quotient is still an exact
    # independent cellular oracle: all contractible boundary/coboundary checks
    # cancel by support aliasing and H_1(T^3; Z4)=Z4^3.
    lengths = (2, 2, 2) if dimension == 2 else (1, 1, 1)
    compiled = _periodic_compile(model, lengths, backend)
    assert compiled.validation.valid
    analysis = analyze_finite_stabilizer(
        compiled.pauli_module, compiled.generators, backend
    )
    assert analysis.codespace_dimension == dimension**3
    assert analysis.logical_projective_order == dimension**6


def test_haah_code_a_cube_formula_compiles_to_commuting_stabilizers(backend):
    model = z2_haah_cubic_code_a_model()
    compiled = _periodic_compile(model, (2, 2, 2), backend)
    assert compiled.validation.valid
    assert len(model.code.species) == 2
    assert len(model.code.stabilizer_templates) == 2
    assert "1101.1962" in model.source
