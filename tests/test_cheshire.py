import pytest

from mobility_toolkit.core import LocalPauliTerm, canonical_json
from mobility_toolkit.defects import (
    ClosedLoop,
    LineDefect,
    OpenSegment,
    TubularDefect,
    analyze_toric_cheshire,
    cheshire_scaling_sample,
)
from mobility_toolkit.finite import FlintIntegerBackend
from mobility_toolkit.geometry import (
    CellularPauliConvention,
    cellular_stabilizer_code,
    rectangular_cubical_complex,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _gf2_rank(bit_rows):
    rows = list(bit_rows)
    rank = 0
    width = max((value.bit_length() for value in rows), default=0)
    for column in range(width):
        pivot = next(
            (index for index in range(rank, len(rows)) if rows[index] & (1 << column)),
            None,
        )
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for index in range(len(rows)):
            if index != rank and rows[index] & (1 << column):
                rows[index] ^= rows[rank]
        rank += 1
    return rank


def _gf2_codespace_dimension(module, operators):
    sites = tuple(system.site_id for system in module.local_systems)
    indices = {site_id: index for index, site_id in enumerate(sites)}
    rows = []
    for operator in operators:
        assert operator.phase == 0
        value = 0
        for term in operator.terms:
            assert len(term.x_exponents) == len(term.z_exponents) == 1
            site = indices[term.site_id]
            value ^= (term.x_exponents[0] & 1) << (2 * site)
            value ^= (term.z_exponents[0] & 1) << (2 * site + 1)
        rows.append(value)
    return 2 ** (len(sites) - _gf2_rank(rows))


def _local_reference_operators(complex_, lines):
    cellular = cellular_stabilizer_code(
        complex_.chain_complex,
        2,
        2,
        convention=CellularPauliConvention.FOURIER_DUAL,
    )
    removed = {cube for line in lines for cube in line.cube_cell_ids}
    operators = [
        check.operator
        for check in cellular.check_records
        if not (check.pauli_kind == "x" and check.cell_id in removed)
    ]
    module = cellular.code.pauli_module
    operators.extend(
        module.operator((LocalPauliTerm.cyclic(face_id, z=1),))
        for line in lines
        for face_id in line.condensate_plaquette_ids
    )
    return module, tuple(operators)


def test_open_segment_matches_eq8_gsd_termination_and_dual_representation(backend):
    ball = rectangular_cubical_complex((3, 1, 1))
    segment = OpenSegment.from_cube_bases(
        ball, "open", ((0, 0, 0), (1, 0, 0))
    )
    result = analyze_toric_cheshire(ball, (segment,), backend)
    report = result.defect_reports[0]

    assert (
        result.bulk_analysis.codespace_dimension,
        result.local_analysis.codespace_dimension,
        result.fixed_sector_analysis.codespace_dimension,
    ) == (1, 2, 1)
    assert result.local_analysis.logical_invariant_factors == (2, 2)
    assert result.fixed_sector_analysis.logical_invariant_factors == ()
    assert report.transformation_certificate.product_identity_verified
    assert report.transformation_certificate.local_commutation_verified
    assert report.sector_term.operator.phase == 0
    assert len(report.endpoint_reports) == 2
    assert report.charge_termination.terminates_on_defect
    assert report.charge_termination.changes_fixed_sector
    assert report.magnetic_termination.terminates_on_defect is False
    assert report.magnetic_termination.conclusion_basis == "exact_no_solution"
    assert report.magnetic_termination.no_solution_certificate.verified
    assert result.pinned_elimination_certificate.verified
    assert result.local_pinned_elimination.certificate.verified
    assert result.fixed_sector_pinned_elimination.certificate.verified
    assert result.tubular_deleted_representation.certificate.verified
    assert (
        result.tubular_deleted_representation.local_analysis.logical_invariant_factors
        == result.local_analysis.logical_invariant_factors
    )
    assert "circuit-depth" in result.theorem_scope
    serialized = canonical_json(result)
    assert "mobility_toolkit.cheshire_static_analysis.v1" in serialized
    assert "line_tube_representation_certificate" in serialized

    assert _gf2_codespace_dimension(
        result.cellular_code.code.pauli_module,
        tuple(term.operator for term in result.bulk_terms),
    ) == 1
    assert _gf2_codespace_dimension(
        result.cellular_code.code.pauli_module,
        tuple(term.operator for term in result.local_terms),
    ) == 2
    assert _gf2_codespace_dimension(
        result.cellular_code.code.pauli_module,
        tuple(term.operator for term in result.fixed_sector_terms),
    ) == 1


def test_contractible_closed_loop_has_no_endpoints_and_one_local_sector(backend):
    ball = rectangular_cubical_complex((2, 2, 1))
    loop = ClosedLoop.from_cube_bases(
        ball,
        "loop",
        ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),
    )
    result = analyze_toric_cheshire(ball, (loop,), backend)
    assert (
        result.bulk_analysis.codespace_dimension,
        result.local_analysis.codespace_dimension,
        result.fixed_sector_analysis.codespace_dimension,
    ) == (1, 2, 1)
    assert result.defect_reports[0].endpoint_reports == ()
    assert result.pinned_elimination_certificate.verified


