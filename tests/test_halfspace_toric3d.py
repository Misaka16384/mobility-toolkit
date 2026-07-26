"""Source, symbolic-primary, and finite-slab checks for 3D toric code."""

import pytest

from mobility_toolkit.boundary_halfspace import (
    FROZEN_Z2_3D_TORIC_ROWS,
    contract_laurent_submodule,
    toric3d_halfspace_capability_report,
    toric3d_z2_z_nonnegative_primary_benchmark,
    verify_toric3d_z_nonnegative_finite,
)
from mobility_toolkit.boundary_halfspace.toric3d import _toric3d_input_modules
from mobility_toolkit.core import Exactness
from mobility_toolkit.engine import describe_m2_backend
from mobility_toolkit.models import zd_3d_toric_model
from mobility_toolkit.periodic import QuasiFreePauliModulePresentation


M2_AVAILABLE = bool(describe_m2_backend()["available"])


def _support(column):
    return tuple(
        tuple(
            (term.coefficient, term.tangent_exponents, term.depth)
            for term in entry.terms
        )
        for entry in column
    )


def _terms(polynomial):
    return {
        (term.exponents, term.coefficient) for term in polynomial.terms
    }


def test_source_frozen_rows_match_canonical_periodic_3d_toric_model():
    rows = tuple(sorted(
        QuasiFreePauliModulePresentation.from_periodic_code(
            zd_3d_toric_model(2).code
        ).to_legacy_generator_rows()
    ))
    assert rows == tuple(sorted(FROZEN_Z2_3D_TORIC_ROWS))


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_analytic_one_sided_contraction_matches_live_normal_saturation():
    bulk, analytic = _toric3d_input_modules()
    saturated = contract_laurent_submodule(bulk, timeout_seconds=60).value
    assert saturated.certificate.verified
    assert saturated.certificate.column_depth_shifts == (1, 0, 0, 0)
    assert saturated.certificate.saturation_generator_count == 4
    assert saturated.generator_columns == analytic.generator_columns


def test_operation_specific_capability_does_not_claim_full_boundary_module():
    report = toric3d_halfspace_capability_report()
    assert report.source_frozen_bulk_presentation == "certified_exact"
    assert report.projected_bulk_primary_subquotient == "certified_exact"
    assert report.finite_periodic_slab_alignment == "bounded_exact"
    assert report.generic_full_boundary_module == "unsupported"
    assert report.secondary_closure == "unsupported"
    assert report.generic_boundary_charge_module == "unsupported"
    assert "isotropic sectors only" in report.local_electric_magnetic_completions


def test_symbolic_primary_has_three_expected_crossing_generators():
    result = toric3d_z2_z_nonnegative_primary_benchmark()
    benchmark = result.value
    assert result.exactness == Exactness.CERTIFIED_EXACT
    assert benchmark.certificate.verified
    assert set(benchmark.generator_labels) == {"e_X", "e_Zx", "e_Zy"}
    assert benchmark.primary.certificate.source_crossing_shifts == (
        (0, 0),
        (2, -1),
        (3, -1),
    )
    supports = {
        label: _support(column)
        for label, column in zip(
            benchmark.generator_labels,
            benchmark.primary.generator_lifts,
        )
    }
    assert supports["e_X"] == (
        ((1, (-1, 0), 0), (1, (0, 0), 0)),
        ((1, (0, -1), 0), (1, (0, 0), 0)),
        ((1, (0, 0), 0),),
        (),
        (),
        (),
    )
    assert supports["e_Zx"] == (
        (),
        (),
        (),
        ((1, (0, 0), 0),),
        (),
        (),
    )
    assert supports["e_Zy"] == (
        (),
        (),
        (),
        (),
        ((1, (0, 0), 0),),
        (),
    )


def test_symbolic_pairing_and_depth_zero_denominator_are_literal():
    benchmark = toric3d_z2_z_nonnegative_primary_benchmark().value
    index = {
        label: position
        for position, label in enumerate(benchmark.generator_labels)
    }
    pairing = benchmark.quasi_symplectic_pairing
    x_index = index["e_X"]
    zx_index = index["e_Zx"]
    zy_index = index["e_Zy"]
    assert _terms(pairing[x_index][zx_index]) == {
        ((0, 0), 1),
        ((1, 0), 1),
    }
    assert _terms(pairing[x_index][zy_index]) == {
        ((0, 0), 1),
        ((0, 1), 1),
    }
    assert pairing[zx_index][x_index] == pairing[x_index][zx_index].involution()
    assert pairing[zy_index][x_index] == pairing[x_index][zy_index].involution()
    assert pairing[x_index][x_index].is_zero
    assert pairing[zx_index][zy_index].is_zero
    one_plus_y, one_plus_x = benchmark.depth_zero_denominator_relation
    assert _terms(one_plus_y) == {((0, 0), 1), ((0, 1), 1)}
    assert _terms(one_plus_x) == {((0, 0), 1), ((1, 0), 1)}


@pytest.mark.parametrize(
    "period_x,period_y,depth",
    ((2, 2, 1), (2, 3, 2), (3, 2, 3), (3, 3, 2), (4, 3, 4)),
)
def test_finite_periodic_slab_aligns_with_symbolic_primary(
    period_x,
    period_y,
    depth,
):
    check = verify_toric3d_z_nonnegative_finite(
        period_x,
        period_y,
        slab_depth=depth,
    )
    sites = period_x * period_y
    assert check.verified
    assert check.boundary_layer_dimension == 6 * sites
    assert check.constraint_count == 4 * sites
    assert check.constraint_rank == 3 * sites
    assert check.local_centralizer_dimension == 3 * sites
    assert check.primary_span_dimension == 3 * sites
    assert check.induced_pairing_rank == 2 * sites - 2
    assert check.radical_dimension == sites + 2
    assert check.denominator_boundary_span_dimension == sites - 1
    assert check.reduced_radical_dimension == 3


def test_electric_and_magnetic_content_is_only_an_isotropic_sector_claim():
    result = toric3d_z2_z_nonnegative_primary_benchmark()
    sectors = {sector.label: sector for sector in result.value.condensation_sectors}
    electric = sectors["electric-compatible Z sector"]
    magnetic = sectors["magnetic-compatible X sector"]
    assert electric.generator_labels == ("e_Zx", "e_Zy")
    assert "electric point charge" in electric.compatible_bulk_content
    assert electric.isotropic_verified
    assert not electric.local_hamiltonian_completion_computed
    assert magnetic.generator_labels == ("e_X",)
    assert "magnetic flux-loop" in magnetic.compatible_bulk_content
    assert magnetic.isotropic_verified
    assert not magnetic.local_hamiltonian_completion_computed
    assert not result.value.full_boundary_module_computed
    assert not result.value.secondary_closure_computed
    assert not result.value.local_boundary_completions_computed
    assert "not automatically synthesized" in result.theorem_scope
    assert "finite slab" in result.warnings[1].lower()


def test_normal_variable_is_not_evaluated_at_one():
    result = toric3d_z2_z_nonnegative_primary_benchmark()
    assert ("normal_variable_specialized_to_one", False) in result.verification
    assert any(
        "full P_boundary" in warning for warning in result.warnings
    )


@pytest.mark.parametrize(
    "arguments,message",
    (
        ((1, 2, 1), "at least two"),
        ((2, 1, 1), "at least two"),
        ((2, 2, 0), "at least one"),
    ),
)
def test_finite_slab_rejects_degenerate_search_windows(arguments, message):
    with pytest.raises(ValueError, match=message):
        verify_toric3d_z_nonnegative_finite(*arguments)
