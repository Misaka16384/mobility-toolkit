"""Canonical finite-region, identification, and stratification contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from mobility_toolkit.core.laurent import TranslationGroup
from mobility_toolkit.core.pauli import LocalSystem
from mobility_toolkit.geometry.frame import LocalPauliAutomorphism, LocalPauliMap


def _coordinate(values: Sequence[int], rank: int, name: str) -> Tuple[int, ...]:
    values = tuple(values)
    if len(values) != rank:
        raise ValueError(f"{name} must have rank {rank}")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise TypeError(f"{name} entries must be integers")
    return values


@dataclass(frozen=True, order=True)
class LatticeCoordinate:
    free: Tuple[int, ...]
    torsion: Tuple[int, ...] = ()

    SCHEMA_ID = "mobility_toolkit.lattice_coordinate.v1"

    def translated(
        self, free_offset: Sequence[int], torsion_offset: Sequence[int] = ()
    ) -> "LatticeCoordinate":
        if len(free_offset) != len(self.free) or len(torsion_offset) != len(self.torsion):
            raise ValueError("translation offset rank mismatch")
        return LatticeCoordinate(
            tuple(left + right for left, right in zip(self.free, free_offset)),
            tuple(left + right for left, right in zip(self.torsion, torsion_offset)),
        )

    def to_canonical_dict(self) -> dict:
        return {"free": self.free, "schema": self.SCHEMA_ID, "torsion": self.torsion}


@dataclass(frozen=True, order=True)
class SiteAddress:
    coordinate: LatticeCoordinate
    species_id: str

    SCHEMA_ID = "mobility_toolkit.site_address.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.species_id, str) or not self.species_id:
            raise ValueError("site-address species_id must be a nonempty string")

    def to_canonical_dict(self) -> dict:
        return {
            "coordinate": self.coordinate,
            "schema": self.SCHEMA_ID,
            "species_id": self.species_id,
        }


@dataclass(frozen=True)
class SpeciesFrame:
    species_id: str
    automorphism: LocalPauliAutomorphism

    def to_canonical_dict(self) -> dict:
        return {"automorphism": self.automorphism, "species_id": self.species_id}


@dataclass(frozen=True)
class AxisIdentification:
    axis_kind: str
    axis: int
    lower: int
    period: int
    twists: Tuple[SpeciesFrame, ...] = ()

    SCHEMA_ID = "mobility_toolkit.axis_identification.v1"

    def __post_init__(self) -> None:
        if self.axis_kind not in {"free", "torsion"}:
            raise ValueError("axis_kind must be 'free' or 'torsion'")
        if self.axis < 0 or self.period <= 0:
            raise ValueError("axis and period must be nonnegative/positive")
        twists = tuple(sorted(self.twists, key=lambda item: item.species_id))
        if len({item.species_id for item in twists}) != len(twists):
            raise ValueError("axis twists must have unique species IDs")
        object.__setattr__(self, "twists", twists)

    def twist_for(self, species_id: str, factors: Tuple[int, ...]) -> LocalPauliAutomorphism:
        for frame in self.twists:
            if frame.species_id == species_id:
                return frame.automorphism
        return LocalPauliAutomorphism.identity(factors)

    def to_canonical_dict(self) -> dict:
        return {
            "axis": self.axis,
            "axis_kind": self.axis_kind,
            "lower": self.lower,
            "period": self.period,
            "schema": self.SCHEMA_ID,
            "twists": self.twists,
        }


@dataclass(frozen=True)
class SiteEmbedding:
    address: SiteAddress
    physical_site_id: str
    frame: LocalPauliAutomorphism

    SCHEMA_ID = "mobility_toolkit.site_embedding.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.physical_site_id, str) or not self.physical_site_id:
            raise ValueError("physical_site_id must be a nonempty string")

    def to_canonical_dict(self) -> dict:
        return {
            "address": self.address,
            "frame": self.frame,
            "physical_site_id": self.physical_site_id,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class SiteAlias:
    source: SiteAddress
    target: SiteAddress
    frame: LocalPauliAutomorphism
    seam_id: str = ""

    SCHEMA_ID = "mobility_toolkit.site_alias.v1"

    def __post_init__(self) -> None:
        if self.source == self.target:
            raise ValueError("site alias source and target must differ")

    def to_canonical_dict(self) -> dict:
        return {
            "frame": self.frame,
            "schema": self.SCHEMA_ID,
            "seam_id": self.seam_id,
            "source": self.source,
            "target": self.target,
        }


@dataclass(frozen=True)
class ResolvedSite:
    raw_address: SiteAddress
    canonical_address: SiteAddress
    physical_site_id: str
    frame: LocalPauliMap
    winding: Tuple[Tuple[str, int, int], ...]
    seams: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.resolved_site.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "canonical_address": self.canonical_address,
            "frame": self.frame,
            "physical_site_id": self.physical_site_id,
            "raw_address": self.raw_address,
            "schema": self.SCHEMA_ID,
            "seams": self.seams,
            "winding": self.winding,
        }


@dataclass(frozen=True, order=True)
class BoundaryFacet:
    cell: LatticeCoordinate
    normal: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.boundary_facet.v1"

    def to_canonical_dict(self) -> dict:
        return {"cell": self.cell, "normal": self.normal, "schema": self.SCHEMA_ID}


@dataclass(frozen=True)
class Stratum:
    stratum_id: str
    intrinsic_dimension: int
    component_id: str
    role: str = "generic"
    site_addresses: Tuple[SiteAddress, ...] = ()
    anchor_coordinates: Tuple[LatticeCoordinate, ...] = ()
    facets: Tuple[BoundaryFacet, ...] = ()
    primitive_normal: Tuple[int, ...] = ()
    parent_ids: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.stratum.v1"

    def __post_init__(self) -> None:
        if not self.stratum_id or not self.component_id:
            raise ValueError("stratum and component IDs must be nonempty")
        if self.intrinsic_dimension < 0:
            raise ValueError("stratum intrinsic dimension must be nonnegative")
        normal = tuple(self.primitive_normal)
        if normal:
            if not any(normal) or math.gcd(*(abs(value) for value in normal)) != 1:
                raise ValueError("stratum normal must be primitive")
        object.__setattr__(self, "site_addresses", tuple(sorted(set(self.site_addresses))))
        object.__setattr__(
            self, "anchor_coordinates", tuple(sorted(set(self.anchor_coordinates)))
        )
        object.__setattr__(self, "facets", tuple(sorted(set(self.facets))))
        object.__setattr__(self, "primitive_normal", normal)
        object.__setattr__(self, "parent_ids", tuple(sorted(set(self.parent_ids))))

    def to_canonical_dict(self) -> dict:
        return {
            "anchor_coordinates": self.anchor_coordinates,
            "component_id": self.component_id,
            "facets": self.facets,
            "intrinsic_dimension": self.intrinsic_dimension,
            "parent_ids": self.parent_ids,
            "primitive_normal": self.primitive_normal,
            "role": self.role,
            "schema": self.SCHEMA_ID,
            "site_addresses": self.site_addresses,
            "stratum_id": self.stratum_id,
        }


@dataclass(frozen=True)
class Stratification:
    ambient_dimension: int
    strata: Tuple[Stratum, ...]

    SCHEMA_ID = "mobility_toolkit.stratification.v1"

    def __post_init__(self) -> None:
        strata = tuple(sorted(self.strata, key=lambda item: item.stratum_id))
        by_id = {item.stratum_id: item for item in strata}
        if len(by_id) != len(strata):
            raise ValueError("stratum IDs must be unique")
        if any(item.intrinsic_dimension > self.ambient_dimension for item in strata):
            raise ValueError("stratum dimension exceeds ambient dimension")
        for item in strata:
            for parent_id in item.parent_ids:
                if parent_id not in by_id:
                    raise ValueError("stratum names an unknown parent")
                if by_id[parent_id].intrinsic_dimension <= item.intrinsic_dimension:
                    raise ValueError("stratum parent must have greater intrinsic dimension")
        visiting = set()
        visited = set()

        def visit(stratum_id):
            if stratum_id in visiting:
                raise ValueError("stratum incidence contains a cycle")
            if stratum_id in visited:
                return
            visiting.add(stratum_id)
            for parent_id in by_id[stratum_id].parent_ids:
                visit(parent_id)
            visiting.remove(stratum_id)
            visited.add(stratum_id)

        for stratum_id in by_id:
            visit(stratum_id)
        object.__setattr__(self, "strata", strata)

    def get(self, stratum_id: str) -> Stratum:
        for stratum in self.strata:
            if stratum.stratum_id == stratum_id:
                return stratum
        raise KeyError(stratum_id)

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_dimension": self.ambient_dimension,
            "schema": self.SCHEMA_ID,
            "strata": self.strata,
        }


@dataclass(frozen=True)
class FiniteRegion:
    translation_group: TranslationGroup
    source_species: Tuple[LocalSystem, ...]
    anchor_coordinates: Tuple[LatticeCoordinate, ...]
    physical_systems: Tuple[LocalSystem, ...]
    embeddings: Tuple[SiteEmbedding, ...]
    axis_identifications: Tuple[AxisIdentification, ...] = ()
    aliases: Tuple[SiteAlias, ...] = ()
    stratification: Optional[Stratification] = None
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.finite_region.v1"

    def __post_init__(self) -> None:
        group = self.translation_group
        species = tuple(sorted(self.source_species, key=lambda item: item.site_id))
        physical = tuple(sorted(self.physical_systems, key=lambda item: item.site_id))
        embeddings = tuple(sorted(self.embeddings, key=lambda item: item.address))
        axes = tuple(
            sorted(self.axis_identifications, key=lambda item: (item.axis_kind, item.axis))
        )
        aliases = tuple(sorted(self.aliases, key=lambda item: item.source))
        if len({item.site_id for item in species}) != len(species):
            raise ValueError("region source species IDs must be unique")
        if len({item.site_id for item in physical}) != len(physical):
            raise ValueError("region physical site IDs must be unique")
        if len({item.address for item in embeddings}) != len(embeddings):
            raise ValueError("region embedding addresses must be unique")
        if len({item.source for item in aliases}) != len(aliases):
            raise ValueError("region alias sources must be unique")
        if set(item.source for item in aliases) & set(item.address for item in embeddings):
            raise ValueError("an address cannot be both a physical embedding and an alias")
        species_map = {item.site_id: item for item in species}
        physical_map = {item.site_id: item for item in physical}
        for coordinate in self.anchor_coordinates:
            self._validate_coordinate(coordinate)
        for embedding in embeddings:
            self._validate_address(embedding.address, species_map)
            if embedding.physical_site_id not in physical_map:
                raise ValueError("embedding names an unknown physical site")
            factors = species_map[embedding.address.species_id].invariant_factors
            if physical_map[embedding.physical_site_id].invariant_factors != factors:
                raise ValueError("embedding changes local invariant factors")
            if embedding.frame.invariant_factors != factors:
                raise ValueError("embedding frame has incompatible invariant factors")
        for alias in aliases:
            self._validate_address(alias.source, species_map)
            self._validate_address(alias.target, species_map)
            source_factors = species_map[alias.source.species_id].invariant_factors
            target_factors = species_map[alias.target.species_id].invariant_factors
            if source_factors != target_factors or alias.frame.invariant_factors != source_factors:
                raise ValueError("site alias changes local invariant factors")
        seen_axes = set()
        for axis in axes:
            key = (axis.axis_kind, axis.axis)
            if key in seen_axes:
                raise ValueError("region has duplicate axis identifications")
            seen_axes.add(key)
            rank = group.free_rank if axis.axis_kind == "free" else len(group.torsion_invariants)
            if axis.axis >= rank:
                raise ValueError("axis identification index is out of range")
            if axis.axis_kind == "torsion":
                expected = group.torsion_invariants[axis.axis]
                if axis.lower != 0 or axis.period != expected:
                    raise ValueError("torsion identification must match its group invariant")
            for twist in axis.twists:
                if twist.species_id not in species_map:
                    raise ValueError("axis twist names unknown species")
                if twist.automorphism.invariant_factors != species_map[
                    twist.species_id
                ].invariant_factors:
                    raise ValueError("axis twist has incompatible invariant factors")
        for species_id, local in species_map.items():
            relevant = [
                axis.twist_for(species_id, local.invariant_factors).forward
                for axis in axes
            ]
            for index, left in enumerate(relevant):
                for right in relevant[index + 1 :]:
                    if left.then(right) != right.then(left):
                        raise ValueError("axis frame holonomies are path dependent")
        if self.stratification is not None and (
            self.stratification.ambient_dimension != group.free_rank
        ):
            raise ValueError("stratification ambient dimension mismatch")
        object.__setattr__(self, "source_species", species)
        object.__setattr__(self, "anchor_coordinates", tuple(sorted(set(self.anchor_coordinates))))
        object.__setattr__(self, "physical_systems", physical)
        object.__setattr__(self, "embeddings", embeddings)
        object.__setattr__(self, "axis_identifications", axes)
        object.__setattr__(self, "aliases", aliases)
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))
        for alias in aliases:
            self.resolve(alias.source)

    def _validate_coordinate(self, coordinate: LatticeCoordinate) -> None:
        _coordinate(coordinate.free, self.translation_group.free_rank, "free coordinate")
        _coordinate(
            coordinate.torsion,
            len(self.translation_group.torsion_invariants),
            "torsion coordinate",
        )

    def _validate_address(
        self, address: SiteAddress, species_map: Dict[str, LocalSystem]
    ) -> None:
        self._validate_coordinate(address.coordinate)
        if address.species_id not in species_map:
            raise ValueError("site address names unknown source species")

    def resolve(self, raw_address: SiteAddress) -> Optional[ResolvedSite]:
        species_map = {item.site_id: item for item in self.source_species}
        self._validate_address(raw_address, species_map)
        factors = species_map[raw_address.species_id].invariant_factors
        current = raw_address
        frame = LocalPauliMap.identity(factors)
        winding = []
        seams = []
        alias_map = {item.source: item for item in self.aliases}
        embedding_map = {item.address: item for item in self.embeddings}
        visited = set()
        while True:
            free = list(current.coordinate.free)
            torsion = list(current.coordinate.torsion)
            for axis in self.axis_identifications:
                values = free if axis.axis_kind == "free" else torsion
                quotient, remainder = divmod(values[axis.axis] - axis.lower, axis.period)
                values[axis.axis] = axis.lower + remainder
                if quotient:
                    twist = axis.twist_for(current.species_id, factors)
                    frame = frame.then(twist.power(quotient))
                    winding.append((axis.axis_kind, axis.axis, quotient))
            for index, order in enumerate(self.translation_group.torsion_invariants):
                if ("torsion", index) not in {
                    (item.axis_kind, item.axis) for item in self.axis_identifications
                }:
                    quotient, remainder = divmod(torsion[index], order)
                    torsion[index] = remainder
                    if quotient:
                        winding.append(("torsion", index, quotient))
            current = SiteAddress(
                LatticeCoordinate(tuple(free), tuple(torsion)), current.species_id
            )
            if current in visited:
                raise ValueError("site aliases contain a resolution cycle")
            visited.add(current)
            alias = alias_map.get(current)
            if alias is not None:
                frame = frame.then(alias.frame.forward)
                if alias.seam_id:
                    seams.append(alias.seam_id)
                current = alias.target
                factors = species_map[current.species_id].invariant_factors
                continue
            embedding = embedding_map.get(current)
            if embedding is None:
                return None
            frame = frame.then(embedding.frame.forward)
            return ResolvedSite(
                raw_address,
                current,
                embedding.physical_site_id,
                frame,
                tuple(winding),
                tuple(seams),
            )

    def to_canonical_dict(self) -> dict:
        return {
            "aliases": self.aliases,
            "anchor_coordinates": self.anchor_coordinates,
            "assumptions": self.assumptions,
            "axis_identifications": self.axis_identifications,
            "embeddings": self.embeddings,
            "physical_systems": self.physical_systems,
            "schema": self.SCHEMA_ID,
            "source_species": self.source_species,
            "stratification": self.stratification,
            "translation_group": self.translation_group,
        }


@dataclass(frozen=True)
class GeometryDisplayMetadata:
    """Visualization-only data deliberately kept outside ``FiniteRegion``."""

    positions: Tuple[Tuple[str, Tuple[float, ...]], ...] = ()
    labels: Tuple[Tuple[str, str], ...] = ()


__all__ = [
    "AxisIdentification",
    "BoundaryFacet",
    "FiniteRegion",
    "GeometryDisplayMetadata",
    "LatticeCoordinate",
    "ResolvedSite",
    "SiteAddress",
    "SiteAlias",
    "SiteEmbedding",
    "SpeciesFrame",
    "Stratification",
    "Stratum",
]
