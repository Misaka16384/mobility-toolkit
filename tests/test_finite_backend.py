import math

import pytest

flint = pytest.importorskip("flint")

from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import (
    DenseMaterializationRefused,
    FlintIntegerBackend,
    IntegerKernelResult,
    KernelCertificate,
    NotInLattice,
    SmithInvariantResult,
    verify_integer_kernel,
    verify_smith_invariants,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _gcd_maximal_minors_3_by_2(matrix):
    rows = matrix.to_rows()
    minors = []
    for first in range(3):
        for second in range(first + 1, 3):
            minors.append(rows[first][0] * rows[second][1] - rows[first][1] * rows[second][0])
    return math.gcd(*(abs(value) for value in minors))


def test_integer_kernel_is_saturated_on_sympy_counterexample(backend):
    matrix = SparseIntMatrix.from_rows(((2, 1, 1),))
    result = backend.integer_kernel(matrix)
    assert result.basis.nrows == 3
    assert result.basis.ncols == 2
    assert matrix.matmul(result.basis).entries == ()
    # A rank-two sublattice of Z^3 is primitive exactly when the gcd of its
    # maximal minors is one. SymPy's fraction-free nullspace gives gcd two here.
    assert _gcd_maximal_minors_3_by_2(result.basis) == 1
    valid, errors = verify_integer_kernel(matrix, result)
    assert valid, errors


def test_integer_kernel_handles_empty_and_full_rank_maps(backend):
    empty_constraints = SparseIntMatrix.zero(0, 3)
    assert backend.integer_kernel(empty_constraints).basis == SparseIntMatrix.identity(3)

    full_rank = SparseIntMatrix.from_rows(((2, 0), (0, 3)))
    assert backend.integer_kernel(full_rank).basis == SparseIntMatrix.zero(2, 0)


def test_corrupted_kernel_certificate_is_rejected(backend):
    matrix = SparseIntMatrix.from_rows(((2, 1, 1),))
    result = backend.integer_kernel(matrix)
    corrupted = IntegerKernelResult(
        result.basis,
        KernelCertificate(
            result.certificate.transposed_hnf,
            SparseIntMatrix.identity(3),
            result.certificate.zero_rows,
        ),
    )
    valid, errors = verify_integer_kernel(matrix, corrupted)
    assert not valid
    assert errors


def test_column_lattice_basis_is_canonical_and_exact(backend):
    generators = SparseIntMatrix.from_rows(((4, 0, 2), (0, 6, 0)))
    result = backend.column_lattice_basis(generators)
    assert result.basis.to_rows() == ((2, 0), (0, 6))

    reordered = SparseIntMatrix.from_rows(((2, 4, 0, 2), (0, 0, 6, 0)))
    assert backend.column_lattice_basis(reordered).basis == result.basis


def test_smith_invariants_are_cross_checked(backend):
    matrix = SparseIntMatrix.from_rows(((4, 2), (6, 0)))
    result = backend.smith_invariants(matrix)
    assert result.diagonal == (2, 6)
    assert result.torsion_invariants == (2, 6)
    valid, errors = verify_smith_invariants(matrix, result)
    assert valid, errors


def test_corrupted_smith_invariants_are_rejected():
    matrix = SparseIntMatrix.from_rows(((4, 2), (6, 0)))
    corrupted = SmithInvariantResult(SparseIntMatrix.diagonal((1, 12)), (1, 12))
    valid, errors = verify_smith_invariants(matrix, corrupted)
    assert not valid
    assert errors

    mismatched_matrix = SmithInvariantResult(SparseIntMatrix.diagonal((2, 6)), (1, 12))
    valid, errors = verify_smith_invariants(matrix, mismatched_matrix)
    assert not valid
    assert "Smith matrix and declared diagonal disagree" in errors


def test_full_lattice_solve_returns_integer_witness_or_rejects(backend):
    basis = SparseIntMatrix.from_rows(((2, 0), (0, 3)))
    vectors = SparseIntMatrix.from_rows(((4, 2), (9, 6)))
    coefficients = backend.solve_full_lattice(basis, vectors)
    assert coefficients.to_rows() == ((2, 1), (3, 2))
    assert basis.matmul(coefficients) == vectors

    with pytest.raises(NotInLattice):
        backend.solve_full_lattice(
            basis,
            SparseIntMatrix.from_rows(((1,), (3,))),
        )


def test_backend_uses_arbitrary_precision_integers(backend):
    huge = 10**80 + 7
    matrix = SparseIntMatrix.from_rows(((huge, 0), (0, huge * 3)))
    assert backend.determinant(matrix) == huge * huge * 3
    assert backend.smith_invariants(matrix).diagonal == (huge, huge * 3)


def test_dense_materialization_budget_is_enforced():
    backend = FlintIntegerBackend(max_dense_entries=8)
    oversized = SparseIntMatrix(3, 3, ((0, 0, 1),))
    with pytest.raises(DenseMaterializationRefused, match="backend limit is 8"):
        backend.integer_kernel(oversized)
