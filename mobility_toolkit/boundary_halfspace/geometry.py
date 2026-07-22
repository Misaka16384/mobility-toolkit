"""Pure-integer geometry for rational lattice half-spaces.

An oriented primitive covector ``n`` describes the retained half-space

    n . x - offset >= 0.

The adapted unimodular basis has tangent vectors in its first ``d - 1``
columns and a transverse vector in its final column.  Consequently
``n * basis_matrix = (0, ..., 0, 1)`` and every lattice point has unique
coordinates ``(tangent, depth)`` with integer depth.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Iterable, Sequence, Tuple


IntegerVector = Tuple[int, ...]
IntegerMatrix = Tuple[IntegerVector, ...]


def _integer_vector(values: Sequence[int], name: str) -> IntegerVector:
    result = tuple(values)
    if not result:
        raise ValueError(f"{name} must be nonempty")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in result):
        raise TypeError(f"{name} entries must be integers")
    return result


def _extended_gcd(left: int, right: int) -> Tuple[int, int, int]:
    """Return nonnegative gcd and Bezout coefficients."""

    old_r, remainder = abs(left), abs(right)
    old_s, coefficient_s = 1, 0
    old_t, coefficient_t = 0, 1
    while remainder:
        quotient = old_r // remainder
        old_r, remainder = remainder, old_r - quotient * remainder
        old_s, coefficient_s = coefficient_s, old_s - quotient * coefficient_s
        old_t, coefficient_t = coefficient_t, old_t - quotient * coefficient_t
    if left < 0:
        old_s = -old_s
    if right < 0:
        old_t = -old_t
    return old_r, old_s, old_t


def _determinant(matrix: IntegerMatrix) -> int:
    """Exact determinant via fraction-free Bareiss elimination."""

    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise ValueError("determinant requires a nonempty square matrix")
    if size == 1:
        return matrix[0][0]
    work = [list(row) for row in matrix]
    sign = 1
    previous = 1
    for pivot_index in range(size - 1):
        pivot_row = next(
            (row for row in range(pivot_index, size) if work[row][pivot_index]),
            None,
        )
        if pivot_row is None:
            return 0
        if pivot_row != pivot_index:
            work[pivot_index], work[pivot_row] = work[pivot_row], work[pivot_index]
            sign = -sign
        pivot = work[pivot_index][pivot_index]
        for row in range(pivot_index + 1, size):
            for column in range(pivot_index + 1, size):
                numerator = (
                    work[row][column] * pivot
                    - work[row][pivot_index] * work[pivot_index][column]
                )
                if numerator % previous:
                    raise ArithmeticError("Bareiss elimination lost exact divisibility")
                work[row][column] = numerator // previous
            work[row][pivot_index] = 0
        previous = pivot
    return sign * work[-1][-1]


def _integer_inverse(matrix: IntegerMatrix) -> IntegerMatrix:
    size = len(matrix)
    augmented = [
        [Fraction(value) for value in row]
        + [Fraction(int(row_index == column)) for column in range(size)]
        for row_index, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot_row = next(
            (row for row in range(column, size) if augmented[row][column]),
            None,
        )
        if pivot_row is None:
            raise ValueError("matrix is singular")
        augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        pivot = augmented[column][column]
        augmented[column] = [value / pivot for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            coefficient = augmented[row][column]
            if coefficient:
                augmented[row] = [
                    left - coefficient * right
                    for left, right in zip(augmented[row], augmented[column])
                ]
    result = []
    for row in augmented:
        inverse_row = row[size:]
        if any(value.denominator != 1 for value in inverse_row):
            raise ValueError("matrix inverse is not integral")
        result.append(tuple(value.numerator for value in inverse_row))
    return tuple(result)


def _matrix_vector(matrix: IntegerMatrix, vector: IntegerVector) -> IntegerVector:
    if any(len(row) != len(vector) for row in matrix):
        raise ValueError("matrix-vector dimension mismatch")
    return tuple(sum(left * right for left, right in zip(row, vector)) for row in matrix)


class OrientationRelation(str, Enum):
    SAME = "same"
    OPPOSITE = "opposite"
    NONPARALLEL = "nonparallel"


@dataclass(frozen=True, order=True)
class PrimitiveNormal:
    """An oriented primitive integer covector.

    ``n`` and ``-n`` remain distinct because they retain opposite sides of the
    same rational hyperplane.
    """

    components: IntegerVector

    SCHEMA_ID = "mobility_toolkit.primitive_normal.v1"

    def __post_init__(self) -> None:
        values = _integer_vector(self.components, "normal")
        divisor = math.gcd(*(abs(value) for value in values))
        if divisor != 1:
            raise ValueError("normal must be nonzero and primitive")
        object.__setattr__(self, "components", values)

    @classmethod
    def from_integer(cls, components: Sequence[int]) -> "PrimitiveNormal":
        values = _integer_vector(components, "normal")
        divisor = math.gcd(*(abs(value) for value in values))
        if divisor == 0:
            raise ValueError("normal must be nonzero")
        return cls(tuple(value // divisor for value in values))

    @classmethod
    def from_rational(cls, components: Sequence[Fraction]) -> "PrimitiveNormal":
        values = tuple(components)
        if not values:
            raise ValueError("normal must be nonempty")
        if any(isinstance(value, float) for value in values):
            raise TypeError("rational normals must not contain floats")
        try:
            fractions = tuple(Fraction(value) for value in values)
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise TypeError("rational normal entries must be exact rational numbers") from error
        denominator = math.lcm(*(value.denominator for value in fractions))
        integers = tuple(value.numerator * (denominator // value.denominator) for value in fractions)
        return cls.from_integer(integers)

    @property
    def dimension(self) -> int:
        return len(self.components)

    @property
    def opposite(self) -> "PrimitiveNormal":
        return PrimitiveNormal(tuple(-value for value in self.components))

    @property
    def unoriented_key(self) -> IntegerVector:
        first = next(value for value in self.components if value)
        return self.components if first > 0 else self.opposite.components

    def dot(self, vector: Sequence[int]) -> int:
        values = _integer_vector(vector, "lattice vector")
        if len(values) != self.dimension:
            raise ValueError("normal and lattice vector dimensions differ")
        return sum(left * right for left, right in zip(self.components, values))

    def compare(self, other: "PrimitiveNormal") -> OrientationRelation:
        return compare_orientations(self, other)

    def to_canonical_dict(self) -> dict:
        return {"components": self.components, "schema": self.SCHEMA_ID}


def compare_orientations(
    left: PrimitiveNormal, right: PrimitiveNormal
) -> OrientationRelation:
    if left.dimension != right.dimension:
        raise ValueError("cannot compare normals of different dimensions")
    if left.components == right.components:
        return OrientationRelation.SAME
    if left.components == right.opposite.components:
        return OrientationRelation.OPPOSITE
    return OrientationRelation.NONPARALLEL


@dataclass(frozen=True)
class UnimodularBasisCertificate:
    determinant: int
    normal_action: IntegerVector
    inverse_matrix: IntegerMatrix

    SCHEMA_ID = "mobility_toolkit.unimodular_basis_certificate.v1"

    @property
    def verified(self) -> bool:
        expected = (0,) * (len(self.normal_action) - 1) + (1,)
        return abs(self.determinant) == 1 and self.normal_action == expected

    def to_canonical_dict(self) -> dict:
        return {
            "determinant": self.determinant,
            "inverse_matrix": self.inverse_matrix,
            "normal_action": self.normal_action,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class UnimodularBasisChange:
    """A certified integer basis adapted to an oriented hyperplane."""

    normal: PrimitiveNormal
    matrix: IntegerMatrix

    SCHEMA_ID = "mobility_toolkit.unimodular_basis_change.v1"

    def __post_init__(self) -> None:
        matrix = tuple(tuple(row) for row in self.matrix)
        size = self.normal.dimension
        if len(matrix) != size or any(len(row) != size for row in matrix):
            raise ValueError("basis-change matrix dimension mismatch")
        if any(isinstance(value, bool) or not isinstance(value, int) for row in matrix for value in row):
            raise TypeError("basis-change matrix entries must be integers")
        determinant = _determinant(matrix)
        if abs(determinant) != 1:
            raise ValueError("basis-change matrix must be unimodular")
        action = tuple(
            sum(self.normal.components[row] * matrix[row][column] for row in range(size))
            for column in range(size)
        )
        if action != (0,) * (size - 1) + (1,):
            raise ValueError("basis is not adapted to the declared oriented normal")
        object.__setattr__(self, "matrix", matrix)

    @classmethod
    def adapted_to(cls, normal: PrimitiveNormal) -> "UnimodularBasisChange":
        size = normal.dimension
        if size == 1:
            return cls(normal, ((normal.components[0],),))
        # Column operations reduce the primitive row normal to (1, 0, ...).
        matrix = [[int(row == column) for column in range(size)] for row in range(size)]
        reduced = list(normal.components)
        for column in range(1, size):
            left, right = reduced[0], reduced[column]
            divisor, bezout_left, bezout_right = _extended_gcd(left, right)
            if divisor == 0:
                continue
            old_left = [matrix[row][0] for row in range(size)]
            old_right = [matrix[row][column] for row in range(size)]
            for row in range(size):
                matrix[row][0] = (
                    bezout_left * old_left[row] + bezout_right * old_right[row]
                )
                matrix[row][column] = (
                    -(right // divisor) * old_left[row]
                    + (left // divisor) * old_right[row]
                )
            reduced[0], reduced[column] = divisor, 0
        if reduced[0] == -1:
            for row in range(size):
                matrix[row][0] = -matrix[row][0]
            reduced[0] = 1
        if reduced != [1] + [0] * (size - 1):
            raise ArithmeticError("failed to complete primitive normal to a lattice basis")
        # Put the positive-depth vector last; all preceding columns are tangent.
        for row in range(size):
            matrix[row][0], matrix[row][-1] = matrix[row][-1], matrix[row][0]
        return cls(normal, tuple(tuple(row) for row in matrix))

    @property
    def inverse_matrix(self) -> IntegerMatrix:
        return _integer_inverse(self.matrix)

    @property
    def tangent_basis(self) -> Tuple[IntegerVector, ...]:
        return tuple(
            tuple(self.matrix[row][column] for row in range(self.normal.dimension))
            for column in range(self.normal.dimension - 1)
        )

    @property
    def transverse_vector(self) -> IntegerVector:
        column = self.normal.dimension - 1
        return tuple(self.matrix[row][column] for row in range(self.normal.dimension))

    @property
    def certificate(self) -> UnimodularBasisCertificate:
        action = tuple(
            sum(
                self.normal.components[row] * self.matrix[row][column]
                for row in range(self.normal.dimension)
            )
            for column in range(self.normal.dimension)
        )
        return UnimodularBasisCertificate(
            _determinant(self.matrix), action, self.inverse_matrix
        )

    def to_boundary_coordinates(self, vector: Sequence[int]) -> IntegerVector:
        values = _integer_vector(vector, "lattice vector")
        if len(values) != self.normal.dimension:
            raise ValueError("basis and lattice vector dimensions differ")
        return _matrix_vector(self.inverse_matrix, values)

    def from_boundary_coordinates(self, coordinates: Sequence[int]) -> IntegerVector:
        values = _integer_vector(coordinates, "boundary coordinates")
        if len(values) != self.normal.dimension:
            raise ValueError("basis and boundary-coordinate dimensions differ")
        return _matrix_vector(self.matrix, values)

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "matrix": self.matrix,
            "normal": self.normal,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class OrientedHalfSpace:
    normal: PrimitiveNormal
    boundary_offset: int = 0

    SCHEMA_ID = "mobility_toolkit.oriented_half_space.v1"

    def __post_init__(self) -> None:
        if isinstance(self.boundary_offset, bool) or not isinstance(self.boundary_offset, int):
            raise TypeError("boundary offset must be an integer")

    @property
    def basis_change(self) -> UnimodularBasisChange:
        return UnimodularBasisChange.adapted_to(self.normal)

    def depth(self, point: Sequence[int]) -> int:
        return self.normal.dot(point) - self.boundary_offset

    def contains(self, point: Sequence[int]) -> bool:
        return self.depth(point) >= 0

    @property
    def opposite(self) -> "OrientedHalfSpace":
        return OrientedHalfSpace(self.normal.opposite, -self.boundary_offset)

    def compare_orientation(self, other: "OrientedHalfSpace") -> OrientationRelation:
        return self.normal.compare(other.normal)

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_offset": self.boundary_offset,
            "normal": self.normal,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True, order=True)
class SemigroupCoordinate:
    tangent: IntegerVector
    depth: int

    SCHEMA_ID = "mobility_toolkit.halfspace_semigroup_coordinate.v1"

    def __post_init__(self) -> None:
        tangent = tuple(self.tangent)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in tangent):
            raise TypeError("tangent coordinates must be integers")
        if isinstance(self.depth, bool) or not isinstance(self.depth, int):
            raise TypeError("semigroup depth must be an integer")
        if self.depth < 0:
            raise ValueError("one-sided semigroup depth must be nonnegative")
        object.__setattr__(self, "tangent", tangent)

    def __add__(self, other: "SemigroupCoordinate") -> "SemigroupCoordinate":
        if len(self.tangent) != len(other.tangent):
            raise ValueError("semigroup-coordinate ranks differ")
        return SemigroupCoordinate(
            tuple(left + right for left, right in zip(self.tangent, other.tangent)),
            self.depth + other.depth,
        )

    def to_canonical_dict(self) -> dict:
        return {"depth": self.depth, "schema": self.SCHEMA_ID, "tangent": self.tangent}


@dataclass(frozen=True)
class HalfSpaceSemigroup:
    """The exact lattice semigroup ``Z^(d-1) x N`` for an orientation."""

    half_space: OrientedHalfSpace
    basis_change: UnimodularBasisChange

    SCHEMA_ID = "mobility_toolkit.halfspace_semigroup.v1"

    def __post_init__(self) -> None:
        if self.basis_change.normal != self.half_space.normal:
            raise ValueError("semigroup basis and half-space normal differ")

    @classmethod
    def create(cls, half_space: OrientedHalfSpace) -> "HalfSpaceSemigroup":
        return cls(half_space, half_space.basis_change)

    @property
    def tangent_rank(self) -> int:
        return self.half_space.normal.dimension - 1

    def coordinates(self, displacement: Sequence[int]) -> SemigroupCoordinate:
        values = self.basis_change.to_boundary_coordinates(displacement)
        # A semigroup describes displacements from a boundary-plane lattice
        # anchor, hence the affine offset does not enter this dot product.
        depth = values[-1]
        return SemigroupCoordinate(values[:-1], depth)

    def ambient(self, coordinate: SemigroupCoordinate) -> IntegerVector:
        if len(coordinate.tangent) != self.tangent_rank:
            raise ValueError("semigroup-coordinate tangent rank mismatch")
        return self.basis_change.from_boundary_coordinates(
            coordinate.tangent + (coordinate.depth,)
        )

    def contains_displacement(self, displacement: Sequence[int]) -> bool:
        return self.half_space.normal.dot(displacement) >= 0

    def support_descriptor(
        self, displacements: Iterable[Sequence[int]]
    ) -> "OneSidedSupportDescriptor":
        return OneSidedSupportDescriptor(self, tuple(tuple(item) for item in displacements))

    def to_canonical_dict(self) -> dict:
        return {
            "basis_change": self.basis_change,
            "half_space": self.half_space,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class OneSidedSupportDescriptor:
    semigroup: HalfSpaceSemigroup
    ambient_displacements: Tuple[IntegerVector, ...]

    SCHEMA_ID = "mobility_toolkit.one_sided_support_descriptor.v1"

    def __post_init__(self) -> None:
        rank = self.semigroup.half_space.normal.dimension
        values = tuple(sorted(set(tuple(item) for item in self.ambient_displacements)))
        if not values:
            raise ValueError("support descriptor must contain at least one displacement")
        for value in values:
            _integer_vector(value, "support displacement")
            if len(value) != rank:
                raise ValueError("support displacement rank mismatch")
            if not self.semigroup.contains_displacement(value):
                raise ValueError("support displacement lies outside the one-sided semigroup")
        object.__setattr__(self, "ambient_displacements", values)

    @property
    def coordinates(self) -> Tuple[SemigroupCoordinate, ...]:
        return tuple(self.semigroup.coordinates(value) for value in self.ambient_displacements)

    @property
    def depth_interval(self) -> Tuple[int, int]:
        depths = tuple(item.depth for item in self.coordinates)
        return min(depths), max(depths)

    @property
    def tangent_intervals(self) -> Tuple[Tuple[int, int], ...]:
        if self.semigroup.tangent_rank == 0:
            return ()
        coordinates = self.coordinates
        return tuple(
            (
                min(item.tangent[axis] for item in coordinates),
                max(item.tangent[axis] for item in coordinates),
            )
            for axis in range(self.semigroup.tangent_rank)
        )

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_displacements": self.ambient_displacements,
            "coordinates": self.coordinates,
            "depth_interval": self.depth_interval,
            "schema": self.SCHEMA_ID,
            "semigroup": self.semigroup,
            "tangent_intervals": self.tangent_intervals,
        }


__all__ = [
    "HalfSpaceSemigroup",
    "OneSidedSupportDescriptor",
    "OrientationRelation",
    "OrientedHalfSpace",
    "PrimitiveNormal",
    "SemigroupCoordinate",
    "UnimodularBasisCertificate",
    "UnimodularBasisChange",
    "compare_orientations",
]
