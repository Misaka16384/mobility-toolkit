r"""Published secondary-operator calibration for half-space boundary modules.

This module freezes Example 45, equations (114)--(118), of Ruba--Yang,
``Witt Groups and Bulk-Boundary Correspondence for Stabilizer States``
(arXiv:2509.10418).  The example is intentionally kept separate from the
generic primary compiler: it proves that the primary image can be a proper
submodule of the full boundary module.

Over

``A = F_2[x^+-1]`` and ``R = A[n^+-1]``,

the primary generators are

``e1 = (1+x, 0)`` and ``e2 = ((1+x)n, 1)``.

The full boundary module contains the secondary generator
``e1_prime = (1, 0)`` with ``(1+x)e1_prime=e1``.  The primary pairing has
off-diagonal entry ``1+x^-1`` whereas the full pairing is unimodular.
No generic closure algorithm is inferred from this one published example.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

from mobility_toolkit.boundary_halfspace.boundary_module import (
    TangentLaurentPolynomial,
    TangentLaurentTerm,
    boundary_pairing,
)
from mobility_toolkit.boundary_halfspace.geometry import PrimitiveNormal
from mobility_toolkit.boundary_halfspace.presentation import (
    TangentDepthPolynomial,
    TangentDepthTerm,
)
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)


PolynomialColumn = Tuple[TangentDepthPolynomial, ...]


def _poly(
    normal: PrimitiveNormal,
    terms: Sequence[Tuple[int, Tuple[int, ...], int]],
) -> TangentDepthPolynomial:
    return TangentDepthPolynomial(
        2,
        normal,
        (),
        tuple(
            TangentDepthTerm(coefficient, tangent, depth, ())
            for coefficient, tangent, depth in terms
        ),
    )


def _add_polynomials(
    left: TangentDepthPolynomial,
    right: TangentDepthPolynomial,
) -> TangentDepthPolynomial:
    if left.coefficient_modulus != right.coefficient_modulus:
        raise ValueError("polynomial coefficient moduli differ")
    if left.normal != right.normal:
        raise ValueError("polynomial half-space normals differ")
    return TangentDepthPolynomial(
        left.coefficient_modulus,
        left.normal,
        left.torsion_invariants,
        left.terms + right.terms,
    )


def _multiply_by_one_plus_x(
    polynomial: TangentDepthPolynomial,
) -> TangentDepthPolynomial:
    shifted = TangentDepthPolynomial(
        polynomial.coefficient_modulus,
        polynomial.normal,
        polynomial.torsion_invariants,
        tuple(
            TangentDepthTerm(
                term.coefficient,
                (term.tangent_exponents[0] + 1,),
                term.depth,
                term.torsion_exponents,
            )
            for term in polynomial.terms
        ),
    )
    return _add_polynomials(polynomial, shifted)


def _shift_and_project_nonnegative(
    column: PolynomialColumn,
    shift: int,
) -> PolynomialColumn:
    return tuple(
        TangentDepthPolynomial(
            entry.coefficient_modulus,
            entry.normal,
            entry.torsion_invariants,
            tuple(
                TangentDepthTerm(
                    term.coefficient,
                    term.tangent_exponents,
                    term.depth + shift,
                    term.torsion_exponents,
                )
                for term in entry.terms
                if term.depth + shift >= 0
            ),
        )
        for entry in column
    )


def _gf2_rank(rows: Iterable[Sequence[int]], width: int) -> int:
    packed = [
        sum((int(value) & 1) << column for column, value in enumerate(row))
        for row in rows
    ]
    rank = 0
    for column in range(width):
        pivot = next(
            (
                row
                for row in range(rank, len(packed))
                if (packed[row] >> column) & 1
            ),
            None,
        )
        if pivot is None:
            continue
        packed[rank], packed[pivot] = packed[pivot], packed[rank]
        for row in range(len(packed)):
            if row != rank and ((packed[row] >> column) & 1):
                packed[row] ^= packed[rank]
        rank += 1
    return rank


@dataclass(frozen=True)
class SecondaryExampleFiniteCheck:
    tangent_period: int
    primary_embedding_rank: int
    secondary_quotient_dimension: int
    primary_pairing_rank: int
    primary_radical_dimension: int
    full_pairing_rank: int
    full_radical_dimension: int

    SCHEMA_ID = "mobility_toolkit.secondary_example_finite_check.v1"

    @property
    def verified(self) -> bool:
        period = self.tangent_period
        return (
            self.primary_embedding_rank == 2 * period - 1
            and self.secondary_quotient_dimension == 1
            and self.primary_pairing_rank == 2 * period - 2
            and self.primary_radical_dimension == 2
            and self.full_pairing_rank == 2 * period
            and self.full_radical_dimension == 0
        )

    def to_canonical_dict(self) -> dict:
        return {
            "full_pairing_rank": self.full_pairing_rank,
            "full_radical_dimension": self.full_radical_dimension,
            "primary_embedding_rank": self.primary_embedding_rank,
            "primary_pairing_rank": self.primary_pairing_rank,
            "primary_radical_dimension": self.primary_radical_dimension,
            "schema": self.SCHEMA_ID,
            "secondary_quotient_dimension": self.secondary_quotient_dimension,
            "tangent_period": self.tangent_period,
            "verified": self.verified,
        }


def verify_secondary_example_finite(
    tangent_period: int,
) -> SecondaryExampleFiniteCheck:
    """Evaluate the published modules on ``x^L=1`` over ``F_2``."""

    if (
        isinstance(tangent_period, bool)
        or not isinstance(tangent_period, int)
        or tangent_period < 2
    ):
        raise ValueError("tangent_period must be an integer at least two")
    period = tangent_period
    one_plus_shift = tuple(
        tuple(
            int(column == row) ^ int(column == ((row + 1) % period))
            for column in range(period)
        )
        for row in range(period)
    )
    zero = tuple(tuple(0 for _ in range(period)) for _ in range(period))
    identity = tuple(
        tuple(int(row == column) for column in range(period))
        for row in range(period)
    )
    primary_embedding = tuple(
        one_plus_shift[row] + zero[row] for row in range(period)
    ) + tuple(zero[row] + identity[row] for row in range(period))
    primary_pairing = tuple(
        zero[row] + one_plus_shift[row] for row in range(period)
    ) + tuple(
        tuple(
            one_plus_shift[column][row] for column in range(period)
        )
        + zero[row]
        for row in range(period)
    )
    full_pairing = tuple(
        zero[row] + identity[row] for row in range(period)
    ) + tuple(identity[row] + zero[row] for row in range(period))
    embedding_rank = _gf2_rank(primary_embedding, 2 * period)
    primary_rank = _gf2_rank(primary_pairing, 2 * period)
    full_rank = _gf2_rank(full_pairing, 2 * period)
    check = SecondaryExampleFiniteCheck(
        tangent_period=period,
        primary_embedding_rank=embedding_rank,
        secondary_quotient_dimension=2 * period - embedding_rank,
        primary_pairing_rank=primary_rank,
        primary_radical_dimension=2 * period - primary_rank,
        full_pairing_rank=full_rank,
        full_radical_dimension=2 * period - full_rank,
    )
    if not check.verified:
        raise ArithmeticError("published secondary finite-period check failed")
    return check


@dataclass(frozen=True)
class RubaYangSecondaryExampleCertificate:
    source_arxiv: str
    source_example: str
    source_equations: Tuple[int, ...]
    literal_bulk_generator: Tuple[str, ...]
    primary_relation_verified: bool
    primary_pairing_verified: bool
    secondary_relation_verified: bool
    full_pairing_unimodular_verified: bool
    finite_checks: Tuple[SecondaryExampleFiniteCheck, ...]

    SCHEMA_ID = "mobility_toolkit.ruba_yang_secondary_example_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.source_arxiv == "2509.10418"
            and self.source_example == "Example 45"
            and self.source_equations == (114, 115, 116, 117, 118)
            and self.primary_relation_verified
            and self.primary_pairing_verified
            and self.secondary_relation_verified
            and self.full_pairing_unimodular_verified
            and all(check.verified for check in self.finite_checks)
        )

    def to_canonical_dict(self) -> dict:
        return {
            "finite_checks": self.finite_checks,
            "full_pairing_unimodular_verified":
                self.full_pairing_unimodular_verified,
            "literal_bulk_generator": self.literal_bulk_generator,
            "primary_pairing_verified": self.primary_pairing_verified,
            "primary_relation_verified": self.primary_relation_verified,
            "schema": self.SCHEMA_ID,
            "secondary_relation_verified": self.secondary_relation_verified,
            "source_arxiv": self.source_arxiv,
            "source_equations": self.source_equations,
            "source_example": self.source_example,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class RubaYangSecondaryBoundaryExample:
    bulk_generator: PolynomialColumn
    primary_generators: Tuple[PolynomialColumn, ...]
    secondary_generator: PolynomialColumn
    full_generators: Tuple[PolynomialColumn, ...]
    primary_pairing: Tuple[Tuple[TangentLaurentPolynomial, ...], ...]
    full_pairing: Tuple[Tuple[TangentLaurentPolynomial, ...], ...]
    secondary_quotient_annihilator: TangentLaurentPolynomial
    primary_boundary_charge_annihilator: TangentLaurentPolynomial
    primary_boundary_charge_multiplicity: int
    full_boundary_charge_invariant_factors: Tuple[int, ...]
    certificate: RubaYangSecondaryExampleCertificate

    SCHEMA_ID = "mobility_toolkit.ruba_yang_secondary_boundary_example.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_generator": self.bulk_generator,
            "certificate": self.certificate,
            "full_boundary_charge_invariant_factors":
                self.full_boundary_charge_invariant_factors,
            "full_generators": self.full_generators,
            "full_pairing": self.full_pairing,
            "primary_boundary_charge_annihilator":
                self.primary_boundary_charge_annihilator,
            "primary_boundary_charge_multiplicity":
                self.primary_boundary_charge_multiplicity,
            "primary_generators": self.primary_generators,
            "primary_pairing": self.primary_pairing,
            "schema": self.SCHEMA_ID,
            "secondary_generator": self.secondary_generator,
            "secondary_quotient_annihilator":
                self.secondary_quotient_annihilator,
        }


def ruba_yang_secondary_boundary_example() -> ComputationResult:
    """Return the exact published primary/secondary contrast in Example 45."""

    normal = PrimitiveNormal.from_integer((0, 1))
    zero = _poly(normal, ())
    bulk = (
        _poly(
            normal,
            (
                (1, (0,), -1),
                (1, (-1,), -1),
                (1, (0,), 1),
                (1, (1,), 1),
            ),
        ),
        _poly(normal, ((1, (0,), 0),)),
    )
    e1 = (
        _poly(normal, ((1, (0,), 0), (1, (1,), 0))),
        zero,
    )
    e2 = (
        _poly(normal, ((1, (0,), 1), (1, (1,), 1))),
        _poly(normal, ((1, (0,), 0),)),
    )
    e1_prime = (
        _poly(normal, ((1, (0,), 0),)),
        zero,
    )
    primary = (e1, e2)
    full = (e1_prime, e2)
    primary_pairing = tuple(
        tuple(boundary_pairing(left, right) for right in primary)
        for left in primary
    )
    full_pairing = tuple(
        tuple(boundary_pairing(left, right) for right in full)
        for left in full
    )
    one_plus_x = TangentLaurentPolynomial(
        2,
        1,
        (
            TangentLaurentTerm(1, (0,)),
            TangentLaurentTerm(1, (1,)),
        ),
    )
    one_plus_x_inverse = one_plus_x.involution()
    one = TangentLaurentPolynomial(
        2,
        1,
        (TangentLaurentTerm(1, (0,)),),
    )
    relation_verified = tuple(
        _multiply_by_one_plus_x(entry) for entry in e1_prime
    ) == e1
    primary_projection_verified = (
        _shift_and_project_nonnegative(bulk, -1) == e1
        and _shift_and_project_nonnegative(bulk, 0) == e2
    )
    primary_pairing_verified = (
        primary_pairing[0][0].is_zero
        and primary_pairing[1][1].is_zero
        and primary_pairing[0][1] == one_plus_x_inverse
        and primary_pairing[1][0] == one_plus_x
    )
    full_pairing_verified = (
        full_pairing[0][0].is_zero
        and full_pairing[1][1].is_zero
        and full_pairing[0][1] == one
        and full_pairing[1][0] == one
    )
    finite_checks = tuple(
        verify_secondary_example_finite(period)
        for period in range(2, 8)
    )
    certificate = RubaYangSecondaryExampleCertificate(
        source_arxiv="2509.10418",
        source_example="Example 45",
        source_equations=(114, 115, 116, 117, 118),
        literal_bulk_generator=(
            "(1+x^-1)n^-1 + (1+x)n",
            "1",
        ),
        primary_relation_verified=primary_projection_verified,
        primary_pairing_verified=primary_pairing_verified,
        secondary_relation_verified=relation_verified,
        full_pairing_unimodular_verified=full_pairing_verified,
        finite_checks=finite_checks,
    )
    if not certificate.verified:
        raise ArithmeticError("published secondary-operator certificate failed")
    value = RubaYangSecondaryBoundaryExample(
        bulk_generator=bulk,
        primary_generators=primary,
        secondary_generator=e1_prime,
        full_generators=full,
        primary_pairing=primary_pairing,
        full_pairing=full_pairing,
        secondary_quotient_annihilator=one_plus_x,
        primary_boundary_charge_annihilator=one_plus_x,
        primary_boundary_charge_multiplicity=2,
        full_boundary_charge_invariant_factors=(),
        certificate=certificate,
    )
    return ComputationResult(
        operation="halfspace.ruba_yang_secondary_boundary_example",
        input_data={
            "arxiv": "2509.10418",
            "example": 45,
            "equations": (114, 115, 116, 117, 118),
        },
        value=value,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=(
            "the published F2 Laurent presentation in Example 45",
            "standard half-space in the second lattice coordinate",
        ),
        theorem_scope=(
            "Exact only for Ruba--Yang Example 45.  It certifies a proper "
            "primary submodule, one secondary saturation generator, and the "
            "published change from a non-unimodular to a standard symplectic "
            "pairing; it is not a generic secondary-closure algorithm."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            ("secondary_relation", "(1+x)e1_prime=e1"),
            ("primary_boundary_charge_module", "(A/(1+x))^2"),
            ("full_boundary_charge_module", "0"),
            ("finite_periods_checked", tuple(range(2, 8))),
        ),
        backend_provenance=BackendProvenance(
            backend="internal-exact-symbolic+gf2",
            algorithm="published-example-literal-replay",
            version="1",
            parameters=(("source_arxiv", "2509.10418"),),
        ),
        warnings=(
            "The full module is not obtained by setting the normal variable to one.",
            "The example demonstrates that primary and full boundary modules can differ.",
        ),
    )


__all__ = [
    "RubaYangSecondaryBoundaryExample",
    "RubaYangSecondaryExampleCertificate",
    "SecondaryExampleFiniteCheck",
    "ruba_yang_secondary_boundary_example",
    "verify_secondary_example_finite",
]
