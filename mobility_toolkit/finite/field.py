"""Certified prime-field fast paths with canonical integer-matrix outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from sympy import isprime

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import FiniteAbelianGroup, FiniteSubgroup


def _matrix_mod(matrix: SparseIntMatrix, prime: int) -> SparseIntMatrix:
    return SparseIntMatrix(
        matrix.nrows,
        matrix.ncols,
        tuple((row, column, value % prime) for row, column, value in matrix.entries),
    )


def _modular_rank(matrix: SparseIntMatrix, prime: int) -> int:
    """Independent forward elimination used only by certificate verification."""

    rows = [[value % prime for value in row] for row in matrix.to_rows()]
    pivot_row = 0
    for column in range(matrix.ncols):
        selected = next(
            (row for row in range(pivot_row, matrix.nrows) if rows[row][column]),
            None,
        )
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        inverse = pow(rows[pivot_row][column], -1, prime)
        rows[pivot_row] = [(value * inverse) % prime for value in rows[pivot_row]]
        for row in range(pivot_row + 1, matrix.nrows):
            coefficient = rows[row][column]
            if coefficient:
                rows[row] = [
                    (value - coefficient * pivot) % prime
                    for value, pivot in zip(rows[row], rows[pivot_row])
                ]
        pivot_row += 1
        if pivot_row == matrix.nrows:
            break
    return pivot_row


@dataclass(frozen=True)
class PrimeFieldRrefResult:
    prime: int
    rref: SparseIntMatrix
    pivot_columns: Tuple[int, ...]
    row_transform: SparseIntMatrix
    algorithm: str

    SCHEMA_ID = "mobility_toolkit.prime_field_rref_result.v1"

    @property
    def rank(self) -> int:
        return len(self.pivot_columns)

    def to_canonical_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "pivot_columns": self.pivot_columns,
            "prime": self.prime,
            "rank": self.rank,
            "row_transform": self.row_transform,
            "rref": self.rref,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PrimeFieldKernelResult:
    basis: SparseIntMatrix
    rref_certificate: PrimeFieldRrefResult

    SCHEMA_ID = "mobility_toolkit.prime_field_kernel_result.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "basis": self.basis,
            "rref_certificate": self.rref_certificate,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PrimeFieldSubgroupResult:
    ambient: FiniteAbelianGroup
    subgroup: FiniteSubgroup
    kernel_certificate: PrimeFieldKernelResult

    def to_canonical_dict(self) -> dict:
        return {
            "ambient": self.ambient,
            "kernel_certificate": self.kernel_certificate,
            "subgroup": self.subgroup,
        }


def _validate_prime(prime: int) -> None:
    if isinstance(prime, bool) or not isinstance(prime, int) or not isprime(prime):
        raise ValueError("field modulus must be prime")


def _generic_rref(matrix: SparseIntMatrix, prime: int) -> PrimeFieldRrefResult:
    rows = [[value % prime for value in row] for row in matrix.to_rows()]
    transform = [
        [1 if row == column else 0 for column in range(matrix.nrows)]
        for row in range(matrix.nrows)
    ]
    pivot_columns = []
    pivot_row = 0
    for column in range(matrix.ncols):
        selected = next(
            (row for row in range(pivot_row, matrix.nrows) if rows[row][column]),
            None,
        )
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        transform[pivot_row], transform[selected] = transform[selected], transform[pivot_row]
        inverse = pow(rows[pivot_row][column], -1, prime)
        rows[pivot_row] = [(value * inverse) % prime for value in rows[pivot_row]]
        transform[pivot_row] = [
            (value * inverse) % prime for value in transform[pivot_row]
        ]
        for row in range(matrix.nrows):
            if row == pivot_row or not rows[row][column]:
                continue
            coefficient = rows[row][column]
            rows[row] = [
                (value - coefficient * pivot) % prime
                for value, pivot in zip(rows[row], rows[pivot_row])
            ]
            transform[row] = [
                (value - coefficient * pivot) % prime
                for value, pivot in zip(transform[row], transform[pivot_row])
            ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == matrix.nrows:
            break
    return PrimeFieldRrefResult(
        prime,
        SparseIntMatrix.from_rows(tuple(rows)) if rows else SparseIntMatrix.zero(0, matrix.ncols),
        tuple(pivot_columns),
        SparseIntMatrix.from_rows(tuple(transform))
        if transform
        else SparseIntMatrix.zero(0, 0),
        "modular_gaussian",
    )


def _binary_rref(matrix: SparseIntMatrix) -> PrimeFieldRrefResult:
    width = matrix.ncols
    packed = []
    for row_index, row in enumerate(matrix.to_rows()):
        value = sum((entry & 1) << column for column, entry in enumerate(row))
        value |= 1 << (width + row_index)
        packed.append(value)
    pivot_columns = []
    pivot_row = 0
    for column in range(width):
        selected = next(
            (row for row in range(pivot_row, matrix.nrows) if packed[row] >> column & 1),
            None,
        )
        if selected is None:
            continue
        packed[pivot_row], packed[selected] = packed[selected], packed[pivot_row]
        for row in range(matrix.nrows):
            if row != pivot_row and packed[row] >> column & 1:
                packed[row] ^= packed[pivot_row]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == matrix.nrows:
            break
    rref_rows = tuple(
        tuple((packed[row] >> column) & 1 for column in range(width))
        for row in range(matrix.nrows)
    )
    transform_rows = tuple(
        tuple((packed[row] >> (width + column)) & 1 for column in range(matrix.nrows))
        for row in range(matrix.nrows)
    )
    return PrimeFieldRrefResult(
        2,
        SparseIntMatrix.from_rows(rref_rows)
        if rref_rows
        else SparseIntMatrix.zero(0, width),
        tuple(pivot_columns),
        SparseIntMatrix.from_rows(transform_rows)
        if transform_rows
        else SparseIntMatrix.zero(0, 0),
        "bitpacked_gf2",
    )


def prime_field_rref(
    matrix: SparseIntMatrix,
    prime: int,
    *,
    use_bitpacked: bool = True,
) -> PrimeFieldRrefResult:
    _validate_prime(prime)
    result = (
        _binary_rref(matrix)
        if prime == 2 and use_bitpacked
        else _generic_rref(matrix, prime)
    )
    verify_prime_field_rref(matrix, result)
    return result


def verify_prime_field_rref(
    matrix: SparseIntMatrix, result: PrimeFieldRrefResult
) -> None:
    _validate_prime(result.prime)
    prime = result.prime
    if (result.rref.nrows, result.rref.ncols) != (matrix.nrows, matrix.ncols):
        raise ArithmeticError("prime-field RREF has the wrong shape")
    if (result.row_transform.nrows, result.row_transform.ncols) != (
        matrix.nrows,
        matrix.nrows,
    ):
        raise ArithmeticError("prime-field row transform has the wrong shape")
    if _matrix_mod(result.row_transform.matmul(matrix), prime) != result.rref:
        raise ArithmeticError("prime-field certificate does not satisfy R = U*A")
    if _modular_rank(result.row_transform, prime) != matrix.nrows:
        raise ArithmeticError("prime-field row transform is not invertible")
    rows = result.rref.to_rows()
    observed_pivots = []
    zero_seen = False
    for row_index, row in enumerate(rows):
        nonzero = tuple(index for index, value in enumerate(row) if value % prime)
        if not nonzero:
            zero_seen = True
            continue
        if zero_seen:
            raise ArithmeticError("prime-field RREF has a nonzero row after a zero row")
        pivot = nonzero[0]
        observed_pivots.append(pivot)
        if row[pivot] % prime != 1:
            raise ArithmeticError("prime-field RREF pivot is not one")
        if any(rows[other][pivot] % prime for other in range(len(rows)) if other != row_index):
            raise ArithmeticError("prime-field RREF pivot column is not reduced")
    if tuple(observed_pivots) != result.pivot_columns:
        raise ArithmeticError("prime-field pivot certificate is incorrect")
    if tuple(sorted(result.pivot_columns)) != result.pivot_columns:
        raise ArithmeticError("prime-field pivots are not in echelon order")


def prime_field_kernel(
    matrix: SparseIntMatrix,
    prime: int,
    *,
    use_bitpacked: bool = True,
) -> PrimeFieldKernelResult:
    rref = prime_field_rref(matrix, prime, use_bitpacked=use_bitpacked)
    pivot_to_row = {pivot: row for row, pivot in enumerate(rref.pivot_columns)}
    free_columns = tuple(
        column for column in range(matrix.ncols) if column not in pivot_to_row
    )
    rref_rows = rref.rref.to_rows()
    entries = []
    for basis_column, free_column in enumerate(free_columns):
        entries.append((free_column, basis_column, 1))
        for pivot_column, row in pivot_to_row.items():
            value = (-rref_rows[row][free_column]) % prime
            if value:
                entries.append((pivot_column, basis_column, value))
    result = PrimeFieldKernelResult(
        SparseIntMatrix(matrix.ncols, len(free_columns), tuple(entries)),
        rref,
    )
    verify_prime_field_kernel(matrix, result)
    return result


def verify_prime_field_kernel(
    matrix: SparseIntMatrix, result: PrimeFieldKernelResult
) -> None:
    verify_prime_field_rref(matrix, result.rref_certificate)
    prime = result.rref_certificate.prime
    if result.basis.nrows != matrix.ncols:
        raise ArithmeticError("prime-field kernel basis has the wrong row count")
    if _matrix_mod(matrix.matmul(result.basis), prime).entries:
        raise ArithmeticError("prime-field kernel basis is not in the kernel")
    expected_nullity = matrix.ncols - result.rref_certificate.rank
    if result.basis.ncols != expected_nullity:
        raise ArithmeticError("prime-field kernel basis has the wrong nullity")


def prime_field_kernel_subgroup(
    matrix: SparseIntMatrix,
    prime: int,
    backend: FiniteIntegerBackend,
) -> PrimeFieldSubgroupResult:
    kernel = prime_field_kernel(matrix, prime)
    ambient = FiniteAbelianGroup.from_coordinate_orders(
        (prime,) * matrix.ncols, backend
    )
    subgroup = ambient.subgroup(kernel.basis, backend)
    if subgroup.order(backend) != prime ** kernel.basis.ncols:
        raise ArithmeticError("field kernel and canonical FGA subgroup disagree")
    return PrimeFieldSubgroupResult(ambient, subgroup, kernel)


__all__ = [
    "PrimeFieldKernelResult",
    "PrimeFieldRrefResult",
    "PrimeFieldSubgroupResult",
    "prime_field_kernel",
    "prime_field_kernel_subgroup",
    "prime_field_rref",
    "verify_prime_field_kernel",
    "verify_prime_field_rref",
]
