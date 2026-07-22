"""Canonical group-ring and Laurent-polynomial value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@dataclass(frozen=True)
class TranslationGroup:
    """A finitely generated abelian translation group.

    Most lattice models use only the free part ``Z^D``. Torsion factors are
    represented now so finite periodic directions do not require a future
    schema break.
    """

    free_rank: int
    torsion_invariants: Tuple[int, ...] = ()
    free_generator_names: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.translation_group.v1"

    def __post_init__(self) -> None:
        free_rank = _integer(self.free_rank, "free_rank")
        if free_rank < 0:
            raise ValueError("free_rank must be nonnegative")
        torsion = tuple(_integer(value, "torsion invariant") for value in self.torsion_invariants)
        if any(value <= 1 for value in torsion):
            raise ValueError("torsion invariants must be greater than one")
        if any(right % left != 0 for left, right in zip(torsion, torsion[1:])):
            raise ValueError("torsion invariants must form a divisibility chain")
        names = tuple(self.free_generator_names)
        if names and len(names) != free_rank:
            raise ValueError("free_generator_names must be empty or match free_rank")
        if not names:
            names = tuple(f"x{index + 1}" for index in range(free_rank))
        if any(not isinstance(name, str) or not name for name in names):
            raise ValueError("translation generator names must be nonempty strings")
        if len(set(names)) != len(names):
            raise ValueError("translation generator names must be unique")
        object.__setattr__(self, "torsion_invariants", torsion)
        object.__setattr__(self, "free_generator_names", names)

    def to_canonical_dict(self) -> dict:
        return {
            "free_generator_names": self.free_generator_names,
            "free_rank": self.free_rank,
            "schema": self.SCHEMA_ID,
            "torsion_invariants": self.torsion_invariants,
        }


@dataclass(frozen=True, order=True)
class LaurentTerm:
    coefficient: int
    free_exponents: Tuple[int, ...]
    torsion_exponents: Tuple[int, ...] = ()

    SCHEMA_ID = "mobility_toolkit.laurent_term.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "coefficient", _integer(self.coefficient, "coefficient"))
        object.__setattr__(
            self,
            "free_exponents",
            tuple(_integer(value, "free exponent") for value in self.free_exponents),
        )
        object.__setattr__(
            self,
            "torsion_exponents",
            tuple(_integer(value, "torsion exponent") for value in self.torsion_exponents),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient": self.coefficient,
            "free_exponents": self.free_exponents,
            "schema": self.SCHEMA_ID,
            "torsion_exponents": self.torsion_exponents,
        }


@dataclass(frozen=True)
class LaurentPolynomial:
    coefficient_modulus: int
    translation_group: TranslationGroup
    terms: Tuple[LaurentTerm, ...] = ()

    SCHEMA_ID = "mobility_toolkit.laurent_polynomial.v1"

    def __post_init__(self) -> None:
        modulus = _integer(self.coefficient_modulus, "coefficient_modulus")
        if modulus <= 1:
            raise ValueError("coefficient_modulus must be greater than one")
        combined: Dict[Tuple[Tuple[int, ...], Tuple[int, ...]], int] = {}
        for term in tuple(self.terms):
            if not isinstance(term, LaurentTerm):
                raise TypeError("terms must be LaurentTerm objects")
            if len(term.free_exponents) != self.translation_group.free_rank:
                raise ValueError("free exponent count does not match translation group")
            if len(term.torsion_exponents) != len(self.translation_group.torsion_invariants):
                raise ValueError("torsion exponent count does not match translation group")
            torsion = tuple(
                exponent % order
                for exponent, order in zip(
                    term.torsion_exponents, self.translation_group.torsion_invariants
                )
            )
            key = (term.free_exponents, torsion)
            combined[key] = (combined.get(key, 0) + term.coefficient) % modulus
        normalized = tuple(
            LaurentTerm(coefficient, free, torsion)
            for (free, torsion), coefficient in sorted(combined.items())
            if coefficient
        )
        object.__setattr__(self, "coefficient_modulus", modulus)
        object.__setattr__(self, "terms", normalized)

    @classmethod
    def zero(cls, modulus: int, group: TranslationGroup) -> "LaurentPolynomial":
        return cls(modulus, group)

    @classmethod
    def one(cls, modulus: int, group: TranslationGroup) -> "LaurentPolynomial":
        return cls(
            modulus,
            group,
            (LaurentTerm(1, (0,) * group.free_rank, (0,) * len(group.torsion_invariants)),),
        )

    @classmethod
    def monomial(
        cls,
        modulus: int,
        group: TranslationGroup,
        coefficient: int,
        free_exponents: Sequence[int],
        torsion_exponents: Sequence[int] = (),
    ) -> "LaurentPolynomial":
        return cls(
            modulus,
            group,
            (LaurentTerm(coefficient, tuple(free_exponents), tuple(torsion_exponents)),),
        )

    def _require_same_ring(self, other: "LaurentPolynomial") -> None:
        if not isinstance(other, LaurentPolynomial):
            raise TypeError("expected LaurentPolynomial")
        if (
            self.coefficient_modulus != other.coefficient_modulus
            or self.translation_group != other.translation_group
        ):
            raise ValueError("Laurent polynomials belong to different group rings")

    def __add__(self, other: "LaurentPolynomial") -> "LaurentPolynomial":
        self._require_same_ring(other)
        return LaurentPolynomial(
            self.coefficient_modulus,
            self.translation_group,
            self.terms + other.terms,
        )

    def __neg__(self) -> "LaurentPolynomial":
        return LaurentPolynomial(
            self.coefficient_modulus,
            self.translation_group,
            tuple(
                LaurentTerm(-term.coefficient, term.free_exponents, term.torsion_exponents)
                for term in self.terms
            ),
        )

    def __sub__(self, other: "LaurentPolynomial") -> "LaurentPolynomial":
        return self + (-other)

    def __mul__(self, other: "LaurentPolynomial") -> "LaurentPolynomial":
        self._require_same_ring(other)
        products = []
        for left in self.terms:
            for right in other.terms:
                products.append(
                    LaurentTerm(
                        left.coefficient * right.coefficient,
                        tuple(a + b for a, b in zip(left.free_exponents, right.free_exponents)),
                        tuple(
                            a + b
                            for a, b in zip(left.torsion_exponents, right.torsion_exponents)
                        ),
                    )
                )
        return LaurentPolynomial(self.coefficient_modulus, self.translation_group, tuple(products))

    def involution(self) -> "LaurentPolynomial":
        """Apply the group inverse involution ``bar(g) = g^-1``."""

        return LaurentPolynomial(
            self.coefficient_modulus,
            self.translation_group,
            tuple(
                LaurentTerm(
                    term.coefficient,
                    tuple(-value for value in term.free_exponents),
                    tuple(-value for value in term.torsion_exponents),
                )
                for term in self.terms
            ),
        )

    @property
    def is_zero(self) -> bool:
        return not self.terms

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_modulus": self.coefficient_modulus,
            "schema": self.SCHEMA_ID,
            "terms": self.terms,
            "translation_group": self.translation_group,
        }


__all__ = ["LaurentPolynomial", "LaurentTerm", "TranslationGroup"]