def test_length_and_tube_radius_are_explicit_finite_scaling_data(backend):
    ball = rectangular_cubical_complex((4, 1, 1))
    short = OpenSegment.from_cube_bases(
        ball, "short", ((0, 0, 0), (1, 0, 0), (2, 0, 0))
    )
    radius_zero = analyze_toric_cheshire(
        ball, (short,), backend, tube_radius_lattice_steps=0
    )
    radius_one_tube = TubularDefect.around_line(ball, short.line, 1)
    sample = cheshire_scaling_sample("length-3-radius-0", radius_zero)
    assert sample.path_cube_count == 3
    assert sample.condensate_count == 2
    assert sample.local_codespace_dimension == 2
    assert sample.fixed_sector_codespace_dimension == 1
    assert len(radius_one_tube.tube_site_ids) > sample.tube_site_count
    assert radius_one_tube.strata.endpoint_cube_cell_ids == short.line.endpoint_cube_ids
    assert set(short.line.condensate_plaquette_ids).isdisjoint(
        radius_one_tube.tube_wall_site_ids
    )


def test_two_open_segments_on_t3_have_one_relative_charge_qubit(backend):
    torus = rectangular_cubical_complex((3, 2, 2), periodic_axes=(0, 1, 2))
    first = OpenSegment.from_cube_bases(
        torus, "first", ((0, 0, 0), (1, 0, 0))
    )
    second = OpenSegment.from_cube_bases(
        torus, "second", ((0, 1, 1), (1, 1, 1))
    )
    result = analyze_toric_cheshire(torus, (first, second), backend)
    assert (
        result.bulk_analysis.codespace_dimension,
        result.local_analysis.codespace_dimension,
        result.fixed_sector_analysis.codespace_dimension,
    ) == (8, 16, 8)
    assert sum(len(report.endpoint_reports) for report in result.defect_reports) == 4
    module = result.cellular_code.code.pauli_module
    local_operators = tuple(term.operator for term in result.local_terms)
    first_sector = result.defect_reports[0].sector_term.operator
    second_sector = result.defect_reports[1].sector_term.operator
    assert _gf2_codespace_dimension(module, local_operators) == 16
    assert _gf2_codespace_dimension(module, local_operators + (first_sector,)) == 8
    assert _gf2_codespace_dimension(
        module, local_operators + (first_sector, second_sector)
    ) == 8


def test_noncontractible_loop_guard_rejects_component_count_formula():
    torus = rectangular_cubical_complex((4, 2, 2), periodic_axes=(0, 1, 2))
    loop = ClosedLoop.from_cube_bases(
        torus,
        "noncontractible",
        ((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)),
    ).line
    module, local_operators = _local_reference_operators(torus, (loop,))
    assert _gf2_codespace_dimension(
        module,
        cellular_stabilizer_code(
            torus.chain_complex,
            2,
            2,
            convention=CellularPauliConvention.FOURIER_DUAL,
        ).code.generators,
    ) == 8
    assert _gf2_codespace_dimension(module, local_operators) == 4


def test_analysis_revalidates_explicit_line_defect_incidence(backend):
    ball = rectangular_cubical_complex((2, 1, 1))
    valid = OpenSegment.from_cube_bases(
        ball, "valid", ((0, 0, 0), (1, 0, 0))
    ).line
    wrong_face = next(
        face_id
        for face_id in ball.chain_complex.cell_ids_by_dimension[2]
        if face_id not in valid.condensate_plaquette_ids
    )
    invalid = LineDefect(
        "invalid",
        valid.cube_cell_ids,
        (wrong_face,),
        valid.topology,
        valid.endpoint_cube_ids,
    )
    with pytest.raises(ValueError, match="ordered line links"):
        analyze_toric_cheshire(ball, (invalid,), backend)
