"""Alternating pairings and symplectic reduction on finite abelian groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import (
    FiniteAbelianGroup,
    FiniteQuotient,
    FiniteSubgroup,
)


def _divide_entries(
    matrix: SparseIntMatrix, divisor: int, failure_message: str
) -> SparseIntMatrix:
    entries = []
    for row, column, value in matrix.entries:
        if value % divisor:
            raise ValueError(failure_message)
        quotient = value // divisor
        if quotient:
            entries.append((row, column, quotient))
    return SparseIntMatrix(matrix.nrows, matrix.ncols, tuple(entries))


def _matrix_mod(matrix: SparseIntMatrix, modulus: int) -> SparseIntMatrix:
    return SparseIntMatrix(
        matrix.nrows,
        matrix.ncols,
        tuple((row, column, value % modulus) for row, column, value in matrix.entries),
    )


@dataclass(frozen=True)
class PairingDescentCertificate:
    left_relation_witness: SparseIntMatrix
    right_relation_witness: SparseIntMatrix
    alternating_witness: SparseIntMatrix

    def to_canonical_dict(self) -> dict:
        return {
            "alternating_witness": self.alternating_witness,
            "left_relation_witness": self.left_relation_witness,
            "right_relation_witness": self.right_relation_witness,
        }


@dataclass(frozen=True)
class PairedFiniteAbelianGroup:
    group: FiniteAbelianGroup
    modulus: int
    pairing_matrix: SparseIntMatrix
    certificate: PairingDescentCertificate

    SCHEMA_ID = "mobility_toolkit.paired_finite_abelian_group.v1"

    @classmethod
    def create(
        cls,
        group: FiniteAbelianGroup,
        modulus: int,
        pairing_matrix: SparseIntMatrix,
    ) -> "PairedFiniteAbelianGroup":
        if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
            raise ValueError("pairing modulus must be an integer greater than one")
        rank = group.presentation_rank
        if (pairing_matrix.nrows, pairing_matrix.ncols) != (rank, rank):
            raise ValueError("pairing matrix has the wrong shape")
        normalized = _matrix_mod(pairing_matrix, modulus)
        if any(normalized.to_rows()[index][index] % modulus for index in range(rank)):
            raise ValueError("pairing diagonal is not zero modulo the modulus")
        alternating_sum = normalized.transpose()
        alternating_sum = SparseIntMatrix(
            rank,
            rank,
            tuple(normalized.entries) + tuple(alternating_sum.entries),
        )
        alternating_witness = _divide_entries(
            alternating_sum, modulus, "pairing is not alternating modulo the modulus"
        )
        relations = group.relation_lattice_basis
        left_witness = _divide_entries(
            relations.transpose().matmul(normalized),
            modulus,
            "pairing does not descend through the group relations",
        )
        right_witness = _divide_entries(
            normalized.matmul(relations),
            modulus,
            "pairing does not descend through the group relations",
        )
        certificate = PairingDescentCertificate(
            left_witness,
            right_witness,
            alternating_witness,
        )
        result = cls(group, modulus, normalized, certificate)
        result.verify_certificate()
        return result

    def verify_certificate(self) -> None:
        relations = self.group.relation_lattice_basis
        modulus_matrix_left = SparseIntMatrix(
            self.certificate.left_relation_witness.nrows,
            self.certificate.left_relation_witness.ncols,
            tuple(
                (row, column, self.modulus * value)
                for row, column, value in self.certificate.left_relation_witness.entries
            ),
        )
        modulus_matrix_right = SparseIntMatrix(
            self.certificate.right_relation_witness.nrows,
            self.certificate.right_relation_witness.ncols,
            tuple(
                (row, column, self.modulus * value)
                for row, column, value in self.certificate.right_relation_witness.entries
            ),
        )
        if relations.transpose().matmul(self.pairing_matrix) != modulus_matrix_left:
            raise ArithmeticError("left pairing descent certificate is invalid")
        if self.pairing_matrix.matmul(relations) != modulus_matrix_right:
            raise ArithmeticError("right pairing descent certificate is invalid")
        alternating_sum = SparseIntMatrix(
            self.group.presentation_rank,
            self.group.presentation_rank,
            tuple(self.pairing_matrix.entries)
            + tuple(self.pairing_matrix.transpose().entries),
        )
        alternating_multiple = SparseIntMatrix(
            self.certificate.alternating_witness.nrows,
            self.certificate.alternating_witness.ncols,
            tuple(
                (row, column, self.modulus * value)
                for row, column, value in self.certificate.alternating_witness.entries
            ),
        )
        if alternating_sum != alternating_multiple:
            raise ArithmeticError("alternating pairing certificate is invalid")

    def orthogonal_complement(
        self, subgroup: FiniteSubgroup, backend: FiniteIntegerBackend
    ) -> FiniteSubgroup:
        if subgroup.ambient != self.group:
            raise ValueError("subgroup belongs to a different paired group")
        rank = self.group.presentation_rank
        constraints = subgroup.preimage_lattice_basis.transpose().matmul(
            self.pairing_matrix
        )
        equations = SparseIntMatrix.hstack(
            constraints,
            SparseIntMatrix.diagonal((self.modulus,) * rank).negate(),
        )
        kernel = backend.integer_kernel(equations).basis
        generators = kernel.select_rows(tuple(range(rank)))
        return self.group.subgroup(generators, backend)

    def radical(
        self, subgroup: FiniteSubgroup, backend: FiniteIntegerBackend
    ) -> FiniteSubgroup:
        return subgroup.intersection(self.orthogonal_complement(subgroup, backend), backend)

    def ambient_radical(self, backend: FiniteIntegerBackend) -> FiniteSubgroup:
        return self.orthogonal_complement(self.group.whole_subgroup(backend), backend)

    def quotient_pairing(
        self,
        numerator: FiniteSubgroup,
        denominator: FiniteSubgroup,
        backend: FiniteIntegerBackend,
    ) -> "PairedFiniteQuotient":
        if numerator.ambient != self.group or denominator.ambient != self.group:
            raise ValueError("quotient subgroups belong to a different paired group")
        if not numerator.contains_subgroup(denominator, backend):
            raise ValueError("pairing quotient denominator is not contained in numerator")
        numerator_radical = self.radical(numerator, backend)
        if not numerator_radical.contains_subgroup(denominator, backend):
            raise ValueError("pairing does not descend: denominator is not in the radical")
        quotient = numerator.quotient_by(denominator, backend)
        representatives = numerator.preimage_lattice_basis
        pairing = _matrix_mod(
            representatives.transpose()
            .matmul(self.pairing_matrix)
            .matmul(representatives),
            self.modulus,
        )
        return PairedFiniteQuotient(
            quotient,
            self.modulus,
            representatives,
            pairing,
        )

    def symplectic_reduction(
        self, subgroup: FiniteSubgroup, backend: FiniteIntegerBackend
    ) -> "PairedFiniteQuotient":
        return self.quotient_pairing(subgroup, self.radical(subgroup, backend), backend)

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "group": self.group,
            "modulus": self.modulus,
            "pairing_matrix": self.pairing_matrix,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PairedFiniteQuotient:
    quotient: FiniteQuotient
    modulus: int
    presentation_representatives: SparseIntMatrix
    presentation_pairing_matrix: SparseIntMatrix

    SCHEMA_ID = "mobility_toolkit.paired_finite_quotient.v1"

    @property
    def invariant_factors(self) -> Tuple[int, ...]:
        return self.quotient.invariant_factors

    @property
    def order(self) -> int:
        return self.quotient.order

    def to_canonical_dict(self) -> dict:
        return {
            "invariant_factors": self.invariant_factors,
            "modulus": self.modulus,
            "order": self.order,
            "presentation_pairing_matrix": self.presentation_pairing_matrix,
            "presentation_representatives": self.presentation_representatives,
            "quotient": self.quotient,
            "schema": self.SCHEMA_ID,
        }


__all__ = [
    "PairedFiniteAbelianGroup",
    "PairedFiniteQuotient",
    "PairingDescentCertificate",
]
