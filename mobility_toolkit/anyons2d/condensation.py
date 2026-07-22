"""Exact subgroup tests for abstract Abelian anyon condensation data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite import (
    FiniteIntegerBackend,
    FiniteSubgroup,
    MembershipWitness,
)

from mobility_toolkit.anyons2d.metric import FiniteMetricGroup


def _column(matrix: SparseIntMatrix, index: int) -> Tuple[int, ...]:
    return tuple(row[index] for row in matrix.to_rows())


@dataclass(frozen=True)
class CondensationCertificate:
    """Certificate for a proposed condensate in an abstract metric group.

    ``bosonic`` means the quadratic form vanishes on the entire subgroup.
    ``lagrangian`` additionally means the subgroup equals its exact braiding
    orthogonal complement.  Neither field asserts a local Hamiltonian completion.
    """

    subgroup: FiniteSubgroup
    restricted_braiding_matrix: SparseIntMatrix
    generator_spin_exponents: Tuple[int, ...]
    orthogonal_complement: FiniteSubgroup
    braiding_isotropic: bool
    bosonic: bool
    lagrangian: bool
    local_completion_constructed: bool = False

    SCHEMA_ID = "mobility_toolkit.anyon_condensation_certificate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "bosonic": self.bosonic,
            "braiding_isotropic": self.braiding_isotropic,
            "generator_spin_exponents": self.generator_spin_exponents,
            "lagrangian": self.lagrangian,
            "local_completion_constructed": self.local_completion_constructed,
            "orthogonal_complement": self.orthogonal_complement,
            "restricted_braiding_matrix": self.restricted_braiding_matrix,
            "schema": self.SCHEMA_ID,
            "subgroup": self.subgroup,
        }


def test_condensation(
    metric: FiniteMetricGroup,
    subgroup: FiniteSubgroup,
    backend: FiniteIntegerBackend,
) -> CondensationCertificate:
    """Validate isotropy, bosonicity and the Lagrangian condition exactly."""

    if subgroup.ambient != metric.group:
        raise ValueError("candidate condensate belongs to a different anyon group")
    lifts = subgroup.preimage_lattice_basis
    restricted = lifts.transpose().matmul(metric.braiding_matrix).matmul(lifts)
    restricted = SparseIntMatrix(
        restricted.nrows,
        restricted.ncols,
        tuple(
            (row, column, value % metric.phase_modulus)
            for row, column, value in restricted.entries
        ),
    )
    spins = tuple(
        metric.spin_exponent(_column(lifts, column))
        for column in range(lifts.ncols)
    )
    isotropic = not restricted.entries
    bosonic = isotropic and all(value == 0 for value in spins)
    orthogonal = metric.orthogonal_complement(subgroup, backend)
    equal_to_orthogonal = subgroup.contains_subgroup(
        orthogonal, backend
    ) and orthogonal.contains_subgroup(subgroup, backend)
    lagrangian = bosonic and equal_to_orthogonal
    result = CondensationCertificate(
        subgroup=subgroup,
        restricted_braiding_matrix=restricted,
        generator_spin_exponents=spins,
        orthogonal_complement=orthogonal,
        braiding_isotropic=isotropic,
        bosonic=bosonic,
        lagrangian=lagrangian,
    )
    verify_condensation_certificate(metric, result, backend)
    return result


def verify_condensation_certificate(
    metric: FiniteMetricGroup,
    certificate: CondensationCertificate,
    backend: FiniteIntegerBackend,
) -> None:
    recomputed = test_condensation_unverified(metric, certificate.subgroup, backend)
    if recomputed != certificate:
        raise ArithmeticError("anyon condensation certificate is invalid")


def test_condensation_unverified(
    metric: FiniteMetricGroup,
    subgroup: FiniteSubgroup,
    backend: FiniteIntegerBackend,
) -> CondensationCertificate:
    """Internal non-recursive implementation used by certificate replay."""

    if subgroup.ambient != metric.group:
        raise ValueError("candidate condensate belongs to a different anyon group")
    lifts = subgroup.preimage_lattice_basis
    restricted = lifts.transpose().matmul(metric.braiding_matrix).matmul(lifts)
    restricted = SparseIntMatrix(
        restricted.nrows,
        restricted.ncols,
        tuple(
            (row, column, value % metric.phase_modulus)
            for row, column, value in restricted.entries
        ),
    )
    spins = tuple(
        metric.spin_exponent(_column(lifts, column))
        for column in range(lifts.ncols)
    )
    isotropic = not restricted.entries
    bosonic = isotropic and all(value == 0 for value in spins)
    orthogonal = metric.orthogonal_complement(subgroup, backend)
    equal = subgroup.contains_subgroup(orthogonal, backend) and orthogonal.contains_subgroup(
        subgroup, backend
    )
    return CondensationCertificate(
        subgroup,
        restricted,
        spins,
        orthogonal,
        isotropic,
        bosonic,
        bosonic and equal,
    )


@dataclass(frozen=True)
class AnyonTerminationCertificate:
    anyon_representative: Tuple[int, ...]
    condensate: CondensationCertificate
    membership_witness: MembershipWitness
    terminates_algebraically: bool = True
    local_completion_constructed: bool = False

    SCHEMA_ID = "mobility_toolkit.anyon_termination_certificate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "anyon_representative": self.anyon_representative,
            "condensate": self.condensate,
            "local_completion_constructed": self.local_completion_constructed,
            "membership_witness": self.membership_witness,
            "schema": self.SCHEMA_ID,
            "terminates_algebraically": self.terminates_algebraically,
        }


def anyon_termination_certificate(
    metric: FiniteMetricGroup,
    condensate: FiniteSubgroup,
    anyon: Sequence[int],
    backend: FiniteIntegerBackend,
) -> AnyonTerminationCertificate:
    """Prove algebraic termination by membership in a bosonic condensate.

    Absence of a returned certificate means only that this proposed condensate
    does not absorb the anyon; it is not a no-go theorem for every boundary.
    """

    vector = tuple(anyon)
    metric.spin_exponent(vector)  # validates shape and integer coordinates
    condensation = test_condensation(metric, condensate, backend)
    if not condensation.bosonic:
        raise ValueError("termination requires a bosonic condensate subgroup")
    witness = condensate.membership_witness(vector, backend)
    if witness is None:
        raise ValueError("anyon is not a member of the proposed condensate")
    return AnyonTerminationCertificate(vector, condensation, witness)


def can_terminate(
    metric: FiniteMetricGroup,
    condensate: FiniteSubgroup,
    anyon: Sequence[int],
    backend: FiniteIntegerBackend,
) -> bool:
    condensation = test_condensation(metric, condensate, backend)
    if not condensation.bosonic:
        return False
    return condensate.contains(tuple(anyon), backend)


__all__ = [
    "AnyonTerminationCertificate",
    "CondensationCertificate",
    "anyon_termination_certificate",
    "can_terminate",
    "test_condensation",
    "verify_condensation_certificate",
]
