"""Certified integer-lattice primitives for finite abelian computations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Tuple

from sympy import Matrix as SympyMatrix
from sympy.matrices.normalforms import smith_normal_form as sympy_smith_normal_form
from sympy.polys.domains import ZZ

from mobility_toolkit.core.integer import SparseIntMatrix


class FiniteBackendUnavailable(RuntimeError):
    pass


class DenseMaterializationRefused(MemoryError):
    pass


class NotInLattice(ValueError):
    pass


@dataclass(frozen=True)
class KernelCertificate:
    transposed_hnf: SparseIntMatrix
    unimodular_transform: SparseIntMatrix
    zero_rows: Tuple[int, ...]

    def to_canonical_dict(self) -> dict:
        return {
            "transposed_hnf": self.transposed_hnf,
            "unimodular_transform": self.unimodular_transform,
            "zero_rows": self.zero_rows,
        }


@dataclass(frozen=True)
class IntegerKernelResult:
    basis: SparseIntMatrix
    certificate: KernelCertificate

    def to_canonical_dict(self) -> dict:
        return {"basis": self.basis, "certificate": self.certificate}


@dataclass(frozen=True)
class ColumnLatticeCertificate:
    transposed_hnf: SparseIntMatrix
    unimodular_transform: SparseIntMatrix
    nonzero_rows: Tuple[int, ...]

    def to_canonical_dict(self) -> dict:
        return {
            "nonzero_rows": self.nonzero_rows,
            "transposed_hnf": self.transposed_hnf,
            "unimodular_transform": self.unimodular_transform,
        }


@dataclass(frozen=True)
class ColumnLatticeResult:
    basis: SparseIntMatrix
    certificate: ColumnLatticeCertificate

    def to_canonical_dict(self) -> dict:
        return {"basis": self.basis, "certificate": self.certificate}


@dataclass(frozen=True)
class SmithInvariantResult:
    smith_matrix: SparseIntMatrix
    diagonal: Tuple[int, ...]

    @property
    def torsion_invariants(self) -> Tuple[int, ...]:
        return tuple(value for value in self.diagonal if value > 1)

    def to_canonical_dict(self) -> dict:
        return {
            "diagonal": self.diagonal,
            "smith_matrix": self.smith_matrix,
            "torsion_invariants": self.torsion_invariants,
        }


class FiniteIntegerBackend(Protocol):
    name: str
    version: str

    def integer_kernel(self, matrix: SparseIntMatrix) -> IntegerKernelResult:
        ...

    def column_lattice_basis(self, matrix: SparseIntMatrix) -> ColumnLatticeResult:
        ...

    def smith_invariants(self, matrix: SparseIntMatrix) -> SmithInvariantResult:
        ...

    def determinant(self, matrix: SparseIntMatrix) -> int:
        ...

    def solve_full_lattice(
        self, basis: SparseIntMatrix, vectors: SparseIntMatrix
    ) -> SparseIntMatrix:
        ...


def _sympy_matrix(matrix: SparseIntMatrix) -> SympyMatrix:
    return SympyMatrix(matrix.to_rows())


def _determinant(matrix: SparseIntMatrix) -> int:
    if matrix.nrows != matrix.ncols:
        raise ValueError("determinant requires a square matrix")
    if matrix.nrows == 0:
        return 1
    return int(_sympy_matrix(matrix).det())


def _row_is_zero(matrix: SparseIntMatrix, row: int) -> bool:
    return all(entry_row != row for entry_row, _, _ in matrix.entries)


def verify_integer_kernel(
    matrix: SparseIntMatrix, result: IntegerKernelResult
) -> Tuple[bool, Tuple[str, ...]]:
    """Independently verify soundness and completeness of an integer kernel."""

    errors = []
    certificate = result.certificate
    transform = certificate.unimodular_transform
    transposed = matrix.transpose()
    if transform.nrows != matrix.ncols or transform.ncols != matrix.ncols:
        errors.append("kernel transform has the wrong shape")
    else:
        if transform.matmul(transposed) != certificate.transposed_hnf:
            errors.append("kernel certificate does not satisfy H = U*A^T")
        if abs(_determinant(transform)) != 1:
            errors.append("kernel transform is not unimodular")
    if tuple(sorted(set(certificate.zero_rows))) != certificate.zero_rows:
        errors.append("kernel zero-row indices are not canonical")
    if any(
        row < 0
        or row >= certificate.transposed_hnf.nrows
        or not _row_is_zero(certificate.transposed_hnf, row)
        for row in certificate.zero_rows
    ):
        errors.append("kernel certificate names a nonzero or invalid HNF row")
    all_zero_rows = tuple(
        row
        for row in range(certificate.transposed_hnf.nrows)
        if _row_is_zero(certificate.transposed_hnf, row)
    )
    if all_zero_rows != certificate.zero_rows:
        errors.append("kernel certificate omits or adds zero rows")
    if result.basis.nrows != matrix.ncols:
        errors.append("kernel basis has the wrong ambient dimension")
    elif matrix.matmul(result.basis).entries:
        errors.append("kernel basis is not in the kernel")
    expected_basis = SparseIntMatrix(
        matrix.ncols,
        len(certificate.zero_rows),
        tuple(
            (column, basis_column, value)
            for basis_column, transform_row in enumerate(certificate.zero_rows)
            for row, column, value in transform.entries
            if row == transform_row
        ),
    )
    if result.basis != expected_basis:
        errors.append("kernel basis does not match zero rows of the unimodular transform")
    expected_nullity = matrix.ncols - int(_sympy_matrix(matrix).rank())
    if result.basis.ncols != expected_nullity:
        errors.append("kernel basis has the wrong nullity")
    return not errors, tuple(errors)


def verify_column_lattice(
    matrix: SparseIntMatrix, result: ColumnLatticeResult
) -> Tuple[bool, Tuple[str, ...]]:
    """Verify that a basis generates exactly the input column lattice."""

    errors = []
    certificate = result.certificate
    transform = certificate.unimodular_transform
    transposed = matrix.transpose()
    if transform.nrows != matrix.ncols or transform.ncols != matrix.ncols:
        errors.append("lattice transform has the wrong shape")
    else:
        if transform.matmul(transposed) != certificate.transposed_hnf:
            errors.append("lattice certificate does not satisfy H = U*A^T")
        if abs(_determinant(transform)) != 1:
            errors.append("lattice transform is not unimodular")
    actual_nonzero = tuple(
        row
        for row in range(certificate.transposed_hnf.nrows)
        if not _row_is_zero(certificate.transposed_hnf, row)
    )
    if actual_nonzero != certificate.nonzero_rows:
        errors.append("lattice certificate has incorrect nonzero rows")
    expected_basis = SparseIntMatrix(
        matrix.nrows,
        len(certificate.nonzero_rows),
        tuple(
            (column, basis_column, value)
            for basis_column, hnf_row in enumerate(certificate.nonzero_rows)
            for row, column, value in certificate.transposed_hnf.entries
            if row == hnf_row
        ),
    )
    if result.basis != expected_basis:
        errors.append("lattice basis is not the transpose of nonzero HNF rows")
    if result.basis.ncols != int(_sympy_matrix(matrix).rank()):
        errors.append("lattice basis has the wrong rank")
    return not errors, tuple(errors)


def verify_smith_invariants(
    matrix: SparseIntMatrix, result: SmithInvariantResult
) -> Tuple[bool, Tuple[str, ...]]:
    """Cross-check Smith invariants with SymPy's independent implementation."""

    errors = []
    expected = sympy_smith_normal_form(_sympy_matrix(matrix), domain=ZZ)
    diagonal = tuple(
        abs(int(expected[index, index]))
        for index in range(min(expected.rows, expected.cols))
        if expected[index, index] != 0
    )
    if result.diagonal != diagonal:
        errors.append("Smith diagonal disagrees with the independent verifier")
    matrix_diagonal = tuple(
        value
        for row, column, value in result.smith_matrix.entries
        if row == column and value != 0
    )
    if matrix_diagonal != result.diagonal:
        errors.append("Smith matrix and declared diagonal disagree")
    if any(right % left != 0 for left, right in zip(result.diagonal, result.diagonal[1:])):
        errors.append("Smith diagonal does not form a divisibility chain")
    if result.smith_matrix.nrows != matrix.nrows or result.smith_matrix.ncols != matrix.ncols:
        errors.append("Smith matrix has the wrong shape")
    for row, column, value in result.smith_matrix.entries:
        if row != column:
            errors.append("Smith matrix is not diagonal")
            break
        if value < 0:
            errors.append("Smith diagonal is not normalized positive")
            break
    return not errors, tuple(errors)


