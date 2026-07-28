import itertools

import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import (
    FlintIntegerBackend,
    PrimeFieldRrefResult,
    prime_field_kernel,
    prime_field_kernel_subgroup,
    prime_field_rref,
    verify_prime_field_rref,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _multiply_mod(matrix, vector, prime):
    return tuple(
        sum(value * coordinate for value, coordinate in zip(row, vector)) % prime
        for row in matrix.to_rows()
    )


def test_bitpacked_gf2_matches_generic_rref_exhaustively():
    for bits in itertools.product(range(2), repeat=6):
        matrix = SparseIntMatrix.from_rows((bits[:3], bits[3:]))
        fast = prime_field_rref(matrix, 2, use_bitpacked=True)
        generic = prime_field_rref(matrix, 2, use_bitpacked=False)
        assert fast.rref == generic.rref
        assert fast.pivot_columns == generic.pivot_columns
        assert fast.algorithm == "bitpacked_gf2"


@pytest.mark.parametrize("prime", (2, 3, 5, 7))
def test_prime_field_kernel_matches_explicit_enumeration(prime):
    matrix = SparseIntMatrix.from_rows(((2, 1, 3), (1, 4, 2)))
    kernel = prime_field_kernel(matrix, prime)
    explicit = {
        vector
        for vector in itertools.product(range(prime), repeat=3)
        if not any(_multiply_mod(matrix, vector, prime))
    }
    basis_rows = kernel.basis.to_rows()
    observed = {
        tuple(
            sum(
                basis_rows[row][column] * coefficients[column]
                for column in range(kernel.basis.ncols)
            )
            % prime
            for row in range(kernel.basis.nrows)
        )
        for coefficients in itertools.product(range(prime), repeat=kernel.basis.ncols)
    }
    assert observed == explicit


def test_field_fast_path_returns_canonical_fga_subgroup(backend):
    matrix = SparseIntMatrix.from_rows(((1, 1, 0, 0), (0, 1, 1, 0)))
    result = prime_field_kernel_subgroup(matrix, 2, backend)
    assert result.kernel_certificate.rref_certificate.algorithm == "bitpacked_gf2"
    assert result.subgroup.order(backend) == 4
    explicit = {
        vector
        for vector in itertools.product(range(2), repeat=4)
        if not any(_multiply_mod(matrix, vector, 2))
    }
    observed = {
        vector
        for vector in itertools.product(range(2), repeat=4)
        if result.subgroup.contains(vector, backend)
    }
    assert observed == explicit


def test_composite_field_modulus_is_rejected():
    with pytest.raises(ValueError, match="must be prime"):
        prime_field_rref(SparseIntMatrix.identity(2), 4)


def test_corrupted_rref_certificate_is_rejected():
    matrix = SparseIntMatrix.from_rows(((1, 2), (2, 1)))
    result = prime_field_rref(matrix, 3)
    corrupted = PrimeFieldRrefResult(
        result.prime,
        result.rref,
        result.pivot_columns,
        SparseIntMatrix.identity(2),
        result.algorithm,
    )
    with pytest.raises(ArithmeticError, match=r"R = U\*A"):
        verify_prime_field_rref(matrix, corrupted)
