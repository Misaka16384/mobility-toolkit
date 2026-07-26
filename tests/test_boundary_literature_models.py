"""Finite toric-boundary checks independent of legacy golden matrices.

Bravyi--Kitaev's relative-homology surface-code picture identifies rough
boundaries by removal of boundary star constraints, so electric Z strings may
end there, and smooth boundaries by removal of boundary plaquette constraints,
so magnetic X strings may end there.  These tests build the cellular Z_d toric
code directly and verify those syndrome/condensation statements for d=2,4.
They are exact finite-patch checks, not thermodynamic boundary-classification
claims.
"""

import pytest

pytest.importorskip("flint")

from mobility_toolkit.boundary import (
    BoundaryOperatorKind,
    CutStabilizerProjection,
    ProjectionPolicy,
    compile_and_analyze_finite_boundary,
    support_window_from_sites,
)
from mobility_toolkit.core import LocalPauliTerm
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer
from mobility_toolkit.geometry import cellular_stabilizer_code, rectangular_cubical_complex


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _commutation_syndrome(operator, checks):
    return tuple(
        record.cell_id
        for record in checks
        if not operator.commutes_with(record.operator)
    )


def _compiled_boundary(modulus, removed_kind, backend):
    disk = rectangular_cubical_complex((1, 1))
    cellular = cellular_stabilizer_code(disk.chain_complex, 1, modulus)
    source_records = cellular.check_records
    removed = tuple(record for record in source_records if record.pauli_kind == removed_kind)
    retained = tuple(record for record in source_records if record.pauli_kind != removed_kind)
    source_generators = tuple(record.operator for record in source_records)
    retained_analysis = analyze_finite_stabilizer(
        cellular.code.pauli_module,
        tuple(record.operator for record in retained),
        backend,
    )
    window_sites = tuple(
        sorted(
            {
                term.site_id
                for record in removed
                for term in record.operator.terms
            }
        )
    )
    window = support_window_from_sites(
        retained_analysis,
        window_sites,
        backend,
        f"z{modulus}-{removed_kind}-boundary",
    )
    projections = tuple(
        CutStabilizerProjection(
            f"cut:{record.pauli_kind}:{record.cell_id}",
            record.operator,
            record.operator,
            ProjectionPolicy.REQUIRE_FULL_SUPPORT,
        )
        for record in removed
    )
    result = compile_and_analyze_finite_boundary(
        retained_analysis,
        window,
        source_generators,
        projections,
        backend,
        source_description=(
            f"cellular Z_{modulus} toric-code cut {removed_kind}-check image; "
            "finite Bravyi--Kitaev relative-homology fixture"
        ),
    )
    return cellular, source_records, retained, removed, result


@pytest.mark.parametrize("modulus", (2, 4))
def test_rough_boundary_condenses_electric_string_endpoints(modulus, backend):
    cellular, source, retained, removed, result = _compiled_boundary(
        modulus, "x", backend
    )
    # A boundary-edge Z is an electric string segment.  All vertex/star checks
    # are cut in this minimal disk, hence it has no retained syndrome, while the
    # uncut parent code detects its two electric endpoints.
    site_id = cellular.code.pauli_module.local_systems[0].site_id
    electric = cellular.code.pauli_module.operator(
        (LocalPauliTerm.cyclic(site_id, z=1),)
    )
    assert _commutation_syndrome(electric, retained) == ()
    assert len(_commutation_syndrome(electric, source)) == 2
    assert result.algebra.analysis.codespace_dimension == modulus**3
    assert result.compilation.image.order(backend) == modulus**3
    assert result.algebra.primary_image.image_modulo_bulk_trivial.invariant_factors == (
        modulus,
        modulus,
        modulus,
    )
    primary_vector = result.algebra.analysis.coordinates.vector(removed[0].operator)
    assert result.algebra.classify(primary_vector, backend).kind is BoundaryOperatorKind.PRIMARY_CANDIDATE
    electric_vector = result.algebra.analysis.coordinates.vector(electric)
    assert result.algebra.classify(electric_vector, backend).kind is BoundaryOperatorKind.SECONDARY_CANDIDATE


@pytest.mark.parametrize("modulus", (2, 4))
def test_smooth_boundary_condenses_magnetic_string_endpoints(modulus, backend):
    cellular, source, retained, removed, result = _compiled_boundary(
        modulus, "z", backend
    )
    # A boundary-edge X is a magnetic dual-string segment.  Removing the single
    # plaquette/flux check lets it terminate; the parent code detects it.
    site_id = cellular.code.pauli_module.local_systems[0].site_id
    magnetic = cellular.code.pauli_module.operator(
        (LocalPauliTerm.cyclic(site_id, x=1),)
    )
    assert _commutation_syndrome(magnetic, retained) == ()
    assert len(_commutation_syndrome(magnetic, source)) == 1
    assert result.algebra.analysis.codespace_dimension == modulus
    assert result.compilation.image.order(backend) == modulus
    assert result.algebra.primary_image.image_modulo_bulk_trivial.invariant_factors == (
        modulus,
    )
    primary_vector = result.algebra.analysis.coordinates.vector(removed[0].operator)
    assert result.algebra.classify(primary_vector, backend).kind is BoundaryOperatorKind.PRIMARY_CANDIDATE
    magnetic_vector = result.algebra.analysis.coordinates.vector(magnetic)
    assert result.algebra.classify(magnetic_vector, backend).kind is BoundaryOperatorKind.SECONDARY_CANDIDATE


@pytest.mark.skip(
    reason=(
        "fish-toric is presently available only as legacy boundary-gauge golden rows; "
        "there is no canonical phase-aware PeriodicCode/cellular source model with cut "
        "provenance, so translating those rows would make the oracle circular"
    )
)
def test_fish_toric_requires_independent_canonical_source_model():
    pass
