import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer
from mobility_toolkit.geometry import (
    FiniteCellComplex,
    boundary_subcomplex,
    cellular_homology,
    cellular_stabilizer_code,
    cubical_complex_from_top_cells,
    diagnose_cubical_mask,
    rectangular_cubical_complex,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


@pytest.mark.parametrize(
    "shape,counts",
    (
        ((1, 1), (4, 4, 1)),
        ((2, 3), (12, 17, 6)),
        ((1, 1, 1), (8, 12, 6, 1)),
    ),
)
def test_open_rectangular_cell_counts_and_chain_condition(shape, counts):
    complex_ = rectangular_cubical_complex(shape)
    assert complex_.chain_complex.cell_counts == counts
    assert complex_.chain_complex.euler_characteristic == 1


def test_annulus_and_two_hole_mask_counts_and_homology(backend):
    annulus_faces = {
        (x, y) for x in range(3) for y in range(3) if (x, y) != (1, 1)
    }
    annulus = cubical_complex_from_top_cells(annulus_faces)
    assert annulus.chain_complex.cell_counts == (16, 24, 8)
    assert annulus.chain_complex.euler_characteristic == 0
    h1 = cellular_homology(annulus.chain_complex, 1, 4, backend)
    assert h1.invariant_factors == (4,)
    assert h1.order == 4

    two_hole_faces = {
        (x, y)
        for x in range(5)
        for y in range(3)
        if (x, y) not in {(1, 1), (3, 1)}
    }
    two_holes = cubical_complex_from_top_cells(two_hole_faces)
    assert two_holes.chain_complex.cell_counts == (24, 38, 13)
    assert two_holes.chain_complex.euler_characteristic == -1
    h1_two = cellular_homology(two_holes.chain_complex, 1, 3, backend)
    assert h1_two.invariant_factors == (3, 3)
    assert h1_two.order == 9


@pytest.mark.parametrize("modulus", (2, 3, 4))
def test_cellular_toric_code_matches_independent_homology_on_disk_annulus_torus(
    backend, modulus
):
    disk = rectangular_cubical_complex((2, 2))
    annulus = cubical_complex_from_top_cells(
        {(x, y) for x in range(3) for y in range(3) if (x, y) != (1, 1)}
    )
    torus = rectangular_cubical_complex((2, 2), periodic_axes=(0, 1))
    for complex_, expected_k in ((disk, 1), (annulus, modulus), (torus, modulus**2)):
        homology = cellular_homology(complex_.chain_complex, 1, modulus, backend)
        cellular = cellular_stabilizer_code(complex_.chain_complex, 1, modulus)
        result = analyze_finite_stabilizer(
            cellular.code.pauli_module, cellular.code.generators, backend
        )
        assert cellular.code.basic_validation_errors() == ()
        assert homology.order == expected_k
        assert result.codespace_dimension == expected_k
        assert result.logical_projective_order == expected_k**2


def test_3d_edge_and_plaquette_conventions_distinguish_h1_and_h2(backend):
    ball = rectangular_cubical_complex((1, 1, 1))
    torus = rectangular_cubical_complex((1, 1, 1), periodic_axes=(0, 1, 2))
    for degree, expected_ball, expected_torus in ((1, 1, 8), (2, 1, 8)):
        for complex_, expected in ((ball, expected_ball), (torus, expected_torus)):
            homology = cellular_homology(complex_.chain_complex, degree, 2, backend)
            code = cellular_stabilizer_code(complex_.chain_complex, degree, 2)
            result = analyze_finite_stabilizer(
                code.code.pauli_module, code.code.generators, backend
            )
            assert homology.order == expected
            assert result.codespace_dimension == expected


@pytest.mark.parametrize("modulus", (2, 3))
def test_3d_solid_torus_and_cubic_shell_separate_h1_from_h2(backend, modulus):
    solid_torus = rectangular_cubical_complex((2, 1, 1), periodic_axes=(0,))
    shell_cells = {
        (x, y, z)
        for x in range(3)
        for y in range(3)
        for z in range(3)
        if (x, y, z) != (1, 1, 1)
    }
    shell = cubical_complex_from_top_cells(shell_cells)
    assert shell.chain_complex.euler_characteristic == 2
    assert cellular_homology(solid_torus.chain_complex, 1, modulus, backend).order == modulus
    assert cellular_homology(solid_torus.chain_complex, 2, modulus, backend).order == 1
    # A minimal CW model of S^2 x I gives the exact shell homology without
    # making the default suite materialize the 108-face cubical presentation.
    minimal_shell = FiniteCellComplex(
        (("vertex",), (), ("sphere",)),
        (
            SparseIntMatrix.zero(0, 1),
            SparseIntMatrix.zero(1, 0),
            SparseIntMatrix.zero(0, 1),
        ),
        ("minimal CW model of a cubic shell, homotopy equivalent to S^2",),
    )
    assert cellular_homology(minimal_shell, 1, modulus, backend).order == 1
    assert cellular_homology(minimal_shell, 2, modulus, backend).order == modulus
    plaquette_code = cellular_stabilizer_code(minimal_shell, 2, modulus)
    result = analyze_finite_stabilizer(
        plaquette_code.code.pauli_module,
        plaquette_code.code.generators,
        backend,
    )
    assert result.codespace_dimension == modulus


def test_boundary_subcomplex_has_expected_components_via_h0(backend):
    disk = rectangular_cubical_complex((3, 3))
    disk_boundary = boundary_subcomplex(disk)
    assert disk_boundary.chain_complex.cell_counts == (12, 12)
    assert cellular_homology(disk_boundary.chain_complex, 0, 2, backend).order == 2

    annulus = cubical_complex_from_top_cells(
        {(x, y) for x in range(3) for y in range(3) if (x, y) != (1, 1)}
    )
    annulus_boundary = boundary_subcomplex(annulus)
    assert cellular_homology(annulus_boundary.chain_complex, 0, 2, backend).order == 4


def test_periodic_rectangle_counts_and_topology(backend):
    cylinder = rectangular_cubical_complex((2, 3), periodic_axes=(0,))
    torus = rectangular_cubical_complex((2, 3), periodic_axes=(0, 1))
    assert cylinder.chain_complex.cell_counts == (8, 14, 6)
    assert cylinder.chain_complex.euler_characteristic == 0
    assert cellular_homology(cylinder.chain_complex, 1, 5, backend).order == 5
    assert torus.chain_complex.cell_counts == (6, 12, 6)
    assert torus.chain_complex.euler_characteristic == 0
    assert cellular_homology(torus.chain_complex, 1, 5, backend).order == 25


def test_disconnected_and_pinched_masks_have_explicit_topology_diagnostics(backend):
    disconnected_cells = {(0, 0), (3, 0)}
    disconnected = cubical_complex_from_top_cells(disconnected_cells)
    diagnostics = diagnose_cubical_mask(disconnected_cells)
    assert diagnostics.facet_connected_components == 2
    assert not diagnostics.has_junctions
    assert cellular_homology(disconnected.chain_complex, 0, 2, backend).order == 4

    diagonal_touch = {(0, 0), (1, 1)}
    pinched = cubical_complex_from_top_cells(diagonal_touch)
    pinched_diagnostics = diagnose_cubical_mask(diagonal_touch)
    assert pinched_diagnostics.facet_connected_components == 2
    assert pinched_diagnostics.has_junctions
    assert pinched_diagnostics.pinched_top_cell_pairs == (((0, 0), (1, 1)),)
    # The closures share a vertex, so H_0 sees one component; the diagnostic
    # prevents silently treating it as a manifold boundary.
    assert cellular_homology(pinched.chain_complex, 0, 2, backend).order == 2
