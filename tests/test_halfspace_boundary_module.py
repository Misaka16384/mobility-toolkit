"""Physics and algebra oracles for the symbolic half-space boundary module."""

import pytest

from mobility_toolkit.boundary_halfspace import (
    HalfSpaceContractionCertificate,
    LaurentHalfSpaceSubmodule,
    OneSidedSubmodule,
    PrimitiveNormal,
    TangentDepthPolynomial,
    TangentDepthTerm,
    boundary_module_capability_report,
    boundary_pairing,
    compile_projected_bulk_primary,
    toric_z2_y_nonnegative_boundary_module,
    verify_toric_z2_y_nonnegative_finite,
)
from mobility_toolkit.core import Exactness


def _poly(normal, terms):
    return TangentDepthPolynomial(
        2,
        normal,
        (),
        tuple(
            TangentDepthTerm(coefficient, tangent, depth, ())
            for coefficient, tangent, depth in terms
        ),
    )


def _toric_modules():
    normal = PrimitiveNormal.from_integer((0, 1))
    zero = _poly(normal, ())
    star = (
        _poly(normal, ((1, (0,), 0), (1, (-1,), 0))),
        _poly(normal, ((1, (0,), 0), (1, (0,), -1))),
        zero,
        zero,
    )
    plaquette = (
        zero,
        zero,
        _poly(normal, ((1, (0,), 0), (1, (0,), 1))),
        _poly(normal, ((1, (0,), 0), (1, (1,), 0))),
    )
    bulk = LaurentHalfSpaceSubmodule(2, normal, 4, (star, plaquette))
    certificate = HalfSpaceContractionCertificate(
        column_depth_shifts=(1, 0),
        cleared_support_nonnegative=True,
        saturation_idempotent=True,
        cleared_module_contained_in_saturation=True,
        localization_equal=True,
        saturation_generator_count=2,
    )
    contracted = OneSidedSubmodule(
        2,
        normal,
        4,
        (tuple(entry.shift_depth(1) for entry in star), plaquette),
        certificate,
    )
    return bulk, contracted


def _support(column):
    return tuple(
        tuple(
            (term.coefficient, term.tangent_exponents, term.depth)
            for term in entry.terms
        )
        for entry in column
    )


def test_operation_specific_capability_is_honest():
    report = boundary_module_capability_report()
    assert report.uniform_prime_primary_subquotient == "certified_exact"
    assert (
        report.supplied_free_pairing_invariants
        == "certified_exact_uniform_prime"
    )
    assert "pairing_radical_kernel" in report.supplied_free_pairing_outputs
    assert "boundary_charge_cokernel" in report.supplied_free_pairing_outputs
    assert report.toric_z2_y_nonnegative_full_module == "certified_exact"
    assert report.generic_full_boundary_module == "unsupported"
    assert report.generic_secondary_closure == "unsupported"
    assert report.generic_boundary_to_bulk_map == "unsupported"


def test_toric_primary_projection_uses_all_and_only_crossing_shifts():
    bulk, contracted = _toric_modules()
    result = compile_projected_bulk_primary(bulk, contracted)
    assert result.exactness == Exactness.CERTIFIED_EXACT
    assert result.value.certificate.source_crossing_shifts == ((0, 0), (1, -1))
    assert result.value.certificate.verified
    supports = {_support(column) for column in result.value.generator_lifts}
    expected_e_x = (
        ((1, (-1,), 0), (1, (0,), 0)),
        ((1, (0,), 0),),
        (),
        (),
    )
    expected_e_z = (
        (),
        (),
        ((1, (0,), 0),),
        (),
    )
    assert supports == {expected_e_x, expected_e_z}
    assert "subquotient" in result.theorem_scope
    assert "secondary" in result.warnings[1].lower()
    assert all(term.depth >= 0 for column in result.value.generator_lifts for entry in column for term in entry.terms)


