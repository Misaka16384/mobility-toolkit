import itertools

import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FlintIntegerBackend,
    PairedFiniteAbelianGroup,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _generators(*columns):
    return SparseIntMatrix(
        len(columns[0]),
        len(columns),
        tuple(
            (row, column, value)
            for column, values in enumerate(columns)
            for row, value in enumerate(values)
            if value
        ),
    )


def test_standard_mixed_pairing_is_nondegenerate(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((2, 2, 3, 3), backend)
    pairing = SparseIntMatrix.from_rows(
        (
            (0, -3, 0, 0),
            (3, 0, 0, 0),
            (0, 0, 0, -2),
            (0, 0, 2, 0),
        )
    )
    paired = PairedFiniteAbelianGroup.create(group, 6, pairing)
    radical = paired.ambient_radical(backend)
    assert radical.order(backend) == 1
    paired.verify_certificate()


def test_orthogonal_complement_matches_brute_force(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend)
    paired = PairedFiniteAbelianGroup.create(
        group, 8, SparseIntMatrix.from_rows(((0, -2), (2, 0)))
    )
    subgroup = group.subgroup(_generators((2, 0)), backend)
    orthogonal = paired.orthogonal_complement(subgroup, backend)
    explicit = {
        (x, z)
        for x, z in itertools.product(range(4), repeat=2)
        if (2 * 2 * z) % 8 == 0
    }
    observed = {
        (x, z)
        for x, z in itertools.product(range(4), repeat=2)
        if orthogonal.contains((x, z), backend)
    }
    assert observed == explicit
    assert orthogonal.order(backend) == len(explicit)


def test_degenerate_pairing_symplectic_reduction(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend)
    paired = PairedFiniteAbelianGroup.create(
        group, 4, SparseIntMatrix.from_rows(((0, -2), (2, 0)))
    )
    whole = group.whole_subgroup(backend)
    radical = paired.radical(whole, backend)
    assert radical.order(backend) == 4
    assert radical.invariant_factors(backend) == (2, 2)
    reduced = paired.symplectic_reduction(whole, backend)
    assert reduced.invariant_factors == (2, 2)
    assert reduced.order == 4


def test_isotropic_subgroup_can_be_quotiented_from_its_centralizer(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend)
    paired = PairedFiniteAbelianGroup.create(
        group, 8, SparseIntMatrix.from_rows(((0, -2), (2, 0)))
    )
    stabilizer = group.subgroup(_generators((2, 0)), backend)
    centralizer = paired.orthogonal_complement(stabilizer, backend)
    logical = paired.quotient_pairing(centralizer, stabilizer, backend)
    assert logical.invariant_factors == (2, 2)
    assert logical.order == 4


def test_pairing_descent_and_alternation_are_validated(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend)
    with pytest.raises(ValueError, match="does not descend"):
        PairedFiniteAbelianGroup.create(
            group, 6, SparseIntMatrix.from_rows(((0, -1), (1, 0)))
        )
    with pytest.raises(ValueError, match="diagonal"):
        PairedFiniteAbelianGroup.create(
            group, 4, SparseIntMatrix.from_rows(((1, 0), (0, 0)))
        )
    with pytest.raises(ValueError, match="not alternating"):
        PairedFiniteAbelianGroup.create(
            group, 4, SparseIntMatrix.from_rows(((0, 1), (1, 0)))
        )
