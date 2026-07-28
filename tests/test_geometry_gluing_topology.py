import math

import pytest

pytest.importorskip("flint")

from mobility_toolkit.finite import FlintIntegerBackend
from mobility_toolkit.geometry import (
    BoundaryGluing,
    CellGluing,
    boundary_chain_subcomplex,
    cellular_homology,
    quotient_cell_complex,
    rectangular_cubical_complex,
    rectangular_glued_cell_complex,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def test_identity_boundary_gluings_reproduce_cylinder_and_torus(backend):
    cylinder = rectangular_glued_cell_complex((2, 3), (BoundaryGluing(0),))
    torus = rectangular_glued_cell_complex(
        (2, 3), (BoundaryGluing(0), BoundaryGluing(1))
    )
    assert cylinder.cell_counts == (8, 14, 6)
    assert cellular_homology(cylinder, 1, 5, backend).order == 5
    boundary = boundary_chain_subcomplex(cylinder)
    assert cellular_homology(boundary, 0, 2, backend).order == 4
    assert torus.cell_counts == (6, 12, 6)
    assert cellular_homology(torus, 1, 5, backend).order == 25
    assert not boundary_chain_subcomplex(torus).cell_ids_by_dimension[0]


def test_mobius_and_cylinder_have_same_h1_but_different_boundary_components(backend):
    cylinder = rectangular_glued_cell_complex((3, 2), (BoundaryGluing(0),))
    mobius = rectangular_glued_cell_complex(
        (3, 2), (BoundaryGluing(0, reverse_axes=(1,)),)
    )
    assert cellular_homology(cylinder, 1, 4, backend).order == 4
    assert cellular_homology(mobius, 1, 4, backend).order == 4
    assert cellular_homology(boundary_chain_subcomplex(cylinder), 0, 2, backend).order == 4
    assert cellular_homology(boundary_chain_subcomplex(mobius), 0, 2, backend).order == 2


@pytest.mark.parametrize("modulus", (3, 4, 6))
def test_klein_bottle_detects_orientation_reversing_gluing(backend, modulus):
    klein = rectangular_glued_cell_complex(
        (2, 2),
        (
            BoundaryGluing(0),
            BoundaryGluing(1, reverse_axes=(0,)),
        ),
    )
    homology = cellular_homology(klein, 1, modulus, backend)
    assert homology.order == modulus * math.gcd(modulus, 2)
    assert homology.invariant_factors == tuple(
        value for value in (math.gcd(modulus, 2), modulus) if value > 1
    )
    assert not boundary_chain_subcomplex(klein).cell_ids_by_dimension[0]


def test_sheared_torus_has_torus_homology(backend):
    sheared = rectangular_glued_cell_complex(
        (3, 4),
        (
            BoundaryGluing(0, transverse_shifts=(0, 1)),
            BoundaryGluing(1),
        ),
    )
    assert cellular_homology(sheared, 1, 3, backend).order == 9


def test_incompatible_partial_cell_gluing_is_rejected():
    cover = rectangular_cubical_complex((1, 1)).chain_complex
    edges = cover.cell_ids_by_dimension[1]
    with pytest.raises(ValueError, match="incompatible with cellular boundaries"):
        quotient_cell_complex(cover, (CellGluing(1, edges[0], edges[1]),))