def test_toric_primary_pairing_is_the_hand_computed_one_plus_x():
    primary = toric_z2_y_nonnegative_boundary_module().value.primary
    e_x_index = next(
        index
        for index, column in enumerate(primary.generator_lifts)
        if column[0].terms
    )
    e_z_index = next(
        index
        for index, column in enumerate(primary.generator_lifts)
        if column[2].terms
    )
    e_x = primary.generator_lifts[e_x_index]
    e_z = primary.generator_lifts[e_z_index]
    omega_xz = boundary_pairing(e_x, e_z)
    omega_zx = boundary_pairing(e_z, e_x)
    assert {(term.exponents, term.coefficient) for term in omega_xz.terms} == {
        ((0,), 1),
        ((1,), 1),
    }
    assert {(term.exponents, term.coefficient) for term in omega_zx.terms} == {
        ((-1,), 1),
        ((0,), 1),
    }
    assert omega_zx == omega_xz.involution()
    assert boundary_pairing(e_x, e_x).is_zero
    assert boundary_pairing(e_z, e_z).is_zero


def test_boundary_pairing_extracts_depth_zero_instead_of_setting_y_to_one():
    normal = PrimitiveNormal.from_integer((0, 1))
    zero = _poly(normal, ())
    x_at_depth_zero = _poly(normal, ((1, (0,), 0),))
    z_at_depth_one = _poly(normal, ((1, (0,), 1),))
    # Evaluation at y=1 would make these anticommute.  The real half-space
    # pairing retains support depth, so different layers have zero physical
    # commutator at the declared tangent displacement.
    assert boundary_pairing(
        (x_at_depth_zero, zero),
        (zero, z_at_depth_one),
    ).is_zero


@pytest.mark.parametrize("period", (2, 3, 4, 5, 6))
def test_finite_periodic_boundary_window_matches_symbolic_toric_module(period):
    check = verify_toric_z2_y_nonnegative_finite(period, strip_depth=3)
    assert check.verified
    assert check.window_dimension == 4 * period
    assert check.constraint_rank == 2 * period
    assert check.local_centralizer_dimension == 2 * period
    assert check.primary_span_dimension == 2 * period
    assert check.induced_pairing_rank == 2 * period - 2
    assert check.radical_dimension == 2


def test_full_toric_module_has_no_secondaries_and_two_boundary_charges():
    result = toric_z2_y_nonnegative_boundary_module()
    boundary = result.value
    assert result.exactness == Exactness.CERTIFIED_EXACT
    assert boundary.certificate.verified
    assert not boundary.has_secondary_operators
    assert boundary.secondary_quotient_invariant_factors == ()
    assert boundary.boundary_charge_invariant_factors == (2, 2)
    assert boundary.boundary_to_bulk_map.is_isomorphism
    assert boundary.boundary_to_bulk_map.target_charge_labels == (
        "electric",
        "magnetic",
    )
    assert result.verification == (
        ("boundary_charge_invariant_factors", (2, 2)),
        ("finite_periods_checked", (2, 3, 4)),
        ("no_secondary_operators", True),
        ("normal_variable_specialized_to_one", False),
    )


def test_generic_primary_compiler_rejects_nonisotropic_bulk_generators():
    normal = PrimitiveNormal.from_integer((0, 1))
    zero = _poly(normal, ())
    one = _poly(normal, ((1, (0,), 0),))
    x_column = (one, zero)
    z_column = (zero, one)
    bulk = LaurentHalfSpaceSubmodule(2, normal, 2, (x_column, z_column))
    certificate = HalfSpaceContractionCertificate(
        column_depth_shifts=(0, 0),
        cleared_support_nonnegative=True,
        saturation_idempotent=True,
        cleared_module_contained_in_saturation=True,
        localization_equal=True,
        saturation_generator_count=2,
    )
    contracted = OneSidedSubmodule(
        2,
        normal,
        2,
        (x_column, z_column),
        certificate,
    )
    with pytest.raises(ValueError, match="not isotropic"):
        compile_projected_bulk_primary(bulk, contracted)
