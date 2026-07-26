"""Finite real-space toric-code cut checks from the cellular presentation.

The parent is a 2x1 open square patch with qudits on edges.  The retained
region is the complete left square, including its interface edges.  Parent
checks crossing from the left square into the discarded right square are
literally restricted to the retained sites and supplied through
``EXPLICIT_SITE_RESTRICTION``.  Thus these tests exercise a spatial cut, not
the former one-cell fixture that simply relabelled removed full-support checks
as boundary projections.

For both Z_2 and Z_4, a primal Z string segment loses exactly its electric
endpoint syndrome at the cut, while a dual X string segment loses exactly its
magnetic endpoint syndrome.  These are finite Bravyi--Kitaev relative-homology
endpoint checks.  Choosing a mutually commuting rough or smooth boundary
Hamiltonian from the cut gauge algebra is a separate condensation step.
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
from mobility_toolkit.core import Exactness, LocalPauliTerm
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


def _left_square_site_ids(parent_complex):
    """Return edges in the closed left square of a 2x1 parent rectangle."""

    return tuple(
        cell.cell_id
        for cell in parent_complex.cells_by_dimension[1]
        if cell.base[0] + (1 if 0 in cell.varying_axes else 0) <= 1
    )


def _compiled_spatial_cut(modulus, backend):
    parent_complex = rectangular_cubical_complex((2, 1))
    cellular = cellular_stabilizer_code(
        parent_complex.chain_complex,
        1,
        modulus,
    )
    retained_site_ids = _left_square_site_ids(parent_complex)
    retained_site_set = set(retained_site_ids)
    source_records = cellular.check_records
    retained_records = tuple(
        record
        for record in source_records
        if {term.site_id for term in record.operator.terms} <= retained_site_set
    )
    cut_records = tuple(
        record
        for record in source_records
        if (
            {term.site_id for term in record.operator.terms} & retained_site_set
            and not {
                term.site_id for term in record.operator.terms
            } <= retained_site_set
        )
    )
    analysis = analyze_finite_stabilizer(
        cellular.code.pauli_module,
        tuple(record.operator for record in retained_records),
        backend,
    )
    window = support_window_from_sites(
        analysis,
        retained_site_ids,
        backend,
        f"z{modulus}-left-square-of-2x1-parent",
    )
    projections = tuple(
        CutStabilizerProjection(
            f"cut:{record.pauli_kind}:{record.cell_id}",
            record.operator,
            record.operator.module.operator(
                tuple(
                    term
                    for term in record.operator.terms
                    if term.site_id in retained_site_set
                ),
                phase=record.operator.phase,
            ),
            ProjectionPolicy.EXPLICIT_SITE_RESTRICTION,
            tuple(
                sorted(
                    term.site_id
                    for term in record.operator.terms
                    if term.site_id not in retained_site_set
                )
            ),
        )
        for record in cut_records
    )
    result = compile_and_analyze_finite_boundary(
        analysis,
        window,
        tuple(record.operator for record in source_records),
        projections,
        backend,
        source_description=(
            f"cellular Z_{modulus} toric code on a 2x1 parent patch, "
            "literally restricted to its closed left square"
        ),
    )
    return (
        parent_complex,
        cellular,
        source_records,
        retained_records,
        cut_records,
        projections,
        result,
    )


@pytest.mark.parametrize("modulus", (2, 4))
def test_real_space_cut_has_complete_literal_primary_image(modulus, backend):
    (
        parent_complex,
        _,
        source,
        retained,
        cut,
        projections,
        result,
    ) = _compiled_spatial_cut(modulus, backend)
    assert parent_complex.chain_complex.cell_counts[-1] == 2
    assert len(source) > len(retained)
    assert cut
    assert all(
        projection.policy is ProjectionPolicy.EXPLICIT_SITE_RESTRICTION
        for projection in projections
    )
    assert all(projection.declared_dropped_site_ids for projection in projections)
    certificate = result.compilation.certificate
    assert certificate.coverage_complete
    assert certificate.exactness is Exactness.BOUNDED_EXACT
    assert all(
        record.restriction_is_identity
        or (
            record.centralizer_membership_verified
            and record.covered_modulo_bulk_trivial
        )
        for record in certificate.coverage_records
    )
    assert result.compilation.image.order(backend) > 1
    for projection in projections:
        vector = result.algebra.analysis.coordinates.vector(
            projection.projected_operator
        )
        assert (
            result.algebra.classify(vector, backend).kind
            is BoundaryOperatorKind.PRIMARY_CANDIDATE
        )


@pytest.mark.parametrize("modulus", (2, 4))
def test_rough_cut_removes_exactly_one_electric_endpoint(modulus, backend):
    (
        parent_complex,
        cellular,
        source,
        retained,
        cut,
        _,
        _,
    ) = _compiled_spatial_cut(modulus, backend)
    horizontal_from_left_to_cut = next(
        cell.cell_id
        for cell in parent_complex.cells_by_dimension[1]
        if cell.varying_axes == (0,) and cell.base == (0, 0)
    )
    electric_segment = cellular.code.pauli_module.operator(
        (LocalPauliTerm.cyclic(horizontal_from_left_to_cut, z=1),)
    )
    parent_syndrome = _commutation_syndrome(
        electric_segment,
        tuple(record for record in source if record.pauli_kind == "x"),
    )
    retained_syndrome = _commutation_syndrome(
        electric_segment,
        tuple(record for record in retained if record.pauli_kind == "x"),
    )
    missing_cut_endpoint = set(parent_syndrome) - set(retained_syndrome)
    assert len(parent_syndrome) == 2
    assert len(retained_syndrome) == 1
    assert len(missing_cut_endpoint) == 1
    assert missing_cut_endpoint <= {
        record.cell_id for record in cut if record.pauli_kind == "x"
    }


@pytest.mark.parametrize("modulus", (2, 4))
def test_smooth_cut_removes_exactly_one_magnetic_endpoint(modulus, backend):
    (
        parent_complex,
        cellular,
        source,
        retained,
        cut,
        _,
        _,
    ) = _compiled_spatial_cut(modulus, backend)
    interface_edge = next(
        cell.cell_id
        for cell in parent_complex.cells_by_dimension[1]
        if cell.varying_axes == (1,) and cell.base == (1, 0)
    )
    magnetic_segment = cellular.code.pauli_module.operator(
        (LocalPauliTerm.cyclic(interface_edge, x=1),)
    )
    parent_syndrome = _commutation_syndrome(
        magnetic_segment,
        tuple(record for record in source if record.pauli_kind == "z"),
    )
    retained_syndrome = _commutation_syndrome(
        magnetic_segment,
        tuple(record for record in retained if record.pauli_kind == "z"),
    )
    missing_cut_endpoint = set(parent_syndrome) - set(retained_syndrome)
    assert len(parent_syndrome) == 2
    assert len(retained_syndrome) == 1
    assert len(missing_cut_endpoint) == 1
    assert missing_cut_endpoint <= {
        record.cell_id for record in cut if record.pauli_kind == "z"
    }


@pytest.mark.skip(
    reason=(
        "fish-toric is presently available only as legacy boundary-gauge golden rows; "
        "there is no canonical phase-aware PeriodicCode/cellular source model with cut "
        "provenance, so translating those rows would make the oracle circular"
    )
)
def test_fish_toric_requires_independent_canonical_source_model():
    pass
