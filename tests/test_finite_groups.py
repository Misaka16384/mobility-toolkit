import itertools

import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import PresentedModule, SparseIntMatrix
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FiniteGroupHomomorphism,
    FlintIntegerBackend,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _generators(*columns):
    if not columns:
        raise ValueError("at least one column is required")
    nrows = len(columns[0])
    return SparseIntMatrix(
        nrows,
        len(columns),
        tuple(
            (row, column, value)
            for column, values in enumerate(columns)
            for row, value in enumerate(values)
            if value
        ),
    )


def test_z6_subgroup_sum_intersection_and_quotient(backend):
    group = FiniteAbelianGroup.from_invariant_factors((6,), backend, ("x",))
    two = group.subgroup(_generators((2,)), backend)
    three = group.subgroup(_generators((3,)), backend)
    assert group.order(backend) == 6
    assert two.order(backend) == 3
    assert three.order(backend) == 2
    assert two.contains((4,), backend)
    assert not two.contains((1,), backend)
    assert two.intersection(three, backend) == group.trivial_subgroup(backend)
    assert two.sum(three, backend) == group.whole_subgroup(backend)

    quotient = group.whole_subgroup(backend).quotient_by(two, backend)
    assert quotient.invariant_factors == (2,)
    assert quotient.order == 2


def test_redundant_generators_have_the_same_canonical_subgroup(backend):
    group = FiniteAbelianGroup.from_invariant_factors((12,), backend)
    first = group.subgroup(_generators((4,)), backend)
    second = group.subgroup(_generators((8,), (4,), (0,)), backend)
    assert first == second
    assert first.order(backend) == 3


def test_mixed_coordinate_orders_produce_canonical_invariants(backend):
    group = FiniteAbelianGroup.from_coordinate_orders(
        (2, 2, 3, 3), backend, ("x2", "z2", "x3", "z3")
    )
    assert group.invariant_factors == (6, 6)
    assert group.order(backend) == 36


def test_finite_group_from_redundant_presentation(backend):
    module = PresentedModule(
        2,
        SparseIntMatrix.from_rows(((4, 8, 0), (0, 0, 6))),
        ("a", "b"),
    )
    group = FiniteAbelianGroup.from_presentation(module, backend)
    assert group.invariant_factors == (2, 12)
    assert group.order(backend) == 24


def test_z12_to_z8_multiplication_by_two(backend):
    source = FiniteAbelianGroup.from_invariant_factors((12,), backend, ("x",))
    target = FiniteAbelianGroup.from_invariant_factors((8,), backend, ("y",))
    hom = FiniteGroupHomomorphism.create(
        source,
        target,
        SparseIntMatrix.from_rows(((2,),)),
        backend,
    )
    kernel = hom.kernel(backend)
    image = hom.image(backend)
    cokernel = hom.cokernel(backend)
    assert kernel.order(backend) == 3
    assert kernel.contains((4,), backend)
    assert kernel.contains((8,), backend)
    assert not kernel.contains((2,), backend)
    assert image.order(backend) == 4
    assert cokernel.order == 2
    assert cokernel.invariant_factors == (2,)
    assert hom.verify_first_isomorphism_order(backend)


def test_invalid_finite_homomorphism_is_rejected(backend):
    source = FiniteAbelianGroup.from_invariant_factors((4,), backend)
    target = FiniteAbelianGroup.from_invariant_factors((6,), backend)
    with pytest.raises(ValueError, match="does not descend"):
        FiniteGroupHomomorphism.create(
            source,
            target,
            SparseIntMatrix.from_rows(((1,),)),
            backend,
        )


def test_small_z6_subgroups_match_explicit_element_enumeration(backend):
    group = FiniteAbelianGroup.from_invariant_factors((6,), backend)
    for generator in range(6):
        subgroup = group.subgroup(_generators((generator,)), backend)
        explicit = {(coefficient * generator) % 6 for coefficient in range(6)}
        observed = {value for value in range(6) if subgroup.contains((value,), backend)}
        assert observed == explicit
        assert subgroup.order(backend) == len(explicit)


def test_two_coordinate_subgroup_membership_matches_brute_force(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((4, 6), backend)
    subgroup = group.subgroup(_generators((2, 3), (1, 2)), backend)
    explicit = {
        ((2 * a + b) % 4, (3 * a + 2 * b) % 6)
        for a, b in itertools.product(range(12), repeat=2)
    }
    observed = {
        (x, y)
        for x, y in itertools.product(range(4), range(6))
        if subgroup.contains((x, y), backend)
    }
    assert observed == explicit
    assert subgroup.order(backend) == len(explicit)
