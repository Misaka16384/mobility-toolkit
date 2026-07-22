"""Finite abelian groups and subgroups via integer preimage lattices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from mobility_toolkit.core.integer import PresentedModule, SparseIntMatrix
from mobility_toolkit.finite.backend import (
    FiniteIntegerBackend,
    NotInLattice,
    SmithInvariantResult,
)


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _column(values: Sequence[int]) -> SparseIntMatrix:
    normalized = tuple(_integer(value, "coordinate") for value in values)
    return SparseIntMatrix(
        len(normalized),
        1,
        tuple((row, 0, value) for row, value in enumerate(normalized) if value),
    )


@dataclass(frozen=True)
class FiniteAbelianGroup:
    """A finite quotient ``Z^n / relation_lattice``."""

    relation_lattice_basis: SparseIntMatrix
    invariant_factors: Tuple[int, ...]
    coordinate_labels: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.finite_abelian_group.v1"

    def __post_init__(self) -> None:
        basis = self.relation_lattice_basis
        if basis.nrows != basis.ncols:
            raise ValueError("a finite group relation-lattice basis must be square")
        factors = tuple(_integer(value, "invariant factor") for value in self.invariant_factors)
        if any(value <= 1 for value in factors):
            raise ValueError("finite invariant factors must be greater than one")
        if any(right % left != 0 for left, right in zip(factors, factors[1:])):
            raise ValueError("invariant factors must form a divisibility chain")
        labels = tuple(self.coordinate_labels)
        if labels and len(labels) != basis.nrows:
            raise ValueError("coordinate labels must be empty or match the presentation rank")
        if any(not isinstance(label, str) or not label for label in labels):
            raise ValueError("coordinate labels must be nonempty strings")
        if len(set(labels)) != len(labels):
            raise ValueError("coordinate labels must be unique")
        object.__setattr__(self, "invariant_factors", factors)
        object.__setattr__(self, "coordinate_labels", labels)

    @classmethod
    def from_coordinate_orders(
        cls,
        orders: Sequence[int],
        backend: FiniteIntegerBackend,
        coordinate_labels: Sequence[str] = (),
    ) -> "FiniteAbelianGroup":
        orders = tuple(_integer(value, "coordinate order") for value in orders)
        if any(value <= 1 for value in orders):
            raise ValueError("coordinate orders must be greater than one")
        relations = SparseIntMatrix.diagonal(orders)
        smith = backend.smith_invariants(relations)
        return cls(relations, smith.torsion_invariants, tuple(coordinate_labels))

    @classmethod
    def from_invariant_factors(
        cls,
        factors: Sequence[int],
        backend: FiniteIntegerBackend,
        coordinate_labels: Sequence[str] = (),
    ) -> "FiniteAbelianGroup":
        factors = tuple(factors)
        group = cls.from_coordinate_orders(factors, backend, coordinate_labels)
        if group.invariant_factors != factors:
            raise ValueError("declared invariant factors are not canonical")
        return group

    @classmethod
    def from_presentation(
        cls, module: PresentedModule, backend: FiniteIntegerBackend
    ) -> "FiniteAbelianGroup":
        lattice = backend.column_lattice_basis(module.relations).basis
        if lattice.ncols != module.ambient_rank:
            raise ValueError("presented module has a free part and is not finite")
        smith = backend.smith_invariants(lattice)
        return cls(lattice, smith.torsion_invariants, module.coordinate_labels)

    @property
    def presentation_rank(self) -> int:
        return self.relation_lattice_basis.nrows

    def order(self, backend: FiniteIntegerBackend) -> int:
        return abs(backend.determinant(self.relation_lattice_basis))

    def trivial_subgroup(self, backend: FiniteIntegerBackend) -> "FiniteSubgroup":
        return FiniteSubgroup._from_preimage(self, self.relation_lattice_basis, backend)

    def whole_subgroup(self, backend: FiniteIntegerBackend) -> "FiniteSubgroup":
        return FiniteSubgroup._from_preimage(
            self, SparseIntMatrix.identity(self.presentation_rank), backend
        )

    def subgroup(
        self, generators: SparseIntMatrix, backend: FiniteIntegerBackend
    ) -> "FiniteSubgroup":
        if generators.nrows != self.presentation_rank:
            raise ValueError("subgroup generators have the wrong ambient rank")
        combined = SparseIntMatrix.hstack(self.relation_lattice_basis, generators)
        basis = backend.column_lattice_basis(combined).basis
        return FiniteSubgroup._from_preimage(self, basis, backend)

    def to_canonical_dict(self) -> dict:
        return {
            "coordinate_labels": self.coordinate_labels,
            "invariant_factors": self.invariant_factors,
            "relation_lattice_basis": self.relation_lattice_basis,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class MembershipWitness:
    coordinates: SparseIntMatrix

    def to_canonical_dict(self) -> dict:
        return {"coordinates": self.coordinates}


@dataclass(frozen=True)
class FiniteQuotient:
    numerator: "FiniteSubgroup"
    denominator: "FiniteSubgroup"
    inclusion_matrix: SparseIntMatrix
    smith: SmithInvariantResult

    @property
    def invariant_factors(self) -> Tuple[int, ...]:
        return self.smith.torsion_invariants

    @property
    def order(self) -> int:
        result = 1
        for value in self.invariant_factors:
            result *= value
        return result

    def to_canonical_dict(self) -> dict:
        return {
            "denominator": self.denominator,
            "inclusion_matrix": self.inclusion_matrix,
            "invariant_factors": self.invariant_factors,
            "numerator": self.numerator,
            "order": self.order,
            "smith": self.smith,
        }


@dataclass(frozen=True)
class FiniteSubgroup:
    """A subgroup represented by its full-rank preimage lattice in ``Z^n``."""

    ambient: FiniteAbelianGroup
    preimage_lattice_basis: SparseIntMatrix

    SCHEMA_ID = "mobility_toolkit.finite_subgroup.v1"

    @classmethod
    def _from_preimage(
        cls,
        ambient: FiniteAbelianGroup,
        basis: SparseIntMatrix,
        backend: FiniteIntegerBackend,
    ) -> "FiniteSubgroup":
        if basis.nrows != ambient.presentation_rank or basis.ncols != ambient.presentation_rank:
            raise ValueError("subgroup preimage lattice must be full-rank square")
        canonical = backend.column_lattice_basis(basis).basis
        if canonical.ncols != ambient.presentation_rank:
            raise ValueError("subgroup preimage lattice is not full rank")
        try:
            backend.solve_full_lattice(canonical, ambient.relation_lattice_basis)
        except NotInLattice as exc:
            raise ValueError("subgroup preimage does not contain ambient relations") from exc
        return cls(ambient, canonical)

    def order(self, backend: FiniteIntegerBackend) -> int:
        relation_det = abs(backend.determinant(self.ambient.relation_lattice_basis))
        preimage_det = abs(backend.determinant(self.preimage_lattice_basis))
        if preimage_det == 0 or relation_det % preimage_det:
            raise ArithmeticError("invalid subgroup determinant ratio")
        return relation_det // preimage_det

    def invariant_factors(self, backend: FiniteIntegerBackend) -> Tuple[int, ...]:
        return self.quotient_by(self.ambient.trivial_subgroup(backend), backend).invariant_factors

    def membership_witness(
        self, vector: Sequence[int], backend: FiniteIntegerBackend
    ) -> Optional[MembershipWitness]:
        if len(vector) != self.ambient.presentation_rank:
            raise ValueError("vector has the wrong ambient rank")
        try:
            coefficients = backend.solve_full_lattice(
                self.preimage_lattice_basis, _column(vector)
            )
        except NotInLattice:
            return None
        return MembershipWitness(coefficients)

    def contains(self, vector: Sequence[int], backend: FiniteIntegerBackend) -> bool:
        return self.membership_witness(vector, backend) is not None

    def contains_subgroup(
        self, other: "FiniteSubgroup", backend: FiniteIntegerBackend
    ) -> bool:
        self._require_same_ambient(other)
        try:
            backend.solve_full_lattice(
                self.preimage_lattice_basis, other.preimage_lattice_basis
            )
        except NotInLattice:
            return False
        return True

    def sum(
        self, other: "FiniteSubgroup", backend: FiniteIntegerBackend
    ) -> "FiniteSubgroup":
        self._require_same_ambient(other)
        basis = backend.column_lattice_basis(
            SparseIntMatrix.hstack(
                self.preimage_lattice_basis, other.preimage_lattice_basis
            )
        ).basis
        return FiniteSubgroup._from_preimage(self.ambient, basis, backend)

    def intersection(
        self, other: "FiniteSubgroup", backend: FiniteIntegerBackend
    ) -> "FiniteSubgroup":
        self._require_same_ambient(other)
        n = self.ambient.presentation_rank
        relation = SparseIntMatrix.hstack(
            self.preimage_lattice_basis, other.preimage_lattice_basis.negate()
        )
        kernel = backend.integer_kernel(relation).basis
        left_coefficients = kernel.select_rows(tuple(range(n)))
        generators = self.preimage_lattice_basis.matmul(left_coefficients)
        basis = backend.column_lattice_basis(generators).basis
        return FiniteSubgroup._from_preimage(self.ambient, basis, backend)

    def quotient_by(
        self, denominator: "FiniteSubgroup", backend: FiniteIntegerBackend
    ) -> FiniteQuotient:
        self._require_same_ambient(denominator)
        try:
            inclusion = backend.solve_full_lattice(
                self.preimage_lattice_basis, denominator.preimage_lattice_basis
            )
        except NotInLattice as exc:
            raise ValueError("quotient denominator is not a subgroup of the numerator") from exc
        smith = backend.smith_invariants(inclusion)
        quotient = FiniteQuotient(self, denominator, inclusion, smith)
        if quotient.order * denominator.order(backend) != self.order(backend):
            raise ArithmeticError("quotient order fails the subgroup order identity")
        return quotient

    def _require_same_ambient(self, other: "FiniteSubgroup") -> None:
        if not isinstance(other, FiniteSubgroup) or self.ambient != other.ambient:
            raise ValueError("finite subgroups belong to different ambient groups")

    def to_canonical_dict(self) -> dict:
        return {
            "ambient": self.ambient,
            "preimage_lattice_basis": self.preimage_lattice_basis,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class FiniteGroupHomomorphism:
    source: FiniteAbelianGroup
    target: FiniteAbelianGroup
    lift_matrix: SparseIntMatrix
    relation_witness: SparseIntMatrix

    SCHEMA_ID = "mobility_toolkit.finite_group_homomorphism.v1"

    @classmethod
    def create(
        cls,
        source: FiniteAbelianGroup,
        target: FiniteAbelianGroup,
        lift_matrix: SparseIntMatrix,
        backend: FiniteIntegerBackend,
    ) -> "FiniteGroupHomomorphism":
        if (lift_matrix.nrows, lift_matrix.ncols) != (
            target.presentation_rank,
            source.presentation_rank,
        ):
            raise ValueError("homomorphism lift has the wrong shape")
        image_of_relations = lift_matrix.matmul(source.relation_lattice_basis)
        try:
            witness = backend.solve_full_lattice(
                target.relation_lattice_basis, image_of_relations
            )
        except NotInLattice as exc:
            raise ValueError("lift matrix does not descend to the finite quotient") from exc
        if target.relation_lattice_basis.matmul(witness) != image_of_relations:
            raise ArithmeticError("homomorphism relation witness failed verification")
        return cls(source, target, lift_matrix, witness)

    def image(self, backend: FiniteIntegerBackend) -> FiniteSubgroup:
        return self.target.subgroup(self.lift_matrix, backend)

    def kernel(self, backend: FiniteIntegerBackend) -> FiniteSubgroup:
        relation = SparseIntMatrix.hstack(
            self.lift_matrix, self.target.relation_lattice_basis.negate()
        )
        integer_kernel = backend.integer_kernel(relation).basis
        source_coefficients = integer_kernel.select_rows(
            tuple(range(self.source.presentation_rank))
        )
        generators = SparseIntMatrix.hstack(
            self.source.relation_lattice_basis, source_coefficients
        )
        basis = backend.column_lattice_basis(generators).basis
        return FiniteSubgroup._from_preimage(self.source, basis, backend)

    def cokernel(self, backend: FiniteIntegerBackend) -> FiniteQuotient:
        return self.target.whole_subgroup(backend).quotient_by(self.image(backend), backend)

    def verify_first_isomorphism_order(self, backend: FiniteIntegerBackend) -> bool:
        kernel_order = self.kernel(backend).order(backend)
        image_order = self.image(backend).order(backend)
        return self.source.order(backend) == kernel_order * image_order

    def to_canonical_dict(self) -> dict:
        return {
            "lift_matrix": self.lift_matrix,
            "relation_witness": self.relation_witness,
            "schema": self.SCHEMA_ID,
            "source": self.source,
            "target": self.target,
        }


__all__ = [
    "FiniteAbelianGroup",
    "FiniteGroupHomomorphism",
    "FiniteQuotient",
    "FiniteSubgroup",
    "MembershipWitness",
]
