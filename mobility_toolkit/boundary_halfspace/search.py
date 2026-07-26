"""Canonical E2 bounded-periodic search domains and certificates.

These schemas specify a finite enumeration problem.  A result is
``bounded_exact`` only when its certificate says that this exact domain was
exhausted.  Nothing here implements the thermodynamic symbolic half-space
modules planned for the full Phase 6 engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from mobility_toolkit.boundary_halfspace.geometry import OrientedHalfSpace
from mobility_toolkit.core.results import Exactness


def _nonnegative_tuple(values, name: str) -> Tuple[int, ...]:
    result = tuple(values)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in result):
        raise TypeError(f"{name} entries must be integers")
    if any(value < 0 for value in result):
        raise ValueError(f"{name} entries must be nonnegative")
    return result


def _positive_optional(value: Optional[int], name: str) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
    ):
        raise ValueError(f"{name} must be a positive integer or None")


@dataclass(frozen=True)
class GeneratorSupportBound:
    tangent_radii: Tuple[int, ...]
    max_inward_depth: int
    max_sites_per_term: int

    SCHEMA_ID = "mobility_toolkit.generator_support_bound.v1"

    def __post_init__(self) -> None:
        radii = _nonnegative_tuple(self.tangent_radii, "tangent radii")
        for value, name in (
            (self.max_inward_depth, "max inward depth"),
            (self.max_sites_per_term, "max sites per term"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.max_sites_per_term == 0:
            raise ValueError("max sites per term must be positive")
        object.__setattr__(self, "tangent_radii", radii)

    def to_canonical_dict(self) -> dict:
        return {
            "max_inward_depth": self.max_inward_depth,
            "max_sites_per_term": self.max_sites_per_term,
            "schema": self.SCHEMA_ID,
            "tangent_radii": self.tangent_radii,
        }


@dataclass(frozen=True)
class AncillaBound:
    max_sites_per_unit_cell: int
    allowed_local_orders: Tuple[int, ...] = ()
    max_cyclic_factors_per_site: int = 1

    SCHEMA_ID = "mobility_toolkit.ancilla_bound.v1"

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_sites_per_unit_cell, bool)
            or not isinstance(self.max_sites_per_unit_cell, int)
            or self.max_sites_per_unit_cell < 0
        ):
            raise ValueError("ancilla site bound must be a nonnegative integer")
        if (
            isinstance(self.max_cyclic_factors_per_site, bool)
            or not isinstance(self.max_cyclic_factors_per_site, int)
            or self.max_cyclic_factors_per_site <= 0
        ):
            raise ValueError("ancilla cyclic-factor bound must be positive")
        orders = tuple(sorted(set(self.allowed_local_orders)))
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 1 for value in orders):
            raise ValueError("allowed ancilla orders must be integers greater than one")
        if self.max_sites_per_unit_cell and not orders:
            raise ValueError("positive ancilla count requires at least one allowed local order")
        object.__setattr__(self, "allowed_local_orders", orders)

    def to_canonical_dict(self) -> dict:
        return {
            "allowed_local_orders": self.allowed_local_orders,
            "max_cyclic_factors_per_site": self.max_cyclic_factors_per_site,
            "max_sites_per_unit_cell": self.max_sites_per_unit_cell,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class ResourceBound:
    max_candidates: Optional[int] = None
    max_completions: Optional[int] = None
    max_wall_time_ms: Optional[int] = None
    max_memory_bytes: Optional[int] = None

    SCHEMA_ID = "mobility_toolkit.resource_bound.v1"

    def __post_init__(self) -> None:
        for name in (
            "max_candidates",
            "max_completions",
            "max_wall_time_ms",
            "max_memory_bytes",
        ):
            _positive_optional(getattr(self, name), name)

    def to_canonical_dict(self) -> dict:
        return {
            "max_candidates": self.max_candidates,
            "max_completions": self.max_completions,
            "max_memory_bytes": self.max_memory_bytes,
            "max_wall_time_ms": self.max_wall_time_ms,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class BoundedPeriodicSearchDomain:
    """The complete input contract for an E2 finite search space."""

    half_space: OrientedHalfSpace
    unit_cell_period: Tuple[int, ...]
    support_bound: GeneratorSupportBound
    completion_depth: int
    ancilla_bound: AncillaBound
    coefficient_domain: str
    candidate_families: Tuple[str, ...] = (
        "translation_compatible_submodules",
        "local_hamiltonian_completions",
    )

    SCHEMA_ID = "mobility_toolkit.e2_bounded_periodic_search_domain.v1"

    def __post_init__(self) -> None:
        period = tuple(self.unit_cell_period)
        tangent_rank = self.half_space.normal.dimension - 1
        if len(period) != tangent_rank:
            raise ValueError("unit-cell period rank must equal tangent-lattice rank")
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in period):
            raise ValueError("unit-cell periods must be positive integers")
        if len(self.support_bound.tangent_radii) != tangent_rank:
            raise ValueError("support tangent-radius rank mismatch")
        if (
            isinstance(self.completion_depth, bool)
            or not isinstance(self.completion_depth, int)
            or self.completion_depth < 0
        ):
            raise ValueError("completion depth must be a nonnegative integer")
        if not isinstance(self.coefficient_domain, str) or not self.coefficient_domain:
            raise ValueError("coefficient domain must be a nonempty capability key")
        families = tuple(sorted(set(self.candidate_families)))
        if not families or any(not isinstance(value, str) or not value for value in families):
            raise ValueError("candidate families must be nonempty strings")
        object.__setattr__(self, "unit_cell_period", period)
        object.__setattr__(self, "candidate_families", families)

    @property
    def enumerated_scope(self) -> Tuple[str, ...]:
        return (
            "all encoded candidates in candidate_families",
            "translation-compatible candidates representable in unit_cell_period (including smaller fundamental periods)",
            "generator support within tangent_radii and max_inward_depth",
            "completion terms within completion_depth",
            "ancillas within ancilla_bound",
            "coefficients restricted to coefficient_domain",
        )

    @property
    def excluded_scope(self) -> Tuple[str, ...]:
        return (
            "larger or different tangent unit-cell periods",
            "support or completion depth outside the declared bounds",
            "ancillas outside the declared count, order, or factor bounds",
            "coefficient domains other than the declared capability key",
            "symbolic thermodynamic completeness (E3)",
            "L_H, P_boundary, relative Ext, and quasi-symplectic boundary modules",
        )

    def to_canonical_dict(self) -> dict:
        return {
            "ancilla_bound": self.ancilla_bound,
            "candidate_families": self.candidate_families,
            "coefficient_domain": self.coefficient_domain,
            "completion_depth": self.completion_depth,
            "excluded_scope": self.excluded_scope,
            "half_space": self.half_space,
            "schema": self.SCHEMA_ID,
            "support_bound": self.support_bound,
            "unit_cell_period": self.unit_cell_period,
        }


class SearchTermination(str, Enum):
    EXHAUSTED = "exhausted"
    RESOURCE_LIMIT = "resource_limit"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class SearchSpaceCertificate:
    domain: BoundedPeriodicSearchDomain
    enumerator: str
    enumerator_version: str
    candidate_encoding: str
    enumeration_order: str
    resource_bound: ResourceBound
    termination: SearchTermination
    visited_candidates: int
    accepted_candidates: int
    total_candidates: Optional[int] = None
    completed_shards: Tuple[str, ...] = ()
    pending_shards: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.e2_search_space_certificate.v1"

    def __post_init__(self) -> None:
        for value, name in (
            (self.visited_candidates, "visited candidate count"),
            (self.accepted_candidates, "accepted candidate count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.accepted_candidates > self.visited_candidates:
            raise ValueError("accepted candidates cannot exceed visited candidates")
        if self.total_candidates is not None and (
            isinstance(self.total_candidates, bool)
            or not isinstance(self.total_candidates, int)
            or self.total_candidates < self.visited_candidates
        ):
            raise ValueError("total candidates must be an integer at least as large as visited")
        for value, name in (
            (self.enumerator, "enumerator"),
            (self.enumerator_version, "enumerator version"),
            (self.candidate_encoding, "candidate encoding"),
            (self.enumeration_order, "enumeration order"),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be nonempty")
        completed = tuple(sorted(set(self.completed_shards)))
        pending = tuple(sorted(set(self.pending_shards)))
        if set(completed) & set(pending):
            raise ValueError("a shard cannot be both completed and pending")
        if self.termination == SearchTermination.EXHAUSTED:
            if self.total_candidates is None or self.visited_candidates != self.total_candidates:
                raise ValueError("exhausted search requires visited == known total candidates")
            if pending:
                raise ValueError("exhausted search cannot have pending shards")
        object.__setattr__(self, "completed_shards", completed)
        object.__setattr__(self, "pending_shards", pending)

    @property
    def exactness(self) -> Exactness:
        if self.termination == SearchTermination.EXHAUSTED:
            return Exactness.BOUNDED_EXACT
        return Exactness.EXPERIMENTAL

    @property
    def bounded_complete(self) -> bool:
        return self.exactness == Exactness.BOUNDED_EXACT

    @property
    def unenumerated_scope(self) -> Tuple[str, ...]:
        result = list(self.domain.excluded_scope)
        if not self.bounded_complete:
            result.insert(0, "the unvisited remainder of the declared E2 search domain")
        return tuple(result)

    def to_canonical_dict(self) -> dict:
        return {
            "accepted_candidates": self.accepted_candidates,
            "bounded_complete": self.bounded_complete,
            "candidate_encoding": self.candidate_encoding,
            "completed_shards": self.completed_shards,
            "domain": self.domain,
            "enumeration_order": self.enumeration_order,
            "enumerator": self.enumerator,
            "enumerator_version": self.enumerator_version,
            "exactness": self.exactness,
            "pending_shards": self.pending_shards,
            "resource_bound": self.resource_bound,
            "schema": self.SCHEMA_ID,
            "termination": self.termination,
            "total_candidates": self.total_candidates,
            "unenumerated_scope": self.unenumerated_scope,
            "visited_candidates": self.visited_candidates,
        }


@dataclass(frozen=True)
class HalfSpaceCapabilityReport:
    exact_lattice_geometry: bool
    bounded_periodic_domain_schema: bool
    bounded_periodic_enumerator: bool
    uniform_prime_lh_contraction: bool
    uniform_prime_primary_subquotient: bool
    symbolic_halfspace_modules: bool
    unsupported_symbolic_outputs: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.halfspace_capability_report.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "bounded_periodic_domain_schema": self.bounded_periodic_domain_schema,
            "bounded_periodic_enumerator": self.bounded_periodic_enumerator,
            "exact_lattice_geometry": self.exact_lattice_geometry,
            "schema": self.SCHEMA_ID,
            "symbolic_halfspace_modules": self.symbolic_halfspace_modules,
            "uniform_prime_lh_contraction": self.uniform_prime_lh_contraction,
            "uniform_prime_primary_subquotient":
                self.uniform_prime_primary_subquotient,
            "unsupported_symbolic_outputs": self.unsupported_symbolic_outputs,
        }


def halfspace_capability_report() -> HalfSpaceCapabilityReport:
    """Report implemented contracts without manufacturing symbolic results."""

    return HalfSpaceCapabilityReport(
        exact_lattice_geometry=True,
        bounded_periodic_domain_schema=True,
        bounded_periodic_enumerator=False,
        uniform_prime_lh_contraction=True,
        uniform_prime_primary_subquotient=True,
        symbolic_halfspace_modules=False,
        unsupported_symbolic_outputs=(
            "P_boundary",
            "secondary_boundary_module",
            "quasi_symplectic_pairing",
            "boundary_to_bulk_map",
            "relative_Ext",
        ),
    )


__all__ = [
    "AncillaBound",
    "BoundedPeriodicSearchDomain",
    "GeneratorSupportBound",
    "HalfSpaceCapabilityReport",
    "ResourceBound",
    "SearchSpaceCertificate",
    "SearchTermination",
    "halfspace_capability_report",
]
