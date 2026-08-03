"""Certified finite generalized-stabilizer analysis with central phases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.core.pauli import PauliModule, PauliOperator
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import (
    FiniteAbelianGroup,
    FiniteSubgroup,
)
from mobility_toolkit.finite.pauli import FinitePauliCoordinates
from mobility_toolkit.finite.pairing import PairedFiniteAbelianGroup, PairedFiniteQuotient


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


def _binary_coefficient_relation_lattice(
    generator_matrix: SparseIntMatrix,
) -> SparseIntMatrix:
    """Exact kernel lattice for a map from Z^m to (Z/2)^n.

    Binary column elimination is lifted with the same unimodular integer
    column operations.  If ``A U = [B 0]`` over GF(2), with the first ``r``
    columns independent, then

        U diag(2 I_r, I_{m-r})

    is an integer basis for ``{c in Z^m : A c = 0 mod 2}``.
    """

    count = generator_matrix.ncols
    binary_columns = [0] * count
    for row, column, value in generator_matrix.entries:
        if value % 2:
            binary_columns[column] ^= 1 << row
    transform_columns = [
        [int(row == column) for row in range(count)]
        for column in range(count)
    ]

    rank = 0
    for row in range(generator_matrix.nrows):
        pivot = next(
            (
                column
                for column in range(rank, count)
                if binary_columns[column] & (1 << row)
            ),
            None,
        )
        if pivot is None:
            continue
        binary_columns[rank], binary_columns[pivot] = (
            binary_columns[pivot],
            binary_columns[rank],
        )
        transform_columns[rank], transform_columns[pivot] = (
            transform_columns[pivot],
            transform_columns[rank],
        )
        for column in range(count):
            if column == rank or not (
                binary_columns[column] & (1 << row)
            ):
                continue
            binary_columns[column] ^= binary_columns[rank]
            transform_columns[column] = [
                left - right
                for left, right in zip(
                    transform_columns[column],
                    transform_columns[rank],
                )
            ]
        rank += 1
        if rank == count:
            break

    if any(binary_columns[column] for column in range(rank, count)):
        raise ArithmeticError("binary column elimination failed to isolate the kernel")
    entries = []
    for column, transform in enumerate(transform_columns):
        scale = 2 if column < rank else 1
        entries.extend(
            (row, column, scale * value)
            for row, value in enumerate(transform)
            if value
        )
    return SparseIntMatrix(count, count, tuple(entries))


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
    logical_module: PairedFiniteQuotient
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
            "logical_projective_order": self.logical_projective_order,
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
        if all(order == 2 for order in coordinates.coordinate_orders):
            coefficient_relations = _binary_coefficient_relation_lattice(
                generator_matrix
            )
        else:
            ambient_relations = SparseIntMatrix.diagonal(
                coordinates.coordinate_orders
            )
            relation_equations = SparseIntMatrix.hstack(
                generator_matrix, ambient_relations.negate()
            )
            relation_kernel = backend.integer_kernel(relation_equations).basis
            coefficient_relations = relation_kernel.select_rows(
                tuple(range(count))
            )
            coefficient_relations = backend.column_lattice_basis(
                coefficient_relations
            ).basis
            if coefficient_relations.ncols != count:
                raise ArithmeticError(
                    "stabilizer coefficient-relation lattice is not full rank"
                )
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
    paired_paulis = PairedFiniteAbelianGroup.create(
        ambient,
        modulus,
        coordinates.pairing_matrix,
    )
    centralizer = paired_paulis.orthogonal_complement(stabilizer, backend)
    if not centralizer.contains_subgroup(stabilizer, backend):
        raise ArithmeticError("validated stabilizer is not contained in its centralizer")

    logical = paired_paulis.quotient_pairing(centralizer, stabilizer, backend)
    stabilizer_order = stabilizer.order(backend)
    if module.hilbert_dimension % stabilizer_order:
        raise ArithmeticError("stabilizer order does not divide Hilbert dimension")
    codespace_dimension = module.hilbert_dimension // stabilizer_order
    if logical.order != codespace_dimension * codespace_dimension:
        raise ArithmeticError("logical Pauli order does not equal K squared")

    return FiniteStabilizerAnalysis(
        module,
        coordinates,
        ambient,
        validation,
        stabilizer,
        centralizer,
        logical,
        codespace_dimension,
    )


__all__ = [
    "FiniteStabilizerAnalysis",
    "InvalidStabilizerGroup",
    "StabilizerValidation",
    "analyze_finite_stabilizer",
    "validate_stabilizer_generators",
]
