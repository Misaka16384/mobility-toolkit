"""Immutable integer-matrix and module-presentation contracts.

This module defines representation and validation only. Certified HNF/SNF,
integer kernels, subgroup intersections, and quotient algorithms belong to the
finite backend introduced in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

MatrixEntry = Tuple[int, int, int]


def _require_plain_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@dataclass(frozen=True)
class SparseIntMatrix:
    """Canonical sorted-COO integer matrix.

    Vectors are columns. A matrix with shape ``(m, n)`` represents a map from
    ``Z^n`` to ``Z^m``.
    """

    nrows: int
    ncols: int
    entries: Tuple[MatrixEntry, ...] = ()

    SCHEMA_ID = "mobility_toolkit.sparse_int_matrix.v1"

    def __post_init__(self) -> None:
        nrows = _require_plain_int(self.nrows, "nrows")
        ncols = _require_plain_int(self.ncols, "ncols")
        if nrows < 0 or ncols < 0:
            raise ValueError("matrix dimensions must be nonnegative")

        combined = {}
        for raw_entry in self.entries:
            if len(raw_entry) != 3:
                raise ValueError("each matrix entry must be (row, column, value)")
            row = _require_plain_int(raw_entry[0], "row")
            column = _require_plain_int(raw_entry[1], "column")
            value = _require_plain_int(raw_entry[2], "value")
            if not (0 <= row < nrows and 0 <= column < ncols):
                raise ValueError(f"matrix entry {(row, column)} is out of bounds")
            combined[(row, column)] = combined.get((row, column), 0) + value

        normalized = tuple(
            (row, column, value)
            for (row, column), value in sorted(combined.items())
            if value != 0
        )
        object.__setattr__(self, "entries", normalized)

    @classmethod
    def zero(cls, nrows: int, ncols: int) -> "SparseIntMatrix":
        return cls(nrows=nrows, ncols=ncols)

    @classmethod
    def identity(cls, size: int) -> "SparseIntMatrix":
        _require_plain_int(size, "size")
        if size < 0:
            raise ValueError("size must be nonnegative")
        return cls(size, size, tuple((i, i, 1) for i in range(size)))

    @classmethod
    def diagonal(cls, values: Sequence[int]) -> "SparseIntMatrix":
        normalized = tuple(_require_plain_int(value, "diagonal value") for value in values)
        size = len(normalized)
        return cls(size, size, tuple((i, i, value) for i, value in enumerate(normalized)))

    @classmethod
    def from_rows(cls, rows: Sequence[Sequence[int]]) -> "SparseIntMatrix":
        materialized = tuple(tuple(row) for row in rows)
        if not materialized:
            return cls(0, 0)
        ncols = len(materialized[0])
        if any(len(row) != ncols for row in materialized):
            raise ValueError("all matrix rows must have equal length")
        entries = []
        for row_index, row in enumerate(materialized):
            for column_index, value in enumerate(row):
                value = _require_plain_int(value, "matrix value")
                if value:
                    entries.append((row_index, column_index, value))
        return cls(len(materialized), ncols, tuple(entries))

    def to_rows(self) -> Tuple[Tuple[int, ...], ...]:
        rows = [[0 for _ in range(self.ncols)] for _ in range(self.nrows)]
        for row, column, value in self.entries:
            rows[row][column] = value
        return tuple(tuple(row) for row in rows)

    def transpose(self) -> "SparseIntMatrix":
        return SparseIntMatrix(
            self.ncols,
            self.nrows,
            tuple((column, row, value) for row, column, value in self.entries),
        )

    def negate(self) -> "SparseIntMatrix":
        return SparseIntMatrix(
            self.nrows,
            self.ncols,
            tuple((row, column, -value) for row, column, value in self.entries),
        )

    @classmethod
    def hstack(cls, *matrices: "SparseIntMatrix") -> "SparseIntMatrix":
        if not matrices:
            return cls.zero(0, 0)
        nrows = matrices[0].nrows
        if any(matrix.nrows != nrows for matrix in matrices):
            raise ValueError("horizontal stack requires equal row counts")
        entries = []
        column_offset = 0
        for matrix in matrices:
            entries.extend(
                (row, column + column_offset, value)
                for row, column, value in matrix.entries
            )
            column_offset += matrix.ncols
        return cls(nrows, column_offset, tuple(entries))

    @classmethod
    def vstack(cls, *matrices: "SparseIntMatrix") -> "SparseIntMatrix":
        if not matrices:
            return cls.zero(0, 0)
        ncols = matrices[0].ncols
        if any(matrix.ncols != ncols for matrix in matrices):
            raise ValueError("vertical stack requires equal column counts")
        entries = []
        row_offset = 0
        for matrix in matrices:
            entries.extend(
                (row + row_offset, column, value)
                for row, column, value in matrix.entries
            )
            row_offset += matrix.nrows
        return cls(row_offset, ncols, tuple(entries))

    def select_rows(self, rows: Sequence[int]) -> "SparseIntMatrix":
        rows = tuple(_require_plain_int(row, "row") for row in rows)
        if len(set(rows)) != len(rows) or any(row < 0 or row >= self.nrows for row in rows):
            raise ValueError("selected rows must be unique valid indices")
        row_map = {old: new for new, old in enumerate(rows)}
        return SparseIntMatrix(
            len(rows),
            self.ncols,
            tuple(
                (row_map[row], column, value)
                for row, column, value in self.entries
                if row in row_map
            ),
        )

    def select_columns(self, columns: Sequence[int]) -> "SparseIntMatrix":
        columns = tuple(_require_plain_int(column, "column") for column in columns)
        if len(set(columns)) != len(columns) or any(
            column < 0 or column >= self.ncols for column in columns
        ):
            raise ValueError("selected columns must be unique valid indices")
        column_map = {old: new for new, old in enumerate(columns)}
        return SparseIntMatrix(
            self.nrows,
            len(columns),
            tuple(
                (row, column_map[column], value)
                for row, column, value in self.entries
                if column in column_map
            ),
        )

    def matmul(self, other: "SparseIntMatrix") -> "SparseIntMatrix":
        if self.ncols != other.nrows:
            raise ValueError(
                f"matrix shape mismatch: {(self.nrows, self.ncols)} cannot multiply "
                f"{(other.nrows, other.ncols)}"
            )
        left_by_inner = {}
        right_by_inner = {}
        for row, inner, value in self.entries:
            left_by_inner.setdefault(inner, []).append((row, value))
        for inner, column, value in other.entries:
            right_by_inner.setdefault(inner, []).append((column, value))
        accumulated = {}
        for inner, left_items in left_by_inner.items():
            for row, left_value in left_items:
                for column, right_value in right_by_inner.get(inner, ()):
                    key = (row, column)
                    accumulated[key] = accumulated.get(key, 0) + left_value * right_value
        return SparseIntMatrix(
            self.nrows,
            other.ncols,
            tuple((row, column, value) for (row, column), value in accumulated.items()),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "entries": self.entries,
            "ncols": self.ncols,
            "nrows": self.nrows,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PresentedModule:
    """A module ``Z^ambient_rank / image(relations)``."""

    ambient_rank: int
    relations: SparseIntMatrix
    coordinate_labels: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.presented_module.v1"

    def __post_init__(self) -> None:
        ambient_rank = _require_plain_int(self.ambient_rank, "ambient_rank")
        if ambient_rank < 0:
            raise ValueError("ambient_rank must be nonnegative")
        if self.relations.nrows != ambient_rank:
            raise ValueError("relation matrix rows must equal ambient_rank")
        labels = tuple(self.coordinate_labels)
        if labels and len(labels) != ambient_rank:
            raise ValueError("coordinate_labels must be empty or match ambient_rank")
        if any(not isinstance(label, str) or not label for label in labels):
            raise ValueError("coordinate labels must be nonempty strings")
        if len(set(labels)) != len(labels):
            raise ValueError("coordinate labels must be unique")
        object.__setattr__(self, "coordinate_labels", labels)

    @classmethod
    def free(cls, rank: int, coordinate_labels: Sequence[str] = ()) -> "PresentedModule":
        return cls(rank, SparseIntMatrix.zero(rank, 0), tuple(coordinate_labels))

    @classmethod
    def from_invariant_factors(
        cls, factors: Sequence[int], coordinate_labels: Sequence[str] = ()
    ) -> "PresentedModule":
        normalized = tuple(_require_plain_int(value, "invariant factor") for value in factors)
        if any(value <= 1 for value in normalized):
            raise ValueError("finite invariant factors must be greater than one")
        if any(right % left != 0 for left, right in zip(normalized, normalized[1:])):
            raise ValueError("invariant factors must form a divisibility chain")
        return cls(len(normalized), SparseIntMatrix.diagonal(normalized), tuple(coordinate_labels))

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_rank": self.ambient_rank,
            "coordinate_labels": self.coordinate_labels,
            "relations": self.relations,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class ModuleMap:
    """A lifted integer matrix between presented modules.

    When supplied, ``relation_witness`` proves
    ``matrix * source.relations = target.relations * relation_witness``.
    """

    source: PresentedModule
    target: PresentedModule
    matrix: SparseIntMatrix
    relation_witness: Optional[SparseIntMatrix] = None

    SCHEMA_ID = "mobility_toolkit.module_map.v1"

    def __post_init__(self) -> None:
        expected_shape = (self.target.ambient_rank, self.source.ambient_rank)
        if (self.matrix.nrows, self.matrix.ncols) != expected_shape:
            raise ValueError(f"map matrix must have shape {expected_shape}")
        witness = self.relation_witness
        if witness is None:
            return
        expected_witness_shape = (
            self.target.relations.ncols,
            self.source.relations.ncols,
        )
        if (witness.nrows, witness.ncols) != expected_witness_shape:
            raise ValueError(f"relation witness must have shape {expected_witness_shape}")
        left = self.matrix.matmul(self.source.relations)
        right = self.target.relations.matmul(witness)
        if left != right:
            raise ValueError("relation witness does not prove a well-defined module map")

    @property
    def relations_verified(self) -> bool:
        return self.relation_witness is not None

    def to_canonical_dict(self) -> dict:
        return {
            "matrix": self.matrix,
            "relation_witness": self.relation_witness,
            "schema": self.SCHEMA_ID,
            "source": self.source,
            "target": self.target,
        }


@dataclass(frozen=True)
class Submodule:
    """Generators of a submodule of a presented ambient module."""

    ambient: PresentedModule
    generators: SparseIntMatrix
    generator_labels: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.submodule.v1"

    def __post_init__(self) -> None:
        if self.generators.nrows != self.ambient.ambient_rank:
            raise ValueError("submodule generator rows must equal the ambient rank")
        labels = tuple(self.generator_labels)
        if labels and len(labels) != self.generators.ncols:
            raise ValueError("generator_labels must be empty or match generator count")
        if any(not isinstance(label, str) or not label for label in labels):
            raise ValueError("generator labels must be nonempty strings")
        object.__setattr__(self, "generator_labels", labels)

    def to_canonical_dict(self) -> dict:
        return {
            "ambient": self.ambient,
            "generator_labels": self.generator_labels,
            "generators": self.generators,
            "schema": self.SCHEMA_ID,
        }


__all__ = [
    "MatrixEntry",
    "ModuleMap",
    "PresentedModule",
    "SparseIntMatrix",
    "Submodule",
]
