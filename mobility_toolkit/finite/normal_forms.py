"""Certified modular normal forms derived from exact integer lattices."""

from __future__ import annotations

from dataclasses import dataclass

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite.backend import (
    ColumnLatticeResult,
    FiniteIntegerBackend,
    verify_column_lattice,
)


@dataclass(frozen=True)
class HowellFormResult:
    """Canonical row-module form over ``Z/modulus``.

    The form is obtained from the row-HNF of the integer preimage lattice
    ``rowspan_Z(A) + modulus*Z^n``.  Reducing its nontrivial rows modulo the
    modulus is the Howell form; retaining the integer lift supplies a complete
    lattice certificate instead of relying on modular pivot heuristics.
    """

    modulus: int
    form: SparseIntMatrix
    lifted_preimage_basis: SparseIntMatrix
    preimage_certificate: ColumnLatticeResult

    SCHEMA_ID = "mobility_toolkit.howell_form_result.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "form": self.form,
            "lifted_preimage_basis": self.lifted_preimage_basis,
            "modulus": self.modulus,
            "preimage_certificate": self.preimage_certificate,
            "schema": self.SCHEMA_ID,
        }


def _reduced_nonzero_rows(matrix: SparseIntMatrix, modulus: int) -> SparseIntMatrix:
    rows = []
    for row in matrix.to_rows():
        reduced = tuple(value % modulus for value in row)
        if any(reduced):
            rows.append(reduced)
    if not rows:
        return SparseIntMatrix.zero(0, matrix.ncols)
    return SparseIntMatrix.from_rows(tuple(rows))


def howell_form(
    matrix: SparseIntMatrix,
    modulus: int,
    backend: FiniteIntegerBackend,
) -> HowellFormResult:
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise ValueError("Howell modulus must be an integer greater than one")
    augmented_rows = SparseIntMatrix.vstack(
        matrix,
        SparseIntMatrix.diagonal((modulus,) * matrix.ncols),
    )
    preimage = backend.column_lattice_basis(augmented_rows.transpose())
    lifted = preimage.basis.transpose()
    form = _reduced_nonzero_rows(lifted, modulus)
    result = HowellFormResult(modulus, form, lifted, preimage)
    verify_howell_form(matrix, result)
    return result


def verify_howell_form(
    matrix: SparseIntMatrix, result: HowellFormResult
) -> None:
    if result.form.ncols != matrix.ncols:
        raise ArithmeticError("Howell form has the wrong column count")
    valid, errors = verify_column_lattice(
        SparseIntMatrix.vstack(
            matrix,
            SparseIntMatrix.diagonal((result.modulus,) * matrix.ncols),
        ).transpose(),
        result.preimage_certificate,
    )
    if not valid:
        raise ArithmeticError("invalid Howell lattice certificate: " + "; ".join(errors))
    expected_lift = result.preimage_certificate.basis.transpose()
    if result.lifted_preimage_basis != expected_lift:
        raise ArithmeticError("Howell integer lift disagrees with its certificate")
    expected_form = _reduced_nonzero_rows(expected_lift, result.modulus)
    if result.form != expected_form:
        raise ArithmeticError("Howell rows disagree with the certified integer lift")
    if any(
        value < 0 or value >= result.modulus
        for _, _, value in result.form.entries
    ):
        raise ArithmeticError("Howell entries are not canonical residues")


__all__ = ["HowellFormResult", "howell_form", "verify_howell_form"]
