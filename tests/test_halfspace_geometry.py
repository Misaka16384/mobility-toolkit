from fractions import Fraction

import pytest

from mobility_toolkit.core.canonical import canonical_hash, canonical_json
from mobility_toolkit.boundary_halfspace import (
    HalfSpaceSemigroup,
    OrientationRelation,
    OrientedHalfSpace,
    PrimitiveNormal,
    SemigroupCoordinate,
    UnimodularBasisChange,
    compare_orientations,
)


def test_integer_normal_normalization_preserves_orientation():
    normal = PrimitiveNormal.from_integer((-6, 9, 3))
    assert normal.components == (-2, 3, 1)
    assert normal.opposite.components == (2, -3, -1)
    assert normal.unoriented_key == (2, -3, -1)
    assert compare_orientations(normal, normal) == OrientationRelation.SAME
    assert compare_orientations(normal, normal.opposite) == OrientationRelation.OPPOSITE
    assert (
        compare_orientations(normal, PrimitiveNormal.from_integer((1, 0, 0)))
        == OrientationRelation.NONPARALLEL
    )


def test_generic_rational_normal_is_cleared_exactly_without_floats():
    normal = PrimitiveNormal.from_rational(
        (Fraction(1, 2), Fraction(-1, 3), Fraction(1, 5))
    )
    assert normal.components == (15, -10, 6)
    with pytest.raises(TypeError, match="floats"):
        PrimitiveNormal.from_rational((0.5, Fraction(1, 3)))


@pytest.mark.parametrize(
    "components",
    [
        (1, 0),
        (2, 1),
        (1, 0, 0),  # axial X-cube boundary orientation
        (0, -1, 0),
        (2, 3, 5),  # generic rational 3D orientation
        (6, -5, 4, 3),
    ],
)
def test_adapted_unimodular_basis_is_exact_in_arbitrary_dimension(components):
    normal = PrimitiveNormal.from_integer(components)
    basis = UnimodularBasisChange.adapted_to(normal)
    certificate = basis.certificate

    assert certificate.verified
    assert abs(certificate.determinant) == 1
    assert certificate.normal_action == (0,) * (normal.dimension - 1) + (1,)
    assert all(normal.dot(vector) == 0 for vector in basis.tangent_basis)
    assert normal.dot(basis.transverse_vector) == 1

    point = tuple(index * index - 3 for index in range(normal.dimension))
    coordinates = basis.to_boundary_coordinates(point)
    assert coordinates[-1] == normal.dot(point)
    assert basis.from_boundary_coordinates(coordinates) == point
    assert "verified\":true" in canonical_json(basis)


def test_one_dimensional_basis_handles_both_orientations():
    for component in (-1, 1):
        normal = PrimitiveNormal((component,))
        basis = UnimodularBasisChange.adapted_to(normal)
        assert basis.matrix == ((component,),)
        assert basis.tangent_basis == ()
        assert basis.certificate.verified


def test_oriented_half_space_depth_and_opposite_are_affine_exact():
    half_space = OrientedHalfSpace(PrimitiveNormal.from_integer((2, 4)), 3)
    assert half_space.normal.components == (1, 2)
    assert half_space.depth((1, 1)) == 0
    assert half_space.contains((3, 0))
    assert not half_space.contains((0, 1))
    assert half_space.opposite.depth((1, 1)) == 0
    assert half_space.compare_orientation(half_space.opposite) == OrientationRelation.OPPOSITE


def test_halfspace_semigroup_round_trip_and_support_bounds_for_generic_3d_normal():
    half_space = OrientedHalfSpace(PrimitiveNormal.from_integer((2, 3, 5)))
    semigroup = HalfSpaceSemigroup.create(half_space)
    left = SemigroupCoordinate((2, -3), 4)
    right = SemigroupCoordinate((-5, 7), 2)

    assert semigroup.coordinates(semigroup.ambient(left)) == left
    assert semigroup.coordinates(semigroup.ambient(right)) == right
    assert semigroup.coordinates(semigroup.ambient(left + right)) == left + right
    assert half_space.normal.dot(semigroup.ambient(left)) == left.depth

    support = semigroup.support_descriptor(
        (semigroup.ambient(left), semigroup.ambient(right), (0, 0, 0))
    )
    assert support.depth_interval == (0, 4)
    assert support.tangent_intervals == ((-5, 2), (-3, 7))
    assert canonical_hash("support", support) == canonical_hash(
        "support",
        semigroup.support_descriptor(reversed(support.ambient_displacements)),
    )


def test_semigroup_rejects_support_on_discarded_side():
    semigroup = HalfSpaceSemigroup.create(
        OrientedHalfSpace(PrimitiveNormal.from_integer((1, 0, 0)))
    )
    assert semigroup.contains_displacement((0, 8, -2))
    assert not semigroup.contains_displacement((-1, 0, 0))
    with pytest.raises(ValueError, match="outside"):
        semigroup.support_descriptor(((0, 0, 0), (-1, 0, 0)))


def test_nonprimitive_direct_normal_and_mismatched_basis_are_rejected():
    with pytest.raises(ValueError, match="primitive"):
        PrimitiveNormal((2, 4))
    normal = PrimitiveNormal((1, 0))
    with pytest.raises(ValueError, match="adapted"):
        UnimodularBasisChange(normal, ((1, 0), (0, 1)))
