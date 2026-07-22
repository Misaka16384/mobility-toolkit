"""Certified finite generalized-stabilizer analysis with central phases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.core.pauli import PauliModule, PauliOperator
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import (
    FiniteAbelianGroup,
    FiniteQuotient,
    FiniteSubgroup,
)
from mobility_toolkit.finite.pauli import FinitePauliCoordinates


class InvalidStabilizerGroup(ValueError):
    """Raised when proposed generators do not define a scalar-free stabilizer."""


def _columns(matrix: SparseIntMatrix) -> Tuple[Tuple[int, ...], ...]:
    rows = matrix.to_rows()
    return tuple(
        tuple(rows[row][column] for row in range(matrix.nrows))
        for column in range(matrix.ncols)
    )


def _matrix_mod(matrix: SparseIntMatrix, modulus: int) -> SparseIntMatrix:
    return SparseIntMatrix(
        matrix.nrows,
        matrix.ncols,
        tuple((row, column, value % modulus) for row, column, value in matrix.entries),
    )


@dataclass(frozen=True)
class StabilizerValidation:
    generator_matrix: SparseIntMatrix
    coefficient_relation_lattice: SparseIntMatrix
    relation_scalar_phases: Tuple[int, ...]
    commutator_matrix: SparseIntMatrix
    errors: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.stabilizer_validation.v1"

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_relation_lattice": self.coefficient_relation_lattice,
            "commutator_matrix": self.commutator_matrix,
            "errors": self.errors,
            "generator_matrix": self.generator_matrix,
            "relation_scalar_phases": self.relation_scalar_phases,
            "schema": self.SCHEMA_ID,
            "valid": self.valid,
        }


@dataclass(frozen=True)
class FiniteStabilizerAnalysis:
    module: PauliModule
    coordinates: FinitePauliCoordinates
    ambient_projective_paulis: FiniteAbelianGroup
    validation: StabilizerValidation
    stabilizer: FiniteSubgroup
    centralizer: FiniteSubgroup
    logical_module: FiniteQuotient
    logical_presentation_representatives: SparseIntMatrix
    logical_presentation_pairing_matrix: SparseIntMatrix
    codespace_dimension: int

    SCHEMA_ID = "mobility_toolkit.finite_stabilizer_analysis.v1"

    @property
    def logical_invariant_factors(self) -> Tuple[int, ...]:
        return self.logical_module.invariant_factors

    @property
    def logical_projective_order(self) -> int:
        return self.logical_module.order

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_projective_paulis": self.ambient_projective_paulis,
            "centralizer": self.centralizer,
            "codespace_dimension": self.codespace_dimension,
            "coordinates": self.coordinates,
            "logical_invariant_factors": self.logical_invariant_factors,
            "logical_module": self.logical_module,
            "logical_presentation_pairing_matrix": self.logical_presentation_pairing_matrix,
            "logical_projective_order": self.logical_projective_order,
            "logical_presentation_representatives": self.logical_presentation_representatives,
            "module": self.module,
            "schema": self.SCHEMA_ID,
            "stabilizer": self.stabilizer,
            "validation": self.validation,
        }


def validate_stabilizer_generators(
    module: PauliModule,
    generators: Sequence[PauliOperator],
    backend: FiniteIntegerBackend,
) -> StabilizerValidation:
    generators = tuple(generators)
    if any(generator.module != module for generator in generators):
        raise ValueError("all stabilizer generators must belong to the supplied module")
    coordinates = FinitePauliCoordinates.from_module(module)
    generator_matrix = coordinates.generator_matrix(generators)
    modulus = module.phase_modulus
    commutator_matrix = _matrix_mod(
        generator_matrix.transpose()
        .matmul(coordinates.pairing_matrix)
        .matmul(generator_matrix),
        modulus,
    )
    errors = []
    if commutator_matrix.entries:
        errors.append("generators do not commute projectively")

    count = len(generators)
    if count:
        ambient_relations = SparseIntMatrix.diagonal(coordinates.coordinate_orders)
        relation_equations = SparseIntMatrix.hstack(
            generator_matrix, ambient_relations.negate()
        )
        relation_kernel = backend.integer_kernel(relation_equations).basis
        coefficient_relations = relation_kernel.select_rows(tuple(range(count)))
        coefficient_relations = backend.column_lattice_basis(
            coefficient_relations
        ).basis
        if coefficient_relations.ncols != count:
            raise ArithmeticError("stabilizer coefficient-relation lattice is not full rank")
    else:
        coefficient_relations = SparseIntMatrix.zero(0, 0)

    relation_phases = []
    for relation in _columns(coefficient_relations):
        product = module.identity()
        for generator, coefficient in zip(generators, relation):
            product = product * generator.power(coefficient)
        if not product.is_projective_identity:
            raise ArithmeticError("coefficient relation failed to close projectively")
        relation_phases.append(product.scalar_phase)
    if any(relation_phases):
        errors.append("generator relations produce a nontrivial scalar")

    return StabilizerValidation(
        generator_matrix,
        coefficient_relations,
        tuple(relation_phases),
        commutator_matrix,
        tuple(errors),
    )


def analyze_finite_stabilizer(
    module: PauliModule,
    generators: Sequence[PauliOperator],
    backend: FiniteIntegerBackend,
) -> FiniteStabilizerAnalysis:
    """Analyze an exact finite stabilizer group and its logical Pauli module."""

    generators = tuple(generators)
    coordinates = FinitePauliCoordinates.from_module(module)
    ambient = coordinates.ambient_group(backend)
    validation = validate_stabilizer_generators(module, generators, backend)
    if not validation.valid:
        raise InvalidStabilizerGroup("; ".join(validation.errors))

    stabilizer = ambient.subgroup(validation.generator_matrix, backend)
    modulus = module.phase_modulus
    constraints = stabilizer.preimage_lattice_basis.transpose().matmul(
        coordinates.pairing_matrix
    )
    constraint_kernel = backend.integer_kernel(
        SparseIntMatrix.hstack(
            constraints,
            SparseIntMatrix.diagonal((modulus,) * coordinates.rank).negate(),
        )
    ).basis
    centralizer_generators = constraint_kernel.select_rows(
        tuple(range(coordinates.rank))
    )
    centralizer = ambient.subgroup(centralizer_generators, backend)
    if not centralizer.contains_subgroup(stabilizer, backend):
        raise ArithmeticError("validated stabilizer is not contained in its centralizer")

    logical = centralizer.quotient_by(stabilizer, backend)
    stabilizer_order = stabilizer.order(backend)
    if module.hilbert_dimension % stabilizer_order:
        raise ArithmeticError("stabilizer order does not divide Hilbert dimension")
    codespace_dimension = module.hilbert_dimension // stabilizer_order
    if logical.order != codespace_dimension * codespace_dimension:
        raise ArithmeticError("logical Pauli order does not equal K squared")

    representatives = centralizer.preimage_lattice_basis
    logical_pairing = _matrix_mod(
        representatives.transpose()
        .matmul(coordinates.pairing_matrix)
        .matmul(representatives),
        modulus,
    )
    return FiniteStabilizerAnalysis(
        module,
        coordinates,
        ambient,
        validation,
        stabilizer,
        centralizer,
        logical,
        representatives,
        logical_pairing,
        codespace_dimension,
    )


__all__ = [
    "FiniteStabilizerAnalysis",
    "InvalidStabilizerGroup",
    "StabilizerValidation",
    "analyze_finite_stabilizer",
    "validate_stabilizer_generators",
]
