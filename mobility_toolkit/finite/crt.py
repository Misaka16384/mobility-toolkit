"""Certified Chinese-remainder and primary decomposition utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import reduce
from operator import mul
from typing import Sequence, Tuple

from sympy import factorint

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import FiniteAbelianGroup, FiniteSubgroup


def prime_power_factors(value: int) -> Tuple[Tuple[int, int, int], ...]:
    """Return canonical ``(prime, exponent, prime**exponent)`` factors."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("factorization input must be a positive integer")
    return tuple(
        (int(prime), int(exponent), int(prime) ** int(exponent))
        for prime, exponent in sorted(factorint(value).items())
    )


def crt_recombine(residues: Sequence[int], moduli: Sequence[int]) -> int:
    residues = tuple(residues)
    moduli = tuple(moduli)
    if len(residues) != len(moduli):
        raise ValueError("CRT residues and moduli must have equal length")
    if any(isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1 for modulus in moduli):
        raise ValueError("CRT moduli must be integers greater than one")
    for left_index, left in enumerate(moduli):
        for right in moduli[left_index + 1 :]:
            if math.gcd(left, right) != 1:
                raise ValueError("CRT moduli must be pairwise coprime")
    total_modulus = reduce(mul, moduli, 1)
    value = 0
    for residue, modulus in zip(residues, moduli):
        cofactor = total_modulus // modulus
        value += (residue % modulus) * cofactor * pow(cofactor, -1, modulus)
    return value % total_modulus


@dataclass(frozen=True)
class PrimaryComponent:
    prime: int
    exponent: int
    prime_power: int
    projector: int
    subgroup: FiniteSubgroup
    invariant_factors: Tuple[int, ...]

    def to_canonical_dict(self) -> dict:
        return {
            "exponent": self.exponent,
            "invariant_factors": self.invariant_factors,
            "prime": self.prime,
            "prime_power": self.prime_power,
            "projector": self.projector,
            "subgroup": self.subgroup,
        }


@dataclass(frozen=True)
class PrimaryDecomposition:
    group: FiniteAbelianGroup
    exponent: int
    components: Tuple[PrimaryComponent, ...]

    SCHEMA_ID = "mobility_toolkit.primary_decomposition.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "components": self.components,
            "exponent": self.exponent,
            "group": self.group,
            "schema": self.SCHEMA_ID,
        }


def primary_decomposition(
    group: FiniteAbelianGroup,
    backend: FiniteIntegerBackend,
) -> PrimaryDecomposition:
    exponent = group.invariant_factors[-1] if group.invariant_factors else 1
    if exponent == 1:
        return PrimaryDecomposition(group, 1, ())
    rank = group.presentation_rank
    components = []
    for prime, power_exponent, prime_power in prime_power_factors(exponent):
        cofactor = exponent // prime_power
        projector = (cofactor * pow(cofactor, -1, prime_power)) % exponent
        generators = SparseIntMatrix(
            rank,
            rank,
            tuple((index, index, projector) for index in range(rank) if projector),
        )
        subgroup = group.subgroup(generators, backend)
        factors = subgroup.invariant_factors(backend)
        if any(
            factor <= 1 or any(other_prime != prime for other_prime, _, _ in prime_power_factors(factor))
            for factor in factors
        ):
            raise ArithmeticError("primary projector produced a non-primary subgroup")
        components.append(
            PrimaryComponent(
                prime,
                power_exponent,
                prime_power,
                projector,
                subgroup,
                factors,
            )
        )
    result = PrimaryDecomposition(group, exponent, tuple(components))
    verify_primary_decomposition(result, backend)
    return result


def verify_primary_decomposition(
    decomposition: PrimaryDecomposition,
    backend: FiniteIntegerBackend,
) -> None:
    group = decomposition.group
    if not decomposition.components:
        if group.order(backend) != 1:
            raise ArithmeticError("nontrivial group has an empty primary decomposition")
        return
    projectors = tuple(component.projector for component in decomposition.components)
    exponent = decomposition.exponent
    if sum(projectors) % exponent != 1 % exponent:
        raise ArithmeticError("primary projectors do not sum to the identity")
    for index, component in enumerate(decomposition.components):
        if component.projector * component.projector % exponent != component.projector:
            raise ArithmeticError("primary projector is not idempotent")
        for other in decomposition.components[index + 1 :]:
            if component.projector * other.projector % exponent:
                raise ArithmeticError("primary projectors are not orthogonal")
            intersection = component.subgroup.intersection(other.subgroup, backend)
            if intersection.order(backend) != 1:
                raise ArithmeticError("distinct primary components intersect nontrivially")
    combined = decomposition.components[0].subgroup
    for component in decomposition.components[1:]:
        combined = combined.sum(component.subgroup, backend)
    if combined != group.whole_subgroup(backend):
        raise ArithmeticError("primary components do not generate the whole group")
    component_order = reduce(
        mul,
        (component.subgroup.order(backend) for component in decomposition.components),
        1,
    )
    if component_order != group.order(backend):
        raise ArithmeticError("primary component orders do not multiply to the group order")


__all__ = [
    "PrimaryComponent",
    "PrimaryDecomposition",
    "crt_recombine",
    "primary_decomposition",
    "prime_power_factors",
    "verify_primary_decomposition",
]
