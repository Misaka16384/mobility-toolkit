r"""Canonical Laurent data in coordinates adapted to a lattice half-space.

This module performs the exact change of lattice basis needed before any
one-sided module calculation.  It deliberately stops short of claiming that
clearing the lowest normal depth computes ``L \cap P_H``: cancellations
between stabilizer columns require a saturation/intersection calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple, Union

from mobility_toolkit.boundary_halfspace.geometry import (
    PrimitiveNormal,
    UnimodularBasisChange,
)
from mobility_toolkit.core.laurent import LaurentPolynomial


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@dataclass(frozen=True, order=True)
class TangentDepthTerm:
    """One group-ring term in adapted ``(tangent, normal-depth)`` coordinates."""

    coefficient: int
    tangent_exponents: Tuple[int, ...]
    depth: int
    torsion_exponents: Tuple[int, ...] = ()

    SCHEMA_ID = "mobility_toolkit.tangent_depth_term.v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "coefficient",
            _integer(self.coefficient, "coefficient"),
        )
        object.__setattr__(
            self,
            "tangent_exponents",
            tuple(_integer(value, "tangent exponent") for value in self.tangent_exponents),
        )
        object.__setattr__(self, "depth", _integer(self.depth, "depth"))
        object.__setattr__(
            self,
            "torsion_exponents",
            tuple(_integer(value, "torsion exponent") for value in self.torsion_exponents),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient": self.coefficient,
            "depth": self.depth,
            "schema": self.SCHEMA_ID,
            "tangent_exponents": self.tangent_exponents,
            "torsion_exponents": self.torsion_exponents,
        }


@dataclass(frozen=True)
class TangentDepthPolynomial:
    """A canonical group-ring polynomial split into tangent and depth degrees."""

    coefficient_modulus: int
    normal: PrimitiveNormal
    torsion_invariants: Tuple[int, ...]
    terms: Tuple[TangentDepthTerm, ...] = ()

    SCHEMA_ID = "mobility_toolkit.tangent_depth_polynomial.v1"

    def __post_init__(self) -> None:
        modulus = _integer(self.coefficient_modulus, "coefficient modulus")
        if modulus <= 1:
            raise ValueError("coefficient modulus must be greater than one")
        torsion = tuple(
            _integer(value, "torsion invariant") for value in self.torsion_invariants
        )
        if any(value <= 1 for value in torsion):
            raise ValueError("torsion invariants must be greater than one")
        combined = {}
        tangent_rank = self.normal.dimension - 1
        for term in tuple(self.terms):
            if not isinstance(term, TangentDepthTerm):
                raise TypeError("terms must be TangentDepthTerm objects")
            if len(term.tangent_exponents) != tangent_rank:
                raise ValueError("term tangent rank does not match the normal")
            if len(term.torsion_exponents) != len(torsion):
                raise ValueError("term torsion rank does not match the translation group")
            torsion_exponents = tuple(
                exponent % order
                for exponent, order in zip(term.torsion_exponents, torsion)
            )
            key = (term.tangent_exponents, term.depth, torsion_exponents)
            combined[key] = (combined.get(key, 0) + term.coefficient) % modulus
        normalized = tuple(
            TangentDepthTerm(coefficient, tangent, depth, torsion_exponents)
            for (tangent, depth, torsion_exponents), coefficient in sorted(combined.items())
            if coefficient
        )
        object.__setattr__(self, "coefficient_modulus", modulus)
        object.__setattr__(self, "torsion_invariants", torsion)
        object.__setattr__(self, "terms", normalized)

    @property
    def tangent_rank(self) -> int:
        return self.normal.dimension - 1

    @property
    def is_zero(self) -> bool:
        return not self.terms

    @property
    def depth_interval(self) -> Tuple[int, int]:
        if not self.terms:
            return (0, 0)
        depths = tuple(term.depth for term in self.terms)
        return min(depths), max(depths)

    def shift_depth(self, amount: int) -> "TangentDepthPolynomial":
        shift = _integer(amount, "depth shift")
        return TangentDepthPolynomial(
            self.coefficient_modulus,
            self.normal,
            self.torsion_invariants,
            tuple(
                TangentDepthTerm(
                    term.coefficient,
                    term.tangent_exponents,
                    term.depth + shift,
                    term.torsion_exponents,
                )
                for term in self.terms
            ),
        )

    def involution(self) -> "TangentDepthPolynomial":
        return TangentDepthPolynomial(
            self.coefficient_modulus,
            self.normal,
            self.torsion_invariants,
            tuple(
                TangentDepthTerm(
                    term.coefficient,
                    tuple(-value for value in term.tangent_exponents),
                    -term.depth,
                    tuple(-value for value in term.torsion_exponents),
                )
                for term in self.terms
            ),
        )

    def coefficient_at_depth(self, depth: int) -> Tuple[TangentDepthTerm, ...]:
        requested = _integer(depth, "depth")
        return tuple(term for term in self.terms if term.depth == requested)

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_modulus": self.coefficient_modulus,
            "depth_interval": self.depth_interval,
            "normal": self.normal,
            "schema": self.SCHEMA_ID,
            "terms": self.terms,
            "torsion_invariants": self.torsion_invariants,
        }


@dataclass(frozen=True)
class OneSidedClearing:
    """A monomial depth shift which puts one polynomial in nonnegative depth."""

    original: TangentDepthPolynomial
    depth_shift: int
    cleared: TangentDepthPolynomial

    SCHEMA_ID = "mobility_toolkit.one_sided_clearing.v1"

    def __post_init__(self) -> None:
        if self.original.normal != self.cleared.normal:
            raise ValueError("clearing changed the half-space normal")
        if self.original.coefficient_modulus != self.cleared.coefficient_modulus:
            raise ValueError("clearing changed the coefficient modulus")
        if self.cleared != self.original.shift_depth(self.depth_shift):
            raise ValueError("cleared polynomial does not match its depth shift")
        if any(term.depth < 0 for term in self.cleared.terms):
            raise ValueError("cleared polynomial still has negative depth")

    def to_canonical_dict(self) -> dict:
        return {
            "cleared": self.cleared,
            "depth_shift": self.depth_shift,
            "original": self.original,
            "schema": self.SCHEMA_ID,
        }


def adapt_laurent_polynomial(
    polynomial: LaurentPolynomial,
    normal_or_basis: Union[
        Sequence[int], PrimitiveNormal, UnimodularBasisChange
    ],
) -> TangentDepthPolynomial:
    """Rewrite a Laurent AST using an exact half-space-adapted lattice basis."""

    if not isinstance(polynomial, LaurentPolynomial):
        raise TypeError("polynomial must be a LaurentPolynomial")
    if isinstance(normal_or_basis, UnimodularBasisChange):
        basis = normal_or_basis
    elif isinstance(normal_or_basis, PrimitiveNormal):
        basis = UnimodularBasisChange.adapted_to(normal_or_basis)
    else:
        basis = UnimodularBasisChange.adapted_to(
            PrimitiveNormal.from_integer(tuple(normal_or_basis))
        )
    if polynomial.translation_group.free_rank != basis.normal.dimension:
        raise ValueError("polynomial free rank and half-space dimension differ")
    terms = []
    for term in polynomial.terms:
        coordinates = basis.to_boundary_coordinates(term.free_exponents)
        terms.append(
            TangentDepthTerm(
                term.coefficient,
                coordinates[:-1],
                coordinates[-1],
                term.torsion_exponents,
            )
        )
    return TangentDepthPolynomial(
        polynomial.coefficient_modulus,
        basis.normal,
        polynomial.translation_group.torsion_invariants,
        tuple(terms),
    )


def clear_negative_depth(polynomial: TangentDepthPolynomial) -> OneSidedClearing:
    """Clear negative normal powers by the smallest possible monomial shift.

    This is a representation operation only.  For a stabilizer *module*, the
    intersection with the one-sided module is a saturation and can contain
    cancellations not visible column-by-column.
    """

    if not isinstance(polynomial, TangentDepthPolynomial):
        raise TypeError("polynomial must be a TangentDepthPolynomial")
    minimum, _ = polynomial.depth_interval
    shift = max(0, -minimum)
    return OneSidedClearing(polynomial, shift, polynomial.shift_depth(shift))


__all__ = [
    "OneSidedClearing",
    "TangentDepthPolynomial",
    "TangentDepthTerm",
    "adapt_laurent_polynomial",
    "clear_negative_depth",
]
