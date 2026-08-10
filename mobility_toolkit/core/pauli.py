"""Phase-aware generalized Pauli value objects.

The public representation is sparse and site-labelled. Flat blocked or
interleaved vectors are backend adapters, never the semantic identity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple


def _plain_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@dataclass(frozen=True)
class LocalSystem:
    """A local Hilbert space labelled by finite-abelian invariant factors."""

    site_id: str
    invariant_factors: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.local_system.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.site_id, str) or not self.site_id:
            raise ValueError("site_id must be a nonempty string")
        factors = tuple(_plain_int(value, "invariant factor") for value in self.invariant_factors)
        if not factors or any(value <= 1 for value in factors):
            raise ValueError("local invariant factors must be greater than one")
        if any(right % left != 0 for left, right in zip(factors, factors[1:])):
            raise ValueError("local invariant factors must form a divisibility chain")
        object.__setattr__(self, "invariant_factors", factors)

    @classmethod
    def cyclic(cls, site_id: str, dimension: int) -> "LocalSystem":
        return cls(site_id, (dimension,))

    @property
    def hilbert_dimension(self) -> int:
        # ⚡ Bolt: C-optimized math.prod for performance
        return math.prod(self.invariant_factors)

    def to_canonical_dict(self) -> dict:
        return {
            "invariant_factors": self.invariant_factors,
            "schema": self.SCHEMA_ID,
            "site_id": self.site_id,
        }


@dataclass(frozen=True)
class LocalPauliTerm:
    """Local projective Pauli exponents for one site."""

    site_id: str
    x_exponents: Tuple[int, ...]
    z_exponents: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.local_pauli_term.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.site_id, str) or not self.site_id:
            raise ValueError("site_id must be a nonempty string")
        object.__setattr__(
            self,
            "x_exponents",
            tuple(_plain_int(value, "X exponent") for value in self.x_exponents),
        )
        object.__setattr__(
            self,
            "z_exponents",
            tuple(_plain_int(value, "Z exponent") for value in self.z_exponents),
        )

    @classmethod
    def cyclic(cls, site_id: str, x: int = 0, z: int = 0) -> "LocalPauliTerm":
        return cls(site_id, (x,), (z,))

    def to_canonical_dict(self) -> dict:
        return {
            "schema": self.SCHEMA_ID,
            "site_id": self.site_id,
            "x_exponents": self.x_exponents,
            "z_exponents": self.z_exponents,
        }


@dataclass(frozen=True)
class PauliModule:
    """Finite generalized Pauli module with a common ``2*lcm`` phase group."""

    local_systems: Tuple[LocalSystem, ...]
    phase_convention: str = "xz_normal_2lcm"

    SCHEMA_ID = "mobility_toolkit.pauli_module.v1"

    def __post_init__(self) -> None:
        systems = tuple(sorted(tuple(self.local_systems), key=lambda item: item.site_id))
        if len({system.site_id for system in systems}) != len(systems):
            raise ValueError("local system site IDs must be unique")
        if self.phase_convention != "xz_normal_2lcm":
            raise ValueError(f"unsupported phase convention: {self.phase_convention}")
        object.__setattr__(self, "local_systems", systems)

    @classmethod
    def from_dimensions(
        cls, dimensions: Sequence[int], site_ids: Sequence[str] = ()
    ) -> "PauliModule":
        dimensions = tuple(_plain_int(value, "dimension") for value in dimensions)
        if site_ids:
            site_ids = tuple(site_ids)
            if len(site_ids) != len(dimensions):
                raise ValueError("site_ids must match dimensions")
        else:
            site_ids = tuple(f"q{index}" for index in range(len(dimensions)))
        return cls(tuple(LocalSystem.cyclic(site_id, dim) for site_id, dim in zip(site_ids, dimensions)))

    @property
    def phase_modulus(self) -> int:
        factors = [2 * factor for system in self.local_systems for factor in system.invariant_factors]
        return math.lcm(*factors) if factors else 2

    @property
    def hilbert_dimension(self) -> int:
        # ⚡ Bolt: C-optimized math.prod for performance
        return math.prod(system.hilbert_dimension for system in self.local_systems)

    @property
    def projective_order(self) -> int:
        return self.hilbert_dimension * self.hilbert_dimension

    def system(self, site_id: str) -> LocalSystem:
        for system in self.local_systems:
            if system.site_id == site_id:
                return system
        raise KeyError(f"unknown Pauli site: {site_id}")

    def identity(self, phase: int = 0) -> "PauliOperator":
        return PauliOperator(self, phase, ())

    def operator(
        self, terms: Iterable[LocalPauliTerm], phase: int = 0
    ) -> "PauliOperator":
        return PauliOperator(self, phase, tuple(terms))

    def to_canonical_dict(self) -> dict:
        return {
            "local_systems": self.local_systems,
            "phase_convention": self.phase_convention,
            "phase_modulus": self.phase_modulus,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PauliOperator:
    """A normal-ordered phase-aware generalized Pauli operator."""

    module: PauliModule
    phase: int = 0
    terms: Tuple[LocalPauliTerm, ...] = ()

    SCHEMA_ID = "mobility_toolkit.pauli_operator.v1"

    def __post_init__(self) -> None:
        phase = _plain_int(self.phase, "phase") % self.module.phase_modulus
        accumulated: Dict[str, Tuple[list, list]] = {}
        for term in tuple(self.terms):
            if not isinstance(term, LocalPauliTerm):
                raise TypeError("Pauli terms must be LocalPauliTerm objects")
            system = self.module.system(term.site_id)
            if len(term.x_exponents) != len(system.invariant_factors):
                raise ValueError(f"X exponent count does not match site {term.site_id}")
            if len(term.z_exponents) != len(system.invariant_factors):
                raise ValueError(f"Z exponent count does not match site {term.site_id}")
            if term.site_id not in accumulated:
                accumulated[term.site_id] = (
                    [0] * len(system.invariant_factors),
                    [0] * len(system.invariant_factors),
                )
            x_values, z_values = accumulated[term.site_id]
            for index, factor in enumerate(system.invariant_factors):
                x_values[index] = (x_values[index] + term.x_exponents[index]) % factor
                z_values[index] = (z_values[index] + term.z_exponents[index]) % factor

        normalized = []
        for site_id in sorted(accumulated):
            x_values, z_values = accumulated[site_id]
            if any(x_values) or any(z_values):
                normalized.append(LocalPauliTerm(site_id, tuple(x_values), tuple(z_values)))
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "terms", tuple(normalized))

    def _term_map(self) -> Dict[str, LocalPauliTerm]:
        return {term.site_id: term for term in self.terms}

    def _normal_order_cocycle(self, other: "PauliOperator") -> int:
        self._require_same_module(other)
        left = self._term_map()
        right = other._term_map()
        total = 0
        modulus = self.module.phase_modulus
        for system in self.module.local_systems:
            left_term = left.get(system.site_id)
            right_term = right.get(system.site_id)
            if left_term is None or right_term is None:
                continue
            for index, factor in enumerate(system.invariant_factors):
                total += (
                    (modulus // factor)
                    * left_term.z_exponents[index]
                    * right_term.x_exponents[index]
                )
        return total % modulus

    def _require_same_module(self, other: "PauliOperator") -> None:
        if not isinstance(other, PauliOperator) or self.module != other.module:
            raise ValueError("Pauli operators must belong to the same module")

    def multiply(self, other: "PauliOperator") -> "PauliOperator":
        self._require_same_module(other)
        terms = list(self.terms) + list(other.terms)
        phase = self.phase + other.phase + self._normal_order_cocycle(other)
        return PauliOperator(self.module, phase, tuple(terms))

    def __mul__(self, other: "PauliOperator") -> "PauliOperator":
        return self.multiply(other)

    def inverse(self) -> "PauliOperator":
        inverse_terms = []
        for term in self.terms:
            system = self.module.system(term.site_id)
            inverse_terms.append(
                LocalPauliTerm(
                    term.site_id,
                    tuple(-value for value in term.x_exponents),
                    tuple(-value for value in term.z_exponents),
                )
            )
        projective_inverse = PauliOperator(self.module, 0, tuple(inverse_terms))
        correction = self._normal_order_cocycle(projective_inverse)
        return PauliOperator(self.module, -self.phase - correction, tuple(inverse_terms))

    def power(self, exponent: int) -> "PauliOperator":
        exponent = _plain_int(exponent, "exponent")
        if exponent < 0:
            return self.inverse().power(-exponent)
        result = self.module.identity()
        base = self
        remaining = exponent
        while remaining:
            if remaining & 1:
                result = result * base
            base = base * base
            remaining >>= 1
        return result

    def __pow__(self, exponent: int) -> "PauliOperator":
        return self.power(exponent)

    def projective_pairing(self, other: "PauliOperator") -> int:
        self._require_same_module(other)
        return (
            self._normal_order_cocycle(other) - other._normal_order_cocycle(self)
        ) % self.module.phase_modulus

    def commutes_with(self, other: "PauliOperator") -> bool:
        return self.projective_pairing(other) == 0

    @property
    def is_projective_identity(self) -> bool:
        return not self.terms

    @property
    def is_identity(self) -> bool:
        return self.is_projective_identity and self.phase == 0

    @property
    def scalar_phase(self) -> int:
        if not self.is_projective_identity:
            raise ValueError("operator is not projectively scalar")
        return self.phase

    @property
    def projective_element_order(self) -> int:
        order = 1
        for term in self.terms:
            system = self.module.system(term.site_id)
            for factor, x_value, z_value in zip(
                system.invariant_factors, term.x_exponents, term.z_exponents
            ):
                if x_value:
                    order = math.lcm(order, factor // math.gcd(factor, x_value))
                if z_value:
                    order = math.lcm(order, factor // math.gcd(factor, z_value))
        return order

    @property
    def scalar_obstruction(self) -> int:
        return self.power(self.projective_element_order).scalar_phase

    def with_phase(self, phase: int) -> "PauliOperator":
        return PauliOperator(self.module, phase, self.terms)

    def projective_key(self) -> tuple:
        return tuple(
            (term.site_id, term.x_exponents, term.z_exponents) for term in self.terms
        )

    def to_canonical_dict(self) -> dict:
        return {
            "module": self.module,
            "phase": self.phase,
            "schema": self.SCHEMA_ID,
            "terms": self.terms,
        }


__all__ = ["LocalPauliTerm", "LocalSystem", "PauliModule", "PauliOperator"]