class FlintIntegerBackend:
    """Arbitrary-precision integer backend using public python-flint APIs."""

    name = "python-flint"

    DEFAULT_MAX_DENSE_ENTRIES = 2_000_000

    def __init__(self, max_dense_entries: int = DEFAULT_MAX_DENSE_ENTRIES) -> None:
        if (
            isinstance(max_dense_entries, bool)
            or not isinstance(max_dense_entries, int)
            or max_dense_entries < 1
        ):
            raise ValueError("max_dense_entries must be a positive integer")
        try:
            import flint
            from flint import fmpz_mat
        except ImportError as exc:
            raise FiniteBackendUnavailable(
                "certified finite arithmetic requires the optional 'finite' extra"
            ) from exc
        self._flint = flint
        self._matrix_type = fmpz_mat
        self.version = str(flint.__version__)
        self.max_dense_entries = max_dense_entries

    def _to_flint(self, matrix: SparseIntMatrix):
        dense_entries = matrix.nrows * matrix.ncols
        if dense_entries > self.max_dense_entries:
            raise DenseMaterializationRefused(
                f"refusing to materialize {dense_entries} dense integer entries; "
                f"backend limit is {self.max_dense_entries}"
            )
        if matrix.nrows == 0 or matrix.ncols == 0:
            return self._matrix_type(matrix.nrows, matrix.ncols)
        return self._matrix_type([list(row) for row in matrix.to_rows()])

    def _from_flint(self, matrix) -> SparseIntMatrix:
        nrows = int(matrix.nrows())
        ncols = int(matrix.ncols())
        entries = []
        for row in range(nrows):
            for column in range(ncols):
                value = int(matrix[row, column])
                if value:
                    entries.append((row, column, value))
        return SparseIntMatrix(nrows, ncols, tuple(entries))

    def integer_kernel(self, matrix: SparseIntMatrix) -> IntegerKernelResult:
        transposed = self._to_flint(matrix.transpose())
        hnf, transform = transposed.hnf(transform=True)
        hnf_ir = self._from_flint(hnf)
        transform_ir = self._from_flint(transform)
        zero_rows = tuple(
            row for row in range(hnf_ir.nrows) if _row_is_zero(hnf_ir, row)
        )
        basis = SparseIntMatrix(
            matrix.ncols,
            len(zero_rows),
            tuple(
                (column, basis_column, value)
                for basis_column, transform_row in enumerate(zero_rows)
                for row, column, value in transform_ir.entries
                if row == transform_row
            ),
        )
        result = IntegerKernelResult(
            basis,
            KernelCertificate(hnf_ir, transform_ir, zero_rows),
        )
        valid, errors = verify_integer_kernel(matrix, result)
        if not valid:
            raise ArithmeticError("invalid FLINT integer kernel: " + "; ".join(errors))
        return result

    def column_lattice_basis(self, matrix: SparseIntMatrix) -> ColumnLatticeResult:
        transposed = self._to_flint(matrix.transpose())
        hnf, transform = transposed.hnf(transform=True)
        hnf_ir = self._from_flint(hnf)
        transform_ir = self._from_flint(transform)
        nonzero_rows = tuple(
            row for row in range(hnf_ir.nrows) if not _row_is_zero(hnf_ir, row)
        )
        basis = SparseIntMatrix(
            matrix.nrows,
            len(nonzero_rows),
            tuple(
                (column, basis_column, value)
                for basis_column, hnf_row in enumerate(nonzero_rows)
                for row, column, value in hnf_ir.entries
                if row == hnf_row
            ),
        )
        result = ColumnLatticeResult(
            basis,
            ColumnLatticeCertificate(hnf_ir, transform_ir, nonzero_rows),
        )
        valid, errors = verify_column_lattice(matrix, result)
        if not valid:
            raise ArithmeticError("invalid FLINT column lattice: " + "; ".join(errors))
        return result

    def smith_invariants(self, matrix: SparseIntMatrix) -> SmithInvariantResult:
        smith = self._from_flint(self._to_flint(matrix).snf())
        diagonal = tuple(
            abs(value)
            for row, column, value in smith.entries
            if row == column and value != 0
        )
        normalized_entries = tuple(
            (row, column, abs(value)) for row, column, value in smith.entries if value != 0
        )
        smith = SparseIntMatrix(smith.nrows, smith.ncols, normalized_entries)
        result = SmithInvariantResult(smith, diagonal)
        valid, errors = verify_smith_invariants(matrix, result)
        if not valid:
            raise ArithmeticError("invalid FLINT Smith form: " + "; ".join(errors))
        return result

    def determinant(self, matrix: SparseIntMatrix) -> int:
        if matrix.nrows != matrix.ncols:
            raise ValueError("determinant requires a square matrix")
        if matrix.nrows == 0:
            return 1
        return int(self._to_flint(matrix).det())

    def solve_full_lattice(
        self, basis: SparseIntMatrix, vectors: SparseIntMatrix
    ) -> SparseIntMatrix:
        if basis.nrows != basis.ncols:
            raise ValueError("full-lattice solve requires a square basis")
        if vectors.nrows != basis.nrows:
            raise ValueError("lattice vectors have the wrong ambient dimension")
        if basis.nrows == 0:
            return SparseIntMatrix.zero(0, vectors.ncols)
        solution = self._to_flint(basis).inv() * self._to_flint(vectors)
        entries = []
        for row in range(int(solution.nrows())):
            for column in range(int(solution.ncols())):
                value = solution[row, column]
                if int(value.denominator) != 1:
                    raise NotInLattice("vectors do not belong to the full-rank lattice")
                integer_value = int(value.numerator)
                if integer_value:
                    entries.append((row, column, integer_value))
        coefficients = SparseIntMatrix(basis.ncols, vectors.ncols, tuple(entries))
        if basis.matmul(coefficients) != vectors:
            raise ArithmeticError("lattice solve failed its defining identity")
        return coefficients


__all__ = [
    "ColumnLatticeCertificate",
    "ColumnLatticeResult",
    "FiniteBackendUnavailable",
    "DenseMaterializationRefused",
    "FiniteIntegerBackend",
    "FlintIntegerBackend",
    "IntegerKernelResult",
    "KernelCertificate",
    "NotInLattice",
    "SmithInvariantResult",
    "verify_column_lattice",
    "verify_integer_kernel",
    "verify_smith_invariants",
]
