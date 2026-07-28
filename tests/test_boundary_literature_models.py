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
from mobility_toolkit.geometry import (
    CrossingPolicy,
    SupportAliasPolicy,
    compile_periodic_code,
    rectangular_region,
)
from mobility_toolkit.models import (
    FISH_TORIC_SOURCE,
    z2_fish_toric_clifford_equivalence,
    z2_fish_toric_model,
)


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


def _fish_cylindrical_cut(backend):
    """Compile a source-locked fish parent and retain three of five columns."""

    fish = z2_fish_toric_model()
    parent_region = rectangular_region(
        (5, 2),
        fish.code.species,
        periodic_axes=(0, 1),
    )
    parent = compile_periodic_code(
        fish.code,
        parent_region,
        crossing_policy=CrossingPolicy.ERROR_ON_CROSSING,
        support_alias_policy=SupportAliasPolicy.REJECT_SUPPORT_ALIAS,
        backend=backend,
    )
    retained_site_ids = tuple(
        embedding.physical_site_id
        for embedding in parent_region.embeddings
        if embedding.address.coordinate.free[0] in (0, 1, 2)
    )
    retained_site_set = set(retained_site_ids)
    source_records = parent.compiled_generators
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
        parent.pauli_module,
        tuple(record.operator for record in retained_records),
        backend,
    )
    window = support_window_from_sites(
        analysis,
        retained_site_ids,
        backend,
        "fish-z2-three-of-five-periodic-columns",
        search_extent=(("normal_columns", 3), ("tangent_period", 2)),
    )
    projections = tuple(
        CutStabilizerProjection(
            f"fish-cut:{index}",
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
        for index, record in enumerate(cut_records)
    )
    result = compile_and_analyze_finite_boundary(
        analysis,
        window,
        tuple(record.operator for record in source_records),
        projections,
        backend,
        source_description=(
            f"{FISH_TORIC_SOURCE}, Eqs. (12)--(13) and Fig. 4(a); "
            "canonical PeriodicCode compiled on a 5x2 torus and literally "
            "restricted to three consecutive columns"
        ),
    )
    return parent, retained_records, cut_records, result


@pytest.fixture(scope="module")
def fish_cut(backend):
    return _fish_cylindrical_cut(backend)


def test_fish_toric_source_templates_equal_the_recorded_clifford_shear():
    equivalence = z2_fish_toric_clifford_equivalence()
    assert equivalence.verified
    assert equivalence.cnot_gate_offsets == ((0, -2), (1, -2))
    assert equivalence.exactness is Exactness.CERTIFIED_EXACT
    assert (
        equivalence.transformed_standard.stabilizer_templates
        == equivalence.source_fish.code.stabilizer_templates
    )
    assert "finite cuts" in equivalence.theorem_scope


def test_fish_toric_cut_has_exact_primary_coverage_and_secondary_classes(
    backend, fish_cut
):
    parent, retained, cut, result = fish_cut
    assert parent.is_stabilizer_code
    assert parent.compilation_certificate.compiled_instance_count == 20
    assert len(retained) == 4
    assert cut
    certificate = result.compilation.certificate
    assert certificate.coverage_complete
    assert certificate.exactness is Exactness.BOUNDED_EXACT
    assert all(
        record.literal_restriction_verified
        and record.source_phase_membership_verified
        for record in certificate.records
    )
    assert result.algebra.primary_image is not None
    primary_order = result.algebra.primary_image.image_modulo_bulk_trivial.order
    assert result.algebra.invariant_factors == (2,) * 16
    assert result.algebra.radical_invariant_factors == ()
    assert result.algebra.order == 2**16
    assert primary_order == 2**14
    # The full/primary quotient has order four: this finite cut witnesses the
    # two independent secondary classes stated for the smooth fish boundary
    # in Fig. 4(b), without identifying our quotient basis with labels 5/6.
    assert result.algebra.order // primary_order == 4
    secondary_lifts = tuple(
        lift
        for lift in result.algebra.presentation_generator_lifts
        if result.algebra.classify(
            result.algebra.analysis.coordinates.vector(lift), backend
        ).kind
        is BoundaryOperatorKind.SECONDARY_CANDIDATE
    )
    assert secondary_lifts


def test_fish_toric_cut_pairing_and_endpoint_scope_are_finite(
    backend, fish_cut
):
    parent, retained, cut, result = fish_cut
    algebra = result.algebra
    assert algebra.exactness is Exactness.BOUNDED_EXACT
    # The phase-aware qubit convention uses zeta_4; nonzero commutators are
    # represented by 2 mod 4, i.e. the expected toric sign -1.
    assert algebra.paired_algebra.modulus == 4
    assert {
        value
        for _, _, value in algebra.paired_algebra.presentation_pairing_matrix.entries
    } == {2}
    assert algebra.radical_invariant_factors == ()
    assert "finite stabilizer system" in algebra.theorem_scope

    # A source-locked electric string segment has two parent endpoints and
    # exactly one retained endpoint.  This is finite raw-cut syndrome
    # bookkeeping, not a claim that a completed gapped boundary was built.
    horizontal_edge = next(
        embedding.physical_site_id
        for embedding in parent.region.embeddings
        if (
            embedding.address.species_id == "h"
            and embedding.address.coordinate.free == (1, 0)
        )
    )
    electric_segment = parent.pauli_module.operator(
        (LocalPauliTerm.cyclic(horizontal_edge, z=1),)
    )
    parent_x_checks = tuple(
        record
        for record in parent.compiled_generators
        if all(term.x_exponents != (0,) for term in record.operator.terms)
    )
    parent_endpoints = tuple(
        record
        for record in parent_x_checks
        if not electric_segment.commutes_with(record.operator)
    )
    retained_endpoints = tuple(record for record in parent_endpoints if record in retained)
    cut_endpoints = tuple(record for record in parent_endpoints if record in cut)
    assert len(parent_endpoints) == 2
    assert len(retained_endpoints) == 1
    assert len(cut_endpoints) == 1

    # Every projected crossing check is a literal boundary-gauge operator:
    # it commutes with retained bulk, and all removed tensor factors are
    # explicitly recorded.
    projected = result.compilation.projected_operators
    assert projected
    for operator in projected:
        vector = algebra.analysis.coordinates.vector(operator)
        assert algebra.local_centralizer.contains(vector, backend)
    assert all(
        record.dropped_site_ids for record in result.compilation.certificate.records
    )
    assert len(cut) == len(projected)


def test_fish_cut_rejects_a_false_dropped_site_certificate(
    backend, fish_cut
):
    parent, _, _, result = fish_cut
    certified = result.compilation.certificate.records[0]
    false_projection = CutStabilizerProjection(
        "tampered-fish-cut",
        certified.source_operator,
        certified.projected_operator,
        ProjectionPolicy.EXPLICIT_SITE_RESTRICTION,
        (),
    )
    with pytest.raises(ValueError, match="dropped-site declaration is not exact"):
        compile_and_analyze_finite_boundary(
            result.algebra.analysis,
            result.algebra.window,
            tuple(record.operator for record in parent.compiled_generators),
            (false_projection,),
            backend,
            source_description="intentionally tampered fish-cut certificate",
        )
