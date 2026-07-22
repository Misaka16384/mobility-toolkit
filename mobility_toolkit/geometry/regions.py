"""Convenience constructors over the generic finite-region contract."""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Iterable, Mapping, Optional, Sequence, Tuple

from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.core.laurent import TranslationGroup
from mobility_toolkit.core.pauli import LocalSystem
from mobility_toolkit.geometry.frame import LocalPauliAutomorphism
from mobility_toolkit.geometry.model import (
    AxisIdentification,
    FiniteRegion,
    LatticeCoordinate,
    SiteAddress,
    SiteEmbedding,
    SpeciesFrame,
    Stratification,
    Stratum,
)


def canonical_physical_site_id(address: SiteAddress) -> str:
    return "site:" + canonical_hash("finite-region-site", address)


def _all_torsion_coordinates(group: TranslationGroup):
    return itertools.product(*(range(order) for order in group.torsion_invariants))


def explicit_coordinate_region(
    translation_group: TranslationGroup,
    free_coordinates: Iterable[Sequence[int]],
    species: Sequence[LocalSystem],
    *,
    axis_identifications: Sequence[AxisIdentification] = (),
    stratification: Optional[Stratification] = None,
    assumptions: Sequence[str] = (),
) -> FiniteRegion:
    species = tuple(species)
    free_coordinates = tuple(sorted(set(tuple(cell) for cell in free_coordinates)))
    if not free_coordinates:
        raise ValueError("finite region needs at least one free coordinate")
    if any(len(cell) != translation_group.free_rank for cell in free_coordinates):
        raise ValueError("finite-region free coordinate rank mismatch")
    coordinates = tuple(
        LatticeCoordinate(free, tuple(torsion))
        for free in free_coordinates
        for torsion in _all_torsion_coordinates(translation_group)
    )
    physical_systems = []
    embeddings = []
    for coordinate in coordinates:
        for local in species:
            address = SiteAddress(coordinate, local.site_id)
            site_id = canonical_physical_site_id(address)
            physical_systems.append(LocalSystem(site_id, local.invariant_factors))
            embeddings.append(
                SiteEmbedding(
                    address,
                    site_id,
                    LocalPauliAutomorphism.identity(local.invariant_factors),
                )
            )
    return FiniteRegion(
        translation_group,
        species,
        coordinates,
        tuple(physical_systems),
        tuple(embeddings),
        tuple(axis_identifications),
        (),
        stratification,
        tuple(assumptions),
    )


def box_stratification(
    shape: Sequence[int],
    species: Sequence[LocalSystem],
    *,
    periodic_axes: Iterable[int] = (),
) -> Stratification:
    shape = tuple(shape)
    dimension = len(shape)
    periodic = frozenset(periodic_axes)
    cells_by_signature = defaultdict(list)
    for cell in itertools.product(*(range(length) for length in shape)):
        signature = []
        for axis, length in enumerate(shape):
            if axis in periodic:
                continue
            if cell[axis] == 0:
                signature.append((axis, "lower"))
            if cell[axis] == length - 1:
                signature.append((axis, "upper"))
        cells_by_signature[tuple(signature)].append(cell)

    def stratum_id(signature):
        if not signature:
            return "bulk"
        return "/".join(f"a{axis}:{side}" for axis, side in signature)

    strata = []
    signatures = set(cells_by_signature)
    for signature, cells in cells_by_signature.items():
        constrained_axes = len({axis for axis, _ in signature})
        intrinsic_dimension = dimension - constrained_axes
        if constrained_axes == 0:
            role = "bulk"
        elif constrained_axes == 1:
            role = "surface"
        elif intrinsic_dimension == 0:
            role = "corner"
        else:
            role = "hinge"
        coordinates = tuple(LatticeCoordinate(tuple(cell)) for cell in cells)
        addresses = tuple(
            SiteAddress(coordinate, local.site_id)
            for coordinate in coordinates
            for local in species
        )
        parents = []
        if signature:
            for removed in range(len(signature)):
                parent_signature = signature[:removed] + signature[removed + 1 :]
                if parent_signature in signatures:
                    parents.append(stratum_id(parent_signature))
        normal = ()
        if constrained_axes == 1:
            axis, side = signature[0]
            values = [0] * dimension
            values[axis] = -1 if side == "lower" else 1
            normal = tuple(values)
        strata.append(
            Stratum(
                stratum_id(signature),
                intrinsic_dimension,
                stratum_id(signature),
                role,
                addresses,
                coordinates,
                (),
                normal,
                tuple(parents),
            )
        )
    return Stratification(dimension, tuple(strata))


def rectangular_region(
    shape: Sequence[int],
    species: Sequence[LocalSystem],
    *,
    periodic_axes: Iterable[int] = (),
    twists: Mapping[Tuple[int, str], LocalPauliAutomorphism] | None = None,
) -> FiniteRegion:
    shape = tuple(shape)
    if not shape or any(value < 1 for value in shape):
        raise ValueError("rectangular region shape entries must be positive")
    periodic = tuple(sorted(set(periodic_axes)))
    if any(axis < 0 or axis >= len(shape) for axis in periodic):
        raise ValueError("periodic region axis is out of range")
    twists = {} if twists is None else dict(twists)
    axis_identifications = []
    for axis in periodic:
        frames = tuple(
            SpeciesFrame(species_id, automorphism)
            for (twist_axis, species_id), automorphism in twists.items()
            if twist_axis == axis
        )
        axis_identifications.append(
            AxisIdentification("free", axis, 0, shape[axis], frames)
        )
    unknown_axes = {axis for axis, _ in twists} - set(periodic)
    if unknown_axes:
        raise ValueError("frame twist is declared on a nonperiodic axis")
    group = TranslationGroup(len(shape))
    stratification = box_stratification(shape, species, periodic_axes=periodic)
    return explicit_coordinate_region(
        group,
        itertools.product(*(range(length) for length in shape)),
        species,
        axis_identifications=axis_identifications,
        stratification=stratification,
        assumptions=("rectangular fundamental region",),
    )


def masked_region(
    top_cells: Iterable[Sequence[int]], species: Sequence[LocalSystem]
) -> FiniteRegion:
    cells = tuple(sorted(set(tuple(cell) for cell in top_cells)))
    if not cells:
        raise ValueError("masked region needs at least one cell")
    return explicit_coordinate_region(
        TranslationGroup(len(cells[0])),
        cells,
        species,
        assumptions=("explicit irregular cell mask",),
    )


def region_with_rectangular_holes(
    outer_shape: Sequence[int],
    holes: Iterable[Tuple[Sequence[int], Sequence[int]]],
    species: Sequence[LocalSystem],
) -> FiniteRegion:
    outer_shape = tuple(outer_shape)
    removed = set()
    for lower, shape in holes:
        lower = tuple(lower)
        shape = tuple(shape)
        if len(lower) != len(outer_shape) or len(shape) != len(outer_shape):
            raise ValueError("hole rank must match the outer region")
        for offset in itertools.product(*(range(length) for length in shape)):
            cell = tuple(left + right for left, right in zip(lower, offset))
            if any(value < 0 or value >= outer_shape[axis] for axis, value in enumerate(cell)):
                raise ValueError("hole extends outside the outer region")
            removed.add(cell)
    cells = {
        cell
        for cell in itertools.product(*(range(length) for length in outer_shape))
        if cell not in removed
    }
    return masked_region(cells, species)


__all__ = [
    "box_stratification",
    "canonical_physical_site_id",
    "explicit_coordinate_region",
    "masked_region",
    "rectangular_region",
    "region_with_rectangular_holes",
]
