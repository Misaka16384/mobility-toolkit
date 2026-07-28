"""Exact finite metric groups for abstract Abelian anyon data.

The bilinear form here is the *symmetric* monodromy pairing.  It must not be
confused with the alternating Pauli commutator represented by
``PairedFiniteAbelianGroup``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FiniteIntegerBackend,
    FiniteSubgroup,
    PairedFiniteAbelianGroup,
)


def _plain_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _matrix_mod(matrix: SparseIntMatrix, modulus: int) -> SparseIntMatrix:
    return SparseIntMatrix(
        matrix.nrows,
        matrix.ncols,
        tuple((row, column, value % modulus) for row, column, value in matrix.entries),
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


def _column(matrix: SparseIntMatrix, index: int) -> Tuple[int, ...]:
    return tuple(row[index] for row in matrix.to_rows())


def _raw_braiding(
    matrix: SparseIntMatrix, left: Sequence[int], right: Sequence[int]
) -> int:
    rows = matrix.to_rows()
    return sum(
        int(left[row]) * rows[row][column] * int(right[column])
        for row in range(matrix.nrows)
        for column in range(matrix.ncols)
    )


def _raw_spin(
    matrix: SparseIntMatrix, generator_spins: Sequence[int], vector: Sequence[int]
) -> int:
    """Evaluate the unique coordinate quadratic polynomial with polarization M."""

    values = tuple(int(value) for value in vector)
    rows = matrix.to_rows()
    result = sum(value * generator_spins[index] for index, value in enumerate(values))
    for index, value in enumerate(values):
        result += value * (value - 1) // 2 * rows[index][index]
    for left in range(len(values)):
        for right in range(left + 1, len(values)):
            result += values[left] * values[right] * rows[left][right]
    return result


def _orthogonal_complement(
    group: FiniteAbelianGroup,
    pairing: SparseIntMatrix,
    modulus: int,
    subgroup: FiniteSubgroup,
    backend: FiniteIntegerBackend,
) -> FiniteSubgroup:
    if subgroup.ambient != group:
        raise ValueError("subgroup belongs to a different finite group")
    rank = group.presentation_rank
    constraints = subgroup.preimage_lattice_basis.transpose().matmul(pairing)
    equations = SparseIntMatrix.hstack(
        constraints,
        SparseIntMatrix.diagonal((modulus,) * rank).negate(),
    )
    kernel = backend.integer_kernel(equations).basis
    generators = kernel.select_rows(tuple(range(rank)))
    return group.subgroup(generators, backend)


@dataclass(frozen=True)
class MetricDescentCertificate:
    """Integer witnesses proving that ``B`` and ``q`` descend to the quotient."""

    left_relation_witness: SparseIntMatrix
    right_relation_witness: SparseIntMatrix
    symmetry_witness: SparseIntMatrix
    relation_spin_witnesses: Tuple[int, ...]

    def to_canonical_dict(self) -> dict:
        return {
            "left_relation_witness": self.left_relation_witness,
            "relation_spin_witnesses": self.relation_spin_witnesses,
            "right_relation_witness": self.right_relation_witness,
            "symmetry_witness": self.symmetry_witness,
        }


@dataclass(frozen=True)
class MetricValidationCertificate:
    descent: MetricDescentCertificate
    ambient_radical: FiniteSubgroup
    nondegenerate: bool

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_radical": self.ambient_radical,
            "descent": self.descent,
            "nondegenerate": self.nondegenerate,
        }


@dataclass(frozen=True)
class FiniteMetricGroup:
    """A finite Abelian group with exact monodromy and topological spin.

    Exponents are in ``Z / phase_modulus``: exponent ``k`` denotes the phase
    ``exp(2*pi*i*k/phase_modulus)``.  ``braiding_matrix`` is symmetric modulo
    the phase modulus and ``generator_spins`` specifies ``q(e_i)``.  The
    quadratic refinement is evaluated without floating point arithmetic.
    """

    group: FiniteAbelianGroup
    phase_modulus: int
    braiding_matrix: SparseIntMatrix
    generator_spins: Tuple[int, ...]
    certificate: MetricValidationCertificate

    SCHEMA_ID = "mobility_toolkit.finite_metric_group.v1"

    @classmethod
    def create(
        cls,
        group: FiniteAbelianGroup,
        phase_modulus: int,
        braiding_matrix: SparseIntMatrix,
        generator_spins: Sequence[int],
        backend: FiniteIntegerBackend,
        require_nondegenerate: bool = True,
    ) -> "FiniteMetricGroup":
        phase_modulus = _plain_int(phase_modulus, "phase_modulus")
        if phase_modulus <= 1:
            raise ValueError("phase_modulus must be greater than one")
        rank = group.presentation_rank
        if (braiding_matrix.nrows, braiding_matrix.ncols) != (rank, rank):
            raise ValueError("braiding matrix has the wrong shape")
        spins = tuple(
            _plain_int(value, "generator spin") % phase_modulus
            for value in generator_spins
        )
        if len(spins) != rank:
            raise ValueError("generator_spins must match the presentation rank")
        pairing = _matrix_mod(braiding_matrix, phase_modulus)
        relations = group.relation_lattice_basis
        symmetry = SparseIntMatrix(
            rank,
            rank,
            tuple(pairing.entries) + tuple(pairing.transpose().negate().entries),
        )
        descent = MetricDescentCertificate(
            left_relation_witness=_divide_entries(
                relations.transpose().matmul(pairing),
                phase_modulus,
                "braiding does not descend in its left argument",
            ),
            right_relation_witness=_divide_entries(
                pairing.matmul(relations),
                phase_modulus,
                "braiding does not descend in its right argument",
            ),
            symmetry_witness=_divide_entries(
                symmetry,
                phase_modulus,
                "anyon monodromy pairing is not symmetric",
            ),
            relation_spin_witnesses=tuple(
                _raw_spin(pairing, spins, _column(relations, column)) // phase_modulus
                for column in range(relations.ncols)
            ),
        )
        for column in range(relations.ncols):
            raw = _raw_spin(pairing, spins, _column(relations, column))
            if raw % phase_modulus:
                raise ValueError("quadratic refinement does not descend through relations")

        provisional = cls(
            group,
            phase_modulus,
            pairing,
            spins,
            MetricValidationCertificate(
                descent,
                group.trivial_subgroup(backend),
                False,
            ),
        )
        radical = _orthogonal_complement(
            group,
            pairing,
            phase_modulus,
            group.whole_subgroup(backend),
            backend,
        )
        nondegenerate = radical.order(backend) == 1
        result = cls(
            group,
            phase_modulus,
            pairing,
            spins,
            MetricValidationCertificate(descent, radical, nondegenerate),
        )
        result.verify_certificate(backend)
        if require_nondegenerate and not nondegenerate:
            raise ValueError("braiding is degenerate, so the data is not a metric group")
        return result

    def braiding_exponent(self, left: Sequence[int], right: Sequence[int]) -> int:
        self._validate_vector(left)
        self._validate_vector(right)
        return _raw_braiding(self.braiding_matrix, left, right) % self.phase_modulus

    def spin_exponent(self, anyon: Sequence[int]) -> int:
        self._validate_vector(anyon)
        return _raw_spin(
            self.braiding_matrix, self.generator_spins, anyon
        ) % self.phase_modulus

    def orthogonal_complement(
        self, subgroup: FiniteSubgroup, backend: FiniteIntegerBackend
    ) -> FiniteSubgroup:
        return _orthogonal_complement(
            self.group,
            self.braiding_matrix,
            self.phase_modulus,
            subgroup,
            backend,
        )

    def as_alternating_pairing(self) -> PairedFiniteAbelianGroup:
        """Return the Pauli-style pairing only when the metric form is alternating.

        Most metric groups do not satisfy this stronger condition.  This method
        is an explicit, checked bridge rather than an identification of symmetric
        anyon braiding with an alternating commutator.
        """

        return PairedFiniteAbelianGroup.create(
            self.group, self.phase_modulus, self.braiding_matrix
        )

    def verify_certificate(self, backend: FiniteIntegerBackend) -> None:
        relations = self.group.relation_lattice_basis
        descent = self.certificate.descent
        if relations.transpose().matmul(self.braiding_matrix) != _scaled(
            descent.left_relation_witness, self.phase_modulus
        ):
            raise ArithmeticError("left braiding descent certificate is invalid")
        if self.braiding_matrix.matmul(relations) != _scaled(
            descent.right_relation_witness, self.phase_modulus
        ):
            raise ArithmeticError("right braiding descent certificate is invalid")
        difference = SparseIntMatrix(
            self.group.presentation_rank,
            self.group.presentation_rank,
            tuple(self.braiding_matrix.entries)
            + tuple(self.braiding_matrix.transpose().negate().entries),
        )
        if difference != _scaled(descent.symmetry_witness, self.phase_modulus):
            raise ArithmeticError("braiding symmetry certificate is invalid")
        expected_spin_witnesses = []
        for column in range(relations.ncols):
            raw = _raw_spin(
                self.braiding_matrix,
                self.generator_spins,
                _column(relations, column),
            )
            if raw % self.phase_modulus:
                raise ArithmeticError("quadratic descent certificate is invalid")
            expected_spin_witnesses.append(raw // self.phase_modulus)
        if tuple(expected_spin_witnesses) != descent.relation_spin_witnesses:
            raise ArithmeticError("relation spin witnesses are invalid")
        radical = self.orthogonal_complement(
            self.group.whole_subgroup(backend), backend
        )
        if radical != self.certificate.ambient_radical:
            raise ArithmeticError("ambient radical certificate is invalid")
        if (radical.order(backend) == 1) != self.certificate.nondegenerate:
            raise ArithmeticError("nondegeneracy certificate is invalid")

    def _validate_vector(self, vector: Sequence[int]) -> None:
        if len(vector) != self.group.presentation_rank:
            raise ValueError("anyon representative has the wrong rank")
        for value in vector:
            _plain_int(value, "anyon coordinate")

    def to_canonical_dict(self) -> dict:
        return {
            "braiding_matrix": self.braiding_matrix,
            "certificate": self.certificate,
            "generator_spins": self.generator_spins,
            "group": self.group,
            "phase_modulus": self.phase_modulus,
            "schema": self.SCHEMA_ID,
        }


def _scaled(matrix: SparseIntMatrix, factor: int) -> SparseIntMatrix:
    return SparseIntMatrix(
        matrix.nrows,
        matrix.ncols,
        tuple((row, column, factor * value) for row, column, value in matrix.entries),
    )


__all__ = [
    "FiniteMetricGroup",
    "MetricDescentCertificate",
    "MetricValidationCertificate",
]
