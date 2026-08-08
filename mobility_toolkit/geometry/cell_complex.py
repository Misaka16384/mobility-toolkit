"""Exact finite cell complexes, cubical constructors, and cellular codes."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence, Tuple

from mobility_toolkit.core.codes import StabilizerCodeSpec
from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.core.pauli import (
    LocalPauliTerm,
    LocalSystem,
    PauliModule,
    PauliOperator,
)
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import (
    FiniteAbelianGroup,
    FiniteGroupHomomorphism,
    FiniteQuotient,
)


@dataclass(frozen=True, order=True)
class CubicalCell:
    ambient_dimension: int
    varying_axes: Tuple[int, ...]
    base: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.cubical_cell.v1"

    def __post_init__(self) -> None:
        axes = tuple(self.varying_axes)
        base = tuple(self.base)
        if self.ambient_dimension < 1 or len(base) != self.ambient_dimension:
            raise ValueError("invalid cubical-cell ambient dimension")
        if axes != tuple(sorted(set(axes))) or any(
            axis < 0 or axis >= self.ambient_dimension for axis in axes
        ):
            raise ValueError("cubical-cell varying axes must be sorted and unique")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in base):
            raise TypeError("cubical-cell base coordinates must be integers")
        object.__setattr__(self, "varying_axes", axes)
        object.__setattr__(self, "base", base)

    @property
    def dimension(self) -> int:
        return len(self.varying_axes)

    @property
    def cell_id(self) -> str:
        axes = ",".join(str(axis) for axis in self.varying_axes)
        base = ",".join(str(value) for value in self.base)
        return f"cube:{self.ambient_dimension}:{self.dimension}:[{axes}]:[{base}]"

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_dimension": self.ambient_dimension,
            "base": self.base,
            "schema": self.SCHEMA_ID,
            "varying_axes": self.varying_axes,
        }


@dataclass(frozen=True)
class FiniteCellComplex:
    cell_ids_by_dimension: Tuple[Tuple[str, ...], ...]
    boundary_maps: Tuple[SparseIntMatrix, ...]
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.finite_cell_complex.v1"

    def __post_init__(self) -> None:
        cells = tuple(tuple(level) for level in self.cell_ids_by_dimension)
        if not cells:
            raise ValueError("finite cell complex needs at least dimension zero")
        if len(self.boundary_maps) != len(cells):
            raise ValueError("one boundary map is required per chain degree")
        for dimension, level in enumerate(cells):
            if tuple(sorted(set(level))) != level:
                raise ValueError("cell IDs must be sorted and unique within each degree")
            boundary = self.boundary_maps[dimension]
            expected_rows = 0 if dimension == 0 else len(cells[dimension - 1])
            if (boundary.nrows, boundary.ncols) != (expected_rows, len(level)):
                raise ValueError("cellular boundary map has the wrong shape")
            if dimension >= 2 and self.boundary_maps[dimension - 1].matmul(boundary).entries:
                raise ValueError("cell complex violates boundary squared equals zero")
        object.__setattr__(self, "cell_ids_by_dimension", cells)
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))

    @property
    def dimension(self) -> int:
        return len(self.cell_ids_by_dimension) - 1

    @property
    def cell_counts(self) -> Tuple[int, ...]:
        return tuple(len(level) for level in self.cell_ids_by_dimension)

    @property
    def euler_characteristic(self) -> int:
        return sum((-1) ** dimension * count for dimension, count in enumerate(self.cell_counts))

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "boundary_maps": self.boundary_maps,
            "cell_ids_by_dimension": self.cell_ids_by_dimension,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class CubicalComplex:
    chain_complex: FiniteCellComplex
    cells_by_dimension: Tuple[Tuple[CubicalCell, ...], ...]
    periodic_axes: Tuple[int, ...] = ()

    SCHEMA_ID = "mobility_toolkit.cubical_complex.v1"

    def __post_init__(self) -> None:
        ids = tuple(tuple(cell.cell_id for cell in level) for level in self.cells_by_dimension)
        if ids != self.chain_complex.cell_ids_by_dimension:
            raise ValueError("cubical cells disagree with chain-complex bases")

    @property
    def dimension(self) -> int:
        return self.chain_complex.dimension

    def to_canonical_dict(self) -> dict:
        return {
            "cells_by_dimension": self.cells_by_dimension,
            "chain_complex": self.chain_complex,
            "periodic_axes": self.periodic_axes,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class MaskTopologyDiagnostics:
    top_cell_count: int
    facet_connected_components: int
    pinched_top_cell_pairs: Tuple[Tuple[Tuple[int, ...], Tuple[int, ...]], ...]

    SCHEMA_ID = "mobility_toolkit.mask_topology_diagnostics.v1"

    @property
    def has_junctions(self) -> bool:
        return bool(self.pinched_top_cell_pairs)

    def to_canonical_dict(self) -> dict:
        return {
            "facet_connected_components": self.facet_connected_components,
            "has_junctions": self.has_junctions,
            "pinched_top_cell_pairs": self.pinched_top_cell_pairs,
            "schema": self.SCHEMA_ID,
            "top_cell_count": self.top_cell_count,
        }


def diagnose_cubical_mask(
    top_cells: Iterable[Sequence[int]],
) -> MaskTopologyDiagnostics:
    cells = tuple(sorted(set(tuple(cell) for cell in top_cells)))
    if not cells:
        raise ValueError("cubical mask diagnostics need at least one top cell")
    dimension = len(cells[0])
    if any(len(cell) != dimension for cell in cells):
        raise ValueError("cubical mask cells have inconsistent dimensions")
    cells_set = frozenset(cells)
    adjacency = {cell: set() for cell in cells}
    pinched = []

    # Calculate one half of all possible neighbor offsets (-1, 0, 1) in n-dimensions
    # to avoid double counting undirected edges.
    offsets = list(itertools.product((-1, 0, 1), repeat=dimension))
    half_offsets = []
    for offset in offsets:
        for val in offset:
            if val > 0:
                half_offsets.append(offset)
                break
            elif val < 0:
                break

    for cell in cells:
        for offset in half_offsets:
            neighbor = tuple(a + b for a, b in zip(cell, offset))
            if neighbor in cells_set:
                diff_count = sum(1 for val in offset if val != 0)
                if diff_count == 1:
                    adjacency[cell].add(neighbor)
                    adjacency[neighbor].add(cell)
                else:
                    pinched.append((cell, neighbor))

    component_count = 0
    unseen = set(cells)
    while unseen:
        component_count += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            neighbors = adjacency[current] & unseen
            unseen.difference_update(neighbors)
            stack.extend(neighbors)
    return MaskTopologyDiagnostics(
        len(cells), component_count, tuple(pinched)
    )


@dataclass(frozen=True, order=True)
class CellGluing:
    dimension: int
    source_cell_id: str
    target_cell_id: str
    orientation: int = 1

    SCHEMA_ID = "mobility_toolkit.cell_gluing.v1"

    def __post_init__(self) -> None:
        if self.dimension < 0 or self.orientation not in {-1, 1}:
            raise ValueError("invalid cell gluing dimension or orientation")
        if self.source_cell_id == self.target_cell_id and self.orientation == 1:
            raise ValueError("identity cell gluing is redundant")

    def to_canonical_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "orientation": self.orientation,
            "schema": self.SCHEMA_ID,
            "source_cell_id": self.source_cell_id,
            "target_cell_id": self.target_cell_id,
        }


@dataclass(frozen=True)
class BoundaryGluing:
    axis: int
    reverse_axes: Tuple[int, ...] = ()
    transverse_shifts: Tuple[int, ...] = ()
    gluing_id: str = ""

    SCHEMA_ID = "mobility_toolkit.boundary_gluing.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "reverse_axes", tuple(sorted(set(self.reverse_axes))))
        object.__setattr__(self, "transverse_shifts", tuple(self.transverse_shifts))

    def to_canonical_dict(self) -> dict:
        return {
            "axis": self.axis,
            "gluing_id": self.gluing_id,
            "reverse_axes": self.reverse_axes,
            "schema": self.SCHEMA_ID,
            "transverse_shifts": self.transverse_shifts,
        }


class _SignedUnionFind:
    def __init__(self, values):
        self.parent = {value: value for value in values}
        self.weight = {value: 1 for value in values}

    def find(self, value):
        parent = self.parent[value]
        if parent == value:
            return value, 1
        root, parent_weight = self.find(parent)
        self.weight[value] *= parent_weight
        self.parent[value] = root
        return root, self.weight[value]

    def union(self, source, target, orientation):
        source_root, source_weight = self.find(source)
        target_root, target_weight = self.find(target)
        relation_weight = orientation * target_weight * source_weight
        if source_root == target_root:
            if source_weight != orientation * target_weight:
                raise ValueError("cell gluing has an orientation-reversing self-cycle")
            return
        if source_root < target_root:
            self.parent[target_root] = source_root
            self.weight[target_root] = relation_weight
        else:
            self.parent[source_root] = target_root
            self.weight[source_root] = relation_weight


def quotient_cell_complex(
    complex_: FiniteCellComplex,
    gluings: Sequence[CellGluing],
) -> FiniteCellComplex:
    gluings = tuple(sorted(set(gluings)))
    by_dimension = [[] for _ in complex_.cell_ids_by_dimension]
    for gluing in gluings:
        if gluing.dimension > complex_.dimension:
            raise ValueError("cell gluing degree exceeds complex dimension")
        cells = set(complex_.cell_ids_by_dimension[gluing.dimension])
        if gluing.source_cell_id not in cells or gluing.target_cell_id not in cells:
            raise ValueError("cell gluing names an unknown cell")
        by_dimension[gluing.dimension].append(gluing)

    orbit_data = []
    quotient_ids = []
    for dimension, cells in enumerate(complex_.cell_ids_by_dimension):
        union = _SignedUnionFind(cells)
        for gluing in by_dimension[dimension]:
            union.union(
                gluing.source_cell_id, gluing.target_cell_id, gluing.orientation
            )
        mapping = {cell: union.find(cell) for cell in cells}
        orbit_data.append(mapping)
        quotient_ids.append(tuple(sorted({root for root, _ in mapping.values()})))

    boundaries = [SparseIntMatrix.zero(0, len(quotient_ids[0]))]
    for dimension in range(1, len(quotient_ids)):
        old_lower = complex_.cell_ids_by_dimension[dimension - 1]
        old_upper = complex_.cell_ids_by_dimension[dimension]
        old_boundary = complex_.boundary_maps[dimension]
        old_rows = old_boundary.to_rows()
        lower_index = {cell: index for index, cell in enumerate(quotient_ids[dimension - 1])}
        upper_index = {cell: index for index, cell in enumerate(quotient_ids[dimension])}
        images_by_upper = {}
        for old_column, upper_cell in enumerate(old_upper):
            upper_root, upper_weight = orbit_data[dimension][upper_cell]
            image = {}
            for old_row, coefficient in enumerate(
                row[old_column] for row in old_rows
            ):
                if not coefficient:
                    continue
                lower_root, lower_weight = orbit_data[dimension - 1][old_lower[old_row]]
                image[lower_root] = image.get(lower_root, 0) + (
                    upper_weight * coefficient * lower_weight
                )
            image = {cell: value for cell, value in image.items() if value}
            previous = images_by_upper.get(upper_root)
            if previous is not None and previous != image:
                raise ValueError("cell gluing is incompatible with cellular boundaries")
            images_by_upper[upper_root] = image
        entries = tuple(
            (lower_index[lower], upper_index[upper], coefficient)
            for upper, image in images_by_upper.items()
            for lower, coefficient in image.items()
        )
        boundaries.append(
            SparseIntMatrix(
                len(quotient_ids[dimension - 1]),
                len(quotient_ids[dimension]),
                entries,
            )
        )
    return FiniteCellComplex(
        tuple(quotient_ids),
        tuple(boundaries),
        complex_.assumptions + ("cellular quotient by explicit oriented gluings",),
    )


def rectangular_glued_cell_complex(
    shape: Sequence[int], gluings: Sequence[BoundaryGluing]
) -> FiniteCellComplex:
    shape = tuple(shape)
    cover = rectangular_cubical_complex(shape)
    dimension = len(shape)
    gluings = tuple(sorted(tuple(gluings), key=lambda item: item.axis))
    glued_axes = {gluing.axis for gluing in gluings}
    if len(glued_axes) != len(gluings):
        raise ValueError("at most one boundary gluing is allowed per axis")
    normalized_gluings = []
    for gluing in gluings:
        if gluing.axis < 0 or gluing.axis >= dimension:
            raise ValueError("boundary gluing axis is out of range")
        if len(gluing.transverse_shifts) not in {0, dimension}:
            raise ValueError("boundary-gluing shifts must be empty or ambient-rank")
        shifts = gluing.transverse_shifts or (0,) * dimension
        if shifts[gluing.axis]:
            raise ValueError("boundary gluing cannot shift along its glued axis")
        if any(axis < 0 or axis >= dimension or axis == gluing.axis for axis in gluing.reverse_axes):
            raise ValueError("invalid reflected transverse axis")
        normalized_gluings.append((gluing, shifts))

    def reduce_cell(cell):
        base = list(cell.base)
        orientation = 1
        for _ in range(1024):
            changed = False
            for gluing, shifts in normalized_gluings:
                axis = gluing.axis
                quotient, remainder = divmod(base[axis], shape[axis])
                if not quotient:
                    continue
                base[axis] = remainder
                direction = 1 if quotient > 0 else -1
                for _step in range(abs(quotient)):
                    for transverse in range(dimension):
                        if transverse == axis:
                            continue
                        if transverse in gluing.reverse_axes:
                            base[transverse] = (
                                shape[transverse]
                                - base[transverse]
                                - (1 if transverse in cell.varying_axes else 0)
                                + shifts[transverse]
                            )
                            if transverse in cell.varying_axes:
                                orientation *= -1
                        else:
                            base[transverse] += direction * shifts[transverse]
                changed = True
            if not changed:
                return CubicalCell(dimension, cell.varying_axes, tuple(base)), orientation
        raise ValueError("boundary gluing reduction did not reach a canonical cell")

    cell_gluings = []
    for gluing, _shifts in normalized_gluings:
        for degree, cells in enumerate(cover.cells_by_dimension):
            lookup = {cell: cell for cell in cells}
            for source in cells:
                if gluing.axis in source.varying_axes:
                    continue
                if source.base[gluing.axis] != shape[gluing.axis]:
                    continue
                target, orientation = reduce_cell(source)
                if target not in lookup:
                    raise ValueError("boundary gluing maps a cell outside the cover")
                cell_gluings.append(
                    CellGluing(degree, source.cell_id, target.cell_id, orientation)
                )
    return quotient_cell_complex(cover.chain_complex, tuple(cell_gluings))


def boundary_chain_subcomplex(complex_: FiniteCellComplex) -> FiniteCellComplex:
    dimension = complex_.dimension
    if dimension == 0:
        raise ValueError("zero-dimensional complex has no codimension-one boundary")
    top_boundary = complex_.boundary_maps[dimension]
    entries_by_row = {}
    for row, column, value in top_boundary.entries:
        entries_by_row.setdefault(row, []).append((column, value))
    selected = [set() for _ in range(dimension)]
    selected[dimension - 1] = {
        row
        for row, entries in entries_by_row.items()
        if len(entries) == 1 and abs(entries[0][1]) == 1
    }
    for degree in range(dimension - 1, 0, -1):
        boundary = complex_.boundary_maps[degree]
        for row, column, value in boundary.entries:
            if value and column in selected[degree]:
                selected[degree - 1].add(row)
    cell_ids = tuple(
        tuple(
            complex_.cell_ids_by_dimension[degree][index]
            for index in sorted(selected[degree])
        )
        for degree in range(dimension)
    )
    boundaries = [SparseIntMatrix.zero(0, len(cell_ids[0]))]
    for degree in range(1, dimension):
        old_boundary = complex_.boundary_maps[degree]
        row_map = {old: new for new, old in enumerate(sorted(selected[degree - 1]))}
        column_map = {old: new for new, old in enumerate(sorted(selected[degree]))}
        boundaries.append(
            SparseIntMatrix(
                len(row_map),
                len(column_map),
                tuple(
                    (row_map[row], column_map[column], value)
                    for row, column, value in old_boundary.entries
                    if row in row_map and column in column_map
                ),
            )
        )
    return FiniteCellComplex(
        cell_ids,
        tuple(boundaries),
        complex_.assumptions + ("cellular codimension-one boundary",),
    )


def _boundary_of_cell(
    cell: CubicalCell,
    periods: Tuple[int, ...],
    periodic_axes: frozenset,
) -> Tuple[Tuple[CubicalCell, int], ...]:
    result = []
    axes = cell.varying_axes
    for position, axis in enumerate(axes):
        remaining = tuple(value for value in axes if value != axis)
        sign = (-1) ** position
        lower = CubicalCell(cell.ambient_dimension, remaining, cell.base)
        upper_base = list(cell.base)
        upper_base[axis] += 1
        if axis in periodic_axes:
            upper_base[axis] %= periods[axis]
        upper = CubicalCell(cell.ambient_dimension, remaining, tuple(upper_base))
        result.append((lower, -sign))
        result.append((upper, sign))
    return tuple(result)


def _assemble_cubical_complex(
    cells_by_dimension: Sequence[Sequence[CubicalCell]],
    periods: Sequence[int],
    periodic_axes: Iterable[int],
    assumptions: Sequence[str] = (),
) -> CubicalComplex:
    levels = tuple(tuple(sorted(set(level))) for level in cells_by_dimension)
    period_tuple = tuple(periods)
    periodic = frozenset(periodic_axes)
    boundaries = [SparseIntMatrix.zero(0, len(levels[0]))]
    for dimension in range(1, len(levels)):
        lower_index = {cell: index for index, cell in enumerate(levels[dimension - 1])}
        entries = []
        for column, cell in enumerate(levels[dimension]):
            for face, coefficient in _boundary_of_cell(cell, period_tuple, periodic):
                if face not in lower_index:
                    raise ArithmeticError("cubical complex is not closed under faces")
                entries.append((lower_index[face], column, coefficient))
        boundaries.append(
            SparseIntMatrix(len(levels[dimension - 1]), len(levels[dimension]), tuple(entries))
        )
    chain = FiniteCellComplex(
        tuple(tuple(cell.cell_id for cell in level) for level in levels),
        tuple(boundaries),
        tuple(assumptions),
    )
    return CubicalComplex(chain, levels, tuple(sorted(periodic)))


def cubical_complex_from_top_cells(
    top_cells: Iterable[Sequence[int]],
) -> CubicalComplex:
    top_cells = tuple(sorted(set(tuple(cell) for cell in top_cells)))
    if not top_cells:
        raise ValueError("cubical mask must contain at least one top cell")
    dimension = len(top_cells[0])
    if dimension < 1 or any(len(cell) != dimension for cell in top_cells):
        raise ValueError("cubical mask top cells must have a common positive dimension")
    levels = [set() for _ in range(dimension + 1)]
    all_axes = tuple(range(dimension))
    for base in top_cells:
        for cell_dimension in range(dimension + 1):
            for varying in itertools.combinations(all_axes, cell_dimension):
                fixed = tuple(axis for axis in all_axes if axis not in varying)
                for upper_choices in itertools.product((0, 1), repeat=len(fixed)):
                    face_base = list(base)
                    for axis, upper in zip(fixed, upper_choices):
                        face_base[axis] += upper
                    levels[cell_dimension].add(
                        CubicalCell(dimension, tuple(varying), tuple(face_base))
                    )
    periods = tuple(max(cell[axis] for cell in top_cells) + 1 for axis in all_axes)
    return _assemble_cubical_complex(
        levels,
        periods,
        (),
        ("open cubical subcomplex generated by the supplied top cells",),
    )


def rectangular_cubical_complex(
    shape: Sequence[int], periodic_axes: Iterable[int] = ()
) -> CubicalComplex:
    shape = tuple(shape)
    if not shape or any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in shape):
        raise ValueError("rectangular shape entries must be positive integers")
    dimension = len(shape)
    periodic = frozenset(periodic_axes)
    if any(axis < 0 or axis >= dimension for axis in periodic):
        raise ValueError("periodic axis is out of range")
    levels = []
    all_axes = tuple(range(dimension))
    for cell_dimension in range(dimension + 1):
        level = []
        for varying in itertools.combinations(all_axes, cell_dimension):
            ranges = []
            for axis, length in enumerate(shape):
                if axis in varying or axis in periodic:
                    ranges.append(range(length))
                else:
                    ranges.append(range(length + 1))
            for base in itertools.product(*ranges):
                level.append(CubicalCell(dimension, tuple(varying), tuple(base)))
        levels.append(level)
    return _assemble_cubical_complex(
        levels,
        shape,
        periodic,
        ("rectangular cubical complex",),
    )


def boundary_subcomplex(complex_: CubicalComplex) -> CubicalComplex:
    dimension = complex_.dimension
    if dimension == 0:
        raise ValueError("zero-dimensional complex has no codimension-one boundary")
    top_boundary = complex_.chain_complex.boundary_maps[dimension]
    entries_by_row = {}
    for row, column, value in top_boundary.entries:
        entries_by_row.setdefault(row, []).append((column, value))
    selected = {
        row
        for row, entries in entries_by_row.items()
        if len(entries) == 1 and abs(entries[0][1]) == 1
    }
    levels = [set() for _ in range(dimension)]
    levels[dimension - 1] = {
        complex_.cells_by_dimension[dimension - 1][row] for row in selected
    }
    for degree in range(dimension - 1, 0, -1):
        for cell in levels[degree]:
            for face, _ in _boundary_of_cell(
                cell,
                tuple(1 for _ in range(dimension)),
                frozenset(),
            ):
                levels[degree - 1].add(face)
    periods = tuple(
        max((cell.base[axis] for level in levels for cell in level), default=0) + 1
        for axis in range(dimension)
    )
    return _assemble_cubical_complex(
        levels,
        periods,
        (),
        ("codimension-one boundary subcomplex",),
    )


def cellular_homology(
    complex_: FiniteCellComplex,
    degree: int,
    coefficient_modulus: int,
    backend: FiniteIntegerBackend,
) -> FiniteQuotient:
    if degree < 0 or degree > complex_.dimension:
        raise ValueError("cellular homology degree is out of range")
    if coefficient_modulus <= 1:
        raise ValueError("cellular coefficient modulus must exceed one")
    chain_group = FiniteAbelianGroup.from_coordinate_orders(
        (coefficient_modulus,) * len(complex_.cell_ids_by_dimension[degree]),
        backend,
        complex_.cell_ids_by_dimension[degree],
    )
    if degree == 0:
        lower_group = FiniteAbelianGroup.from_coordinate_orders((), backend)
    else:
        lower_group = FiniteAbelianGroup.from_coordinate_orders(
            (coefficient_modulus,) * len(complex_.cell_ids_by_dimension[degree - 1]),
            backend,
            complex_.cell_ids_by_dimension[degree - 1],
        )
    boundary = FiniteGroupHomomorphism.create(
        chain_group,
        lower_group,
        complex_.boundary_maps[degree],
        backend,
    )
    cycles = boundary.kernel(backend)
    if degree == complex_.dimension:
        boundaries = chain_group.trivial_subgroup(backend)
    else:
        upper_group = FiniteAbelianGroup.from_coordinate_orders(
            (coefficient_modulus,) * len(complex_.cell_ids_by_dimension[degree + 1]),
            backend,
            complex_.cell_ids_by_dimension[degree + 1],
        )
        upper_boundary = FiniteGroupHomomorphism.create(
            upper_group,
            chain_group,
            complex_.boundary_maps[degree + 1],
            backend,
        )
        boundaries = upper_boundary.image(backend)
    if not cycles.contains_subgroup(boundaries, backend):
        raise ArithmeticError("cellular boundaries are not contained in cycles")
    return cycles.quotient_by(boundaries, backend)


@dataclass(frozen=True)
class CellularCode:
    chain_complex: FiniteCellComplex
    qudit_degree: int
    coefficient_modulus: int
    code: StabilizerCodeSpec
    convention: "CellularPauliConvention"
    check_records: Tuple["CellularCheck", ...]
    x_check_cell_ids: Tuple[str, ...]
    z_check_cell_ids: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.cellular_code.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "chain_complex": self.chain_complex,
            "code": self.code,
            "coefficient_modulus": self.coefficient_modulus,
            "convention": self.convention,
            "check_records": self.check_records,
            "qudit_degree": self.qudit_degree,
            "schema": self.SCHEMA_ID,
            "x_check_cell_ids": self.x_check_cell_ids,
            "z_check_cell_ids": self.z_check_cell_ids,
        }


class CellularPauliConvention(str, Enum):
    PRIMAL = "primal_x_lower_z_upper"
    FOURIER_DUAL = "fourier_dual_z_lower_x_upper"


@dataclass(frozen=True)
class CellularCheck:
    cell_id: str
    pauli_kind: str
    operator: PauliOperator

    SCHEMA_ID = "mobility_toolkit.cellular_check.v1"

    def __post_init__(self) -> None:
        if self.pauli_kind not in {"x", "z"}:
            raise ValueError("cellular check kind must be x or z")

    def to_canonical_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "operator": self.operator,
            "pauli_kind": self.pauli_kind,
            "schema": self.SCHEMA_ID,
        }


def cellular_stabilizer_code(
    complex_: FiniteCellComplex,
    qudit_degree: int,
    coefficient_modulus: int,
    convention: CellularPauliConvention = CellularPauliConvention.PRIMAL,
) -> CellularCode:
    if qudit_degree < 1 or qudit_degree > complex_.dimension:
        raise ValueError("cellular code qudits require degree 1 through top dimension")
    site_ids = complex_.cell_ids_by_dimension[qudit_degree]
    module = PauliModule(
        tuple(LocalSystem.cyclic(site_id, coefficient_modulus) for site_id in site_ids)
    )
    if not isinstance(convention, CellularPauliConvention):
        raise TypeError("cellular Pauli convention must be explicit enum value")
    records = []
    lower_ids = complex_.cell_ids_by_dimension[qudit_degree - 1]
    lower_rows = complex_.boundary_maps[qudit_degree].to_rows()
    lower_kind = "x" if convention == CellularPauliConvention.PRIMAL else "z"
    for check_id, row in zip(lower_ids, lower_rows):
        terms = tuple(
            LocalPauliTerm.cyclic(
                site_id,
                x=coefficient if lower_kind == "x" else 0,
                z=coefficient if lower_kind == "z" else 0,
            )
            for site_id, coefficient in zip(site_ids, row)
            if coefficient
        )
        records.append(CellularCheck(check_id, lower_kind, module.operator(terms)))
    if qudit_degree < complex_.dimension:
        upper_ids = complex_.cell_ids_by_dimension[qudit_degree + 1]
        upper_rows = complex_.boundary_maps[qudit_degree + 1].to_rows()
        upper_kind = "z" if convention == CellularPauliConvention.PRIMAL else "x"
        for column, check_id in enumerate(upper_ids):
            terms = tuple(
                LocalPauliTerm.cyclic(
                    site_id,
                    x=upper_rows[row][column] if upper_kind == "x" else 0,
                    z=upper_rows[row][column] if upper_kind == "z" else 0,
                )
                for row, site_id in enumerate(site_ids)
                if upper_rows[row][column]
            )
            records.append(CellularCheck(check_id, upper_kind, module.operator(terms)))
    else:
        upper_ids = ()
        upper_kind = "z" if convention == CellularPauliConvention.PRIMAL else "x"
    generators = tuple(record.operator for record in records)
    code = StabilizerCodeSpec(
        module,
        generators,
        (
            "cellular generalized Pauli code from signed integer incidence maps",
        ),
    )
    return CellularCode(
        complex_,
        qudit_degree,
        coefficient_modulus,
        code,
        convention,
        tuple(records),
        tuple(record.cell_id for record in records if record.pauli_kind == "x"),
        tuple(record.cell_id for record in records if record.pauli_kind == "z"),
    )


__all__ = [
    "BoundaryGluing",
    "CellGluing",
    "CellularCode",
    "CellularCheck",
    "CellularPauliConvention",
    "CubicalCell",
    "CubicalComplex",
    "FiniteCellComplex",
    "MaskTopologyDiagnostics",
    "boundary_subcomplex",
    "boundary_chain_subcomplex",
    "cellular_homology",
    "cellular_stabilizer_code",
    "cubical_complex_from_top_cells",
    "diagnose_cubical_mask",
    "rectangular_cubical_complex",
    "rectangular_glued_cell_complex",
    "quotient_cell_complex",
]
