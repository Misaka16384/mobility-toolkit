"""Phase-aware local Pauli frames used by twisted finite identifications."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.pauli import LocalPauliTerm, LocalSystem, PauliModule


@dataclass(frozen=True)
class LocalPauliImage:
    phase: int
    x_exponents: Tuple[int, ...]
    z_exponents: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.local_pauli_image.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "phase": self.phase,
            "schema": self.SCHEMA_ID,
            "x_exponents": self.x_exponents,
            "z_exponents": self.z_exponents,
        }


def _local_module(factors: Tuple[int, ...]) -> PauliModule:
    return PauliModule((LocalSystem("__local_frame__", factors),))


def _to_operator(factors: Tuple[int, ...], image: LocalPauliImage):
    module = _local_module(factors)
    return module.operator(
        (
            LocalPauliTerm(
                "__local_frame__",
                image.x_exponents,
                image.z_exponents,
            ),
        ),
        phase=image.phase,
    )


def _from_operator(operator) -> LocalPauliImage:
    factor_count = len(operator.module.local_systems[0].invariant_factors)
    if operator.terms:
        term = operator.terms[0]
        x_values = term.x_exponents
        z_values = term.z_exponents
    else:
        x_values = (0,) * factor_count
        z_values = (0,) * factor_count
    return LocalPauliImage(operator.phase, x_values, z_values)


@dataclass(frozen=True)
class LocalPauliMap:
    """A phase-preserving homomorphism specified by basis-generator images."""

    invariant_factors: Tuple[int, ...]
    images: Tuple[LocalPauliImage, ...]

    SCHEMA_ID = "mobility_toolkit.local_pauli_map.v1"

    def __post_init__(self) -> None:
        factors = tuple(self.invariant_factors)
        if not factors or any(value <= 1 for value in factors):
            raise ValueError("local frame invariant factors must be greater than one")
        if any(right % left != 0 for left, right in zip(factors, factors[1:])):
            raise ValueError("local frame invariant factors must form a divisibility chain")
        if len(self.images) != 2 * len(factors):
            raise ValueError("local Pauli map needs X/Z images for every factor")
        normalized = tuple(_from_operator(_to_operator(factors, image)) for image in self.images)
        object.__setattr__(self, "invariant_factors", factors)
        object.__setattr__(self, "images", normalized)
        self._validate_homomorphism()

    @classmethod
    def identity(cls, factors: Sequence[int]) -> "LocalPauliMap":
        factors = tuple(factors)
        images = []
        for index in range(len(factors)):
            x_values = [0] * len(factors)
            z_values = [0] * len(factors)
            x_values[index] = 1
            images.append(LocalPauliImage(0, tuple(x_values), tuple(z_values)))
            x_values = [0] * len(factors)
            z_values = [0] * len(factors)
            z_values[index] = 1
            images.append(LocalPauliImage(0, tuple(x_values), tuple(z_values)))
        return cls(factors, tuple(images))

    @property
    def phase_modulus(self) -> int:
        return math.lcm(*(2 * factor for factor in self.invariant_factors))

    def _basis_operators(self):
        module = _local_module(self.invariant_factors)
        result = []
        for index in range(len(self.invariant_factors)):
            x_values = [0] * len(self.invariant_factors)
            z_values = [0] * len(self.invariant_factors)
            x_values[index] = 1
            result.append(
                module.operator(
                    (LocalPauliTerm("__local_frame__", tuple(x_values), tuple(z_values)),)
                )
            )
            x_values = [0] * len(self.invariant_factors)
            z_values = [0] * len(self.invariant_factors)
            z_values[index] = 1
            result.append(
                module.operator(
                    (LocalPauliTerm("__local_frame__", tuple(x_values), tuple(z_values)),)
                )
            )
        return tuple(result)

    def _validate_homomorphism(self) -> None:
        source_basis = self._basis_operators()
        image_basis = tuple(_to_operator(self.invariant_factors, image) for image in self.images)
        for index, (source, image) in enumerate(zip(source_basis, image_basis)):
            factor = self.invariant_factors[index // 2]
            if not image.power(factor).is_identity:
                raise ValueError("local Pauli image violates a source order relation")
            if image.projective_element_order != source.projective_element_order:
                raise ValueError("local Pauli image changes a basis-generator order")
        for left_index, source_left in enumerate(source_basis):
            for right_index, source_right in enumerate(source_basis):
                if image_basis[left_index].projective_pairing(image_basis[right_index]) != (
                    source_left.projective_pairing(source_right)
                ):
                    raise ValueError("local Pauli images do not preserve the commutator pairing")

    def apply(
        self,
        x_exponents: Sequence[int],
        z_exponents: Sequence[int],
        phase: int = 0,
    ) -> LocalPauliImage:
        x_exponents = tuple(x_exponents)
        z_exponents = tuple(z_exponents)
        if len(x_exponents) != len(self.invariant_factors) or len(z_exponents) != len(
            self.invariant_factors
        ):
            raise ValueError("local Pauli exponents do not match the frame factors")
        module = _local_module(self.invariant_factors)
        result = module.identity(phase)
        for index, (x_value, z_value) in enumerate(zip(x_exponents, z_exponents)):
            result = result * _to_operator(
                self.invariant_factors, self.images[2 * index]
            ).power(x_value)
            result = result * _to_operator(
                self.invariant_factors, self.images[2 * index + 1]
            ).power(z_value)
        return _from_operator(result)

    def then(self, after: "LocalPauliMap") -> "LocalPauliMap":
        """Return ``after o self``."""

        if not isinstance(after, LocalPauliMap) or after.invariant_factors != self.invariant_factors:
            raise ValueError("local Pauli maps have incompatible factors")
        images = tuple(
            after.apply(image.x_exponents, image.z_exponents, image.phase)
            for image in self.images
        )
        return LocalPauliMap(self.invariant_factors, images)

    @property
    def is_identity(self) -> bool:
        return self == self.identity(self.invariant_factors)

    def to_canonical_dict(self) -> dict:
        return {
            "images": self.images,
            "invariant_factors": self.invariant_factors,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class LocalPauliAutomorphism:
    forward: LocalPauliMap
    inverse: LocalPauliMap

    SCHEMA_ID = "mobility_toolkit.local_pauli_automorphism.v1"

    def __post_init__(self) -> None:
        if self.forward.invariant_factors != self.inverse.invariant_factors:
            raise ValueError("local Pauli automorphism maps have incompatible factors")
        if not self.forward.then(self.inverse).is_identity:
            raise ValueError("declared inverse is not a left inverse")
        if not self.inverse.then(self.forward).is_identity:
            raise ValueError("declared inverse is not a right inverse")

    @classmethod
    def identity(cls, factors: Sequence[int]) -> "LocalPauliAutomorphism":
        identity = LocalPauliMap.identity(tuple(factors))
        return cls(identity, identity)

    @classmethod
    def cyclic_multipliers(
        cls, factors: Sequence[int], multipliers: Sequence[int]
    ) -> "LocalPauliAutomorphism":
        factors = tuple(factors)
        multipliers = tuple(multipliers)
        if len(factors) != len(multipliers):
            raise ValueError("one cyclic multiplier is required per invariant factor")

        def make_map(values):
            images = []
            for index, (factor, value) in enumerate(zip(factors, values)):
                if math.gcd(value, factor) != 1:
                    raise ValueError("cyclic frame multiplier must be a unit")
                inverse_value = pow(value, -1, factor)
                x_values = [0] * len(factors)
                z_values = [0] * len(factors)
                x_values[index] = value
                images.append(LocalPauliImage(0, tuple(x_values), tuple(z_values)))
                x_values = [0] * len(factors)
                z_values = [0] * len(factors)
                z_values[index] = inverse_value
                images.append(LocalPauliImage(0, tuple(x_values), tuple(z_values)))
            return LocalPauliMap(factors, tuple(images))

        forward = make_map(multipliers)
        inverse = make_map(tuple(pow(value, -1, factor) for value, factor in zip(multipliers, factors)))
        return cls(forward, inverse)

    @classmethod
    def fourier(cls, factors: Sequence[int]) -> "LocalPauliAutomorphism":
        factors = tuple(factors)

        def make_map(inverse: bool):
            images = []
            for index, factor in enumerate(factors):
                x_values = [0] * len(factors)
                z_values = [0] * len(factors)
                if inverse:
                    z_values[index] = -1
                else:
                    z_values[index] = 1
                images.append(LocalPauliImage(0, tuple(x_values), tuple(z_values)))
                x_values = [0] * len(factors)
                z_values = [0] * len(factors)
                if inverse:
                    x_values[index] = 1
                else:
                    x_values[index] = -1
                images.append(LocalPauliImage(0, tuple(x_values), tuple(z_values)))
            return LocalPauliMap(factors, tuple(images))

        return cls(make_map(False), make_map(True))

    @property
    def invariant_factors(self) -> Tuple[int, ...]:
        return self.forward.invariant_factors

    def power(self, exponent: int) -> LocalPauliMap:
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            raise TypeError("frame exponent must be an integer")
        base = self.forward if exponent >= 0 else self.inverse
        remaining = abs(exponent)
        result = LocalPauliMap.identity(self.invariant_factors)
        while remaining:
            if remaining & 1:
                result = result.then(base)
            base = base.then(base)
            remaining >>= 1
        return result

    def to_canonical_dict(self) -> dict:
        return {
            "forward": self.forward,
            "inverse": self.inverse,
            "schema": self.SCHEMA_ID,
        }


__all__ = [
    "LocalPauliAutomorphism",
    "LocalPauliImage",
    "LocalPauliMap",
]
