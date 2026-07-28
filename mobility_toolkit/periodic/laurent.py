"""Canonical group-ring values used by periodic module presentations.

Strings are deliberately absent from the mathematical identity of these
objects.  Rendering and parsing helpers at the bottom of this module are
backend-boundary adapters; they always convert to or from the canonical AST.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.laurent import (
    LaurentPolynomial,
    LaurentTerm,
    TranslationGroup,
)


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@dataclass(frozen=True)
class GroupRingMonomial:
    """One element of a finitely generated abelian translation group."""

    translation_group: TranslationGroup
    free_exponents: Tuple[int, ...]
    torsion_exponents: Tuple[int, ...] = ()

    SCHEMA_ID = "mobility_toolkit.group_ring_monomial.v1"

    def __post_init__(self) -> None:
        free = tuple(_integer(value, "free exponent") for value in self.free_exponents)
        torsion = tuple(
            _integer(value, "torsion exponent") for value in self.torsion_exponents
        )
        if len(free) != self.translation_group.free_rank:
            raise ValueError("free exponent count does not match the translation group")
        if len(torsion) != len(self.translation_group.torsion_invariants):
            raise ValueError("torsion exponent count does not match the translation group")
        torsion = tuple(
            value % order
            for value, order in zip(torsion, self.translation_group.torsion_invariants)
        )
        object.__setattr__(self, "free_exponents", free)
        object.__setattr__(self, "torsion_exponents", torsion)

    @classmethod
    def identity(cls, group: TranslationGroup) -> "GroupRingMonomial":
        return cls(
            group,
            (0,) * group.free_rank,
            (0,) * len(group.torsion_invariants),
        )

    def _require_same_group(self, other: "GroupRingMonomial") -> None:
        if not isinstance(other, GroupRingMonomial):
            raise TypeError("expected GroupRingMonomial")
        if self.translation_group != other.translation_group:
            raise ValueError("monomials belong to different translation groups")

    def __mul__(self, other: "GroupRingMonomial") -> "GroupRingMonomial":
        self._require_same_group(other)
        return GroupRingMonomial(
            self.translation_group,
            tuple(a + b for a, b in zip(self.free_exponents, other.free_exponents)),
            tuple(
                a + b
                for a, b in zip(self.torsion_exponents, other.torsion_exponents)
            ),
        )

    def inverse(self) -> "GroupRingMonomial":
        return GroupRingMonomial(
            self.translation_group,
            tuple(-value for value in self.free_exponents),
            tuple(-value for value in self.torsion_exponents),
        )

    def as_polynomial(self, coefficient_modulus: int, coefficient: int = 1) -> LaurentPolynomial:
        return LaurentPolynomial.monomial(
            coefficient_modulus,
            self.translation_group,
            _integer(coefficient, "coefficient"),
            self.free_exponents,
            self.torsion_exponents,
        )

    def to_canonical_dict(self) -> dict:
        return {
            "free_exponents": self.free_exponents,
            "schema": self.SCHEMA_ID,
            "torsion_exponents": self.torsion_exponents,
            "translation_group": self.translation_group,
        }


def polynomial_from_terms(
    coefficient_modulus: int,
    translation_group: TranslationGroup,
    terms: Sequence[Tuple[int, GroupRingMonomial]],
) -> LaurentPolynomial:
    """Build a polynomial while enforcing a single declared group ring."""

    ast_terms = []
    for coefficient, monomial in tuple(terms):
        if not isinstance(monomial, GroupRingMonomial):
            raise TypeError("polynomial terms must contain GroupRingMonomial objects")
        if monomial.translation_group != translation_group:
            raise ValueError("polynomial monomial belongs to a different translation group")
        ast_terms.append(
            LaurentTerm(
                _integer(coefficient, "coefficient"),
                monomial.free_exponents,
                monomial.torsion_exponents,
            )
        )
    return LaurentPolynomial(coefficient_modulus, translation_group, tuple(ast_terms))


def render_m2_laurent(polynomial: LaurentPolynomial) -> str:
    """Render canonical AST to the legacy Laurent quotient used by Macaulay2.

    This function is not a serializer: its output must never be used as a
    cache key or mathematical identifier.
    """

    if polynomial.translation_group.torsion_invariants:
        raise ValueError("the legacy Macaulay2 adapter does not support torsion translations")
    if polynomial.is_zero:
        return "0"
    rendered = []
    for term in polynomial.terms:
        factors = []
        coefficient = term.coefficient % polynomial.coefficient_modulus
        for index, exponent in enumerate(term.free_exponents, 1):
            if exponent == 0:
                continue
            variable = f"x{index}" if exponent > 0 else f"t{index}"
            power = abs(exponent)
            factors.append(variable if power == 1 else f"{variable}^{power}")
        if coefficient != 1 or not factors:
            factors.insert(0, str(coefficient))
        rendered.append("*".join(factors))
    return " + ".join(rendered)


def parse_legacy_laurent(
    expression: str,
    coefficient_modulus: int,
    translation_group: TranslationGroup,
) -> LaurentPolynomial:
    """Parse legacy/M2 text and immediately return the canonical AST.

    Parsing is intentionally an adapter-only escape hatch.  The periodic
    request and presentation schemas do not accept polynomial strings.
    """

    if translation_group.torsion_invariants:
        raise ValueError("legacy Laurent syntax cannot represent torsion translations")
    if not isinstance(expression, str):
        raise TypeError("legacy Laurent expression must be a string")
    # Reuse the already-hardened exact parser at the old API boundary.  Its
    # dictionary result is not allowed to escape this function.
    from mobility_toolkit.translate import _parse_laurent_poly

    parsed = _parse_laurent_poly(
        expression,
        translation_group.free_rank,
        coefficient_modulus,
    )
    return LaurentPolynomial(
        coefficient_modulus,
        translation_group,
        tuple(
            LaurentTerm(coefficient, exponents, ())
            for exponents, coefficient in parsed.items()
        ),
    )


__all__ = [
    "GroupRingMonomial",
    "LaurentPolynomial",
    "LaurentTerm",
    "TranslationGroup",
    "parse_legacy_laurent",
    "polynomial_from_terms",
    "render_m2_laurent",
]
