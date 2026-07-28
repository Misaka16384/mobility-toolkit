"""Exact support-window boundary algebras for finite stabilizer systems.

The objects in this module are deliberately finite-window objects.  They do
not identify translates, minimize supports, or infer an infinite half-space
algebra from repeated finite-size data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence, Tuple

from mobility_toolkit.core import Exactness, PauliOperator, PresentedModule, SparseIntMatrix
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FiniteGroupHomomorphism,
    FiniteIntegerBackend,
    FiniteQuotient,
    FiniteStabilizerAnalysis,
    FiniteSubgroup,
    PairedFiniteAbelianGroup,
    PairedFiniteQuotient,
)


def _columns(matrix: SparseIntMatrix) -> Tuple[Tuple[int, ...], ...]:
    rows = matrix.to_rows()
    return tuple(
        tuple(rows[row][column] for row in range(matrix.nrows))
        for column in range(matrix.ncols)
    )


class BoundaryOperatorKind(str, Enum):
    """Finite-window algebraic role of a supported operator.

    Primary/secondary labels are only assigned when an explicit projected
    cut-stabilizer image is supplied.  The radical of the induced pairing is a
    separate object and never determines these labels.
    """

    PRIMARY_CANDIDATE = "primary_candidate"
    SECONDARY_CANDIDATE = "secondary_candidate"
    BULK_TRIVIAL = "bulk_trivial"
    UNCLASSIFIED_NONTRIVIAL = "unclassified_nontrivial"


@dataclass(frozen=True)
class SupportWindow:
    window_id: str
    paulis: FiniteSubgroup
    site_ids: Tuple[str, ...] = ()
    search_extent: Tuple[Tuple[str, int], ...] = ()

    SCHEMA_ID = "mobility_toolkit.support_window.v1"

    def __post_init__(self) -> None:
        if not self.window_id:
            raise ValueError("window_id must be nonempty")
        object.__setattr__(self, "site_ids", tuple(sorted(set(self.site_ids))))
        extent = tuple(sorted(tuple(item) for item in self.search_extent))
        if any(len(item) != 2 or not isinstance(item[0], str) for item in extent):
            raise ValueError("search_extent must contain (name, integer) pairs")
        if any(isinstance(item[1], bool) or not isinstance(item[1], int) for item in extent):
            raise ValueError("search extents must be integers")
        object.__setattr__(self, "search_extent", extent)

    def to_canonical_dict(self) -> dict:
        return {
            "paulis": self.paulis,
            "schema": self.SCHEMA_ID,
            "search_extent": self.search_extent,
            "site_ids": self.site_ids,
            "window_id": self.window_id,
        }


@dataclass(frozen=True)
class TangentTranslationSpec:
    """An explicit ambient projective-Pauli automorphism.

    No quotient by this action is performed.  Keeping the action itself is
    essential for later periodic and orbit-aware boundary calculations.
    """

    name: str
    lift_matrix: SparseIntMatrix

    SCHEMA_ID = "mobility_toolkit.tangent_translation_spec.v1"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("translation name must be nonempty")

    def to_canonical_dict(self) -> dict:
        return {
            "lift_matrix": self.lift_matrix,
            "name": self.name,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class TangentTranslationAction:
    name: str
    ambient_action: FiniteGroupHomomorphism
    quotient_action: FiniteGroupHomomorphism
    numerator_coordinate_matrix: SparseIntMatrix

    SCHEMA_ID = "mobility_toolkit.tangent_translation_action.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_action": self.ambient_action,
            "name": self.name,
            "numerator_coordinate_matrix": self.numerator_coordinate_matrix,
            "quotient_action": self.quotient_action,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class BoundaryOperatorClassification:
    kind: BoundaryOperatorKind
    ambient_vector: Tuple[int, ...]
    criterion: str

    SCHEMA_ID = "mobility_toolkit.boundary_operator_classification.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_vector": self.ambient_vector,
            "criterion": self.criterion,
            "kind": self.kind,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PrimaryBoundaryImage:
    """Explicit finite-window image of projected/cut bulk stabilizers."""

    image_in_local_centralizer: FiniteSubgroup
    image_modulo_bulk_trivial: FiniteQuotient
    source_description: str

    SCHEMA_ID = "mobility_toolkit.primary_boundary_image.v1"

    def __post_init__(self) -> None:
        if not self.source_description:
            raise ValueError("primary source_description must be nonempty")

    def to_canonical_dict(self) -> dict:
        return {
            "image_in_local_centralizer": self.image_in_local_centralizer,
            "image_modulo_bulk_trivial": self.image_modulo_bulk_trivial,
            "schema": self.SCHEMA_ID,
            "source_description": self.source_description,
        }


@dataclass(frozen=True)
class FiniteBoundaryAlgebra:
    """The exact finite quotient ``(S^perp intersect W)/(S intersect W)``."""

    analysis: FiniteStabilizerAnalysis
    window: SupportWindow
    local_centralizer: FiniteSubgroup
    bulk_trivial: FiniteSubgroup
    paired_algebra: PairedFiniteQuotient
    radical_numerator: FiniteSubgroup
    radical: FiniteQuotient
    primary_image: Optional[PrimaryBoundaryImage]
    presentation_generator_lifts: Tuple[PauliOperator, ...]
    tangent_translations: Tuple[TangentTranslationAction, ...]
    exactness: Exactness = Exactness.BOUNDED_EXACT
    theorem_scope: str = (
        "exact only for the supplied finite stabilizer system and support window; "
        "no thermodynamic stabilization or half-space completeness is asserted"
    )

    SCHEMA_ID = "mobility_toolkit.finite_boundary_algebra.v1"

    @property
    def invariant_factors(self) -> Tuple[int, ...]:
        return self.paired_algebra.invariant_factors

    @property
    def radical_invariant_factors(self) -> Tuple[int, ...]:
        return self.radical.invariant_factors

    @property
    def order(self) -> int:
        return self.paired_algebra.order

    def classify(
        self, vector: Sequence[int], backend: FiniteIntegerBackend
    ) -> BoundaryOperatorClassification:
        values = tuple(vector)
        if len(values) != self.analysis.ambient_projective_paulis.presentation_rank:
            raise ValueError("boundary operator vector has the wrong ambient rank")
        if not self.window.paulis.contains(values, backend):
            raise ValueError("operator is not supported in the declared window")
        if self.bulk_trivial.contains(values, backend):
            return BoundaryOperatorClassification(
                BoundaryOperatorKind.BULK_TRIVIAL,
                values,
                "the operator lies in S_bulk intersect W",
            )
        if not self.local_centralizer.contains(values, backend):
            raise ValueError("operator does not commute with the finite bulk stabilizer")
        if self.primary_image is None:
            return BoundaryOperatorClassification(
                BoundaryOperatorKind.UNCLASSIFIED_NONTRIVIAL,
                values,
                "no projected cut-stabilizer image was supplied, so primary/secondary is undefined",
            )
        if self.primary_image.image_in_local_centralizer.contains(values, backend):
            return BoundaryOperatorClassification(
                BoundaryOperatorKind.PRIMARY_CANDIDATE,
                values,
                "the class lies in the explicitly supplied projected cut-stabilizer image",
            )
        return BoundaryOperatorClassification(
            BoundaryOperatorKind.SECONDARY_CANDIDATE,
            values,
            "the class is in A_W but outside the explicitly supplied primary image; "
            "these secondary classes are a set, not a canonical subgroup",
        )

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_trivial": self.bulk_trivial,
            "exactness": self.exactness,
            "invariant_factors": self.invariant_factors,
            "local_centralizer": self.local_centralizer,
            "order": self.order,
            "presentation_generator_lifts": self.presentation_generator_lifts,
            "paired_algebra": self.paired_algebra,
            "primary_image": self.primary_image,
            "radical_invariant_factors": self.radical_invariant_factors,
            "schema": self.SCHEMA_ID,
            "radical": self.radical,
            "radical_numerator": self.radical_numerator,
            "tangent_translations": self.tangent_translations,
            "theorem_scope": self.theorem_scope,
            "window": self.window,
        }


@dataclass(frozen=True)
class BoundaryStabilityObservation:
    window_id: str
    invariant_factors: Tuple[int, ...]
    radical_invariant_factors: Tuple[int, ...]
    translation_names: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.boundary_stability_observation.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "invariant_factors": self.invariant_factors,
            "radical_invariant_factors": self.radical_invariant_factors,
            "schema": self.SCHEMA_ID,
            "translation_names": self.translation_names,
            "window_id": self.window_id,
        }


@dataclass(frozen=True)
class BoundaryStabilityScan:
    observations: Tuple[BoundaryStabilityObservation, ...]
    stable_tail_length: int
    exactness: Exactness = Exactness.STABILIZED_EMPIRICALLY
    theorem_scope: str = (
        "signature stability across the supplied finite windows only; equality of "
        "thermodynamic boundary algebras is not certified"
    )

    SCHEMA_ID = "mobility_toolkit.boundary_stability_scan.v1"

    @property
    def stabilized(self) -> bool:
        return self.stable_tail_length >= 2

    def to_canonical_dict(self) -> dict:
        return {
            "exactness": self.exactness,
            "observations": self.observations,
            "schema": self.SCHEMA_ID,
            "stabilized": self.stabilized,
            "stable_tail_length": self.stable_tail_length,
            "theorem_scope": self.theorem_scope,
        }


def support_window_from_sites(
    analysis: FiniteStabilizerAnalysis,
    site_ids: Iterable[str],
    backend: FiniteIntegerBackend,
    window_id: str = "site-window",
    search_extent: Sequence[Tuple[str, int]] = (),
) -> SupportWindow:
    requested = tuple(sorted(set(site_ids)))
    known = {system.site_id for system in analysis.module.local_systems}
    unknown = tuple(site_id for site_id in requested if site_id not in known)
    if unknown:
        raise ValueError("unknown boundary-window sites: " + ", ".join(unknown))
    selected = tuple(
        index
        for index, axis in enumerate(analysis.coordinates.axes)
        if axis.site_id in requested
    )
    rank = analysis.ambient_projective_paulis.presentation_rank
    generators = SparseIntMatrix(
        rank,
        len(selected),
        tuple((axis, column, 1) for column, axis in enumerate(selected)),
    )
    subgroup = analysis.ambient_projective_paulis.subgroup(generators, backend)
    return SupportWindow(window_id, subgroup, requested, tuple(search_extent))


def _quotient_group(
    quotient: PairedFiniteQuotient, backend: FiniteIntegerBackend
) -> FiniteAbelianGroup:
    rank = quotient.quotient.inclusion_matrix.nrows
    return FiniteAbelianGroup.from_presentation(
        PresentedModule(rank, quotient.quotient.inclusion_matrix), backend
    )


def _translation_action(
    spec: TangentTranslationSpec,
    analysis: FiniteStabilizerAnalysis,
    local_centralizer: FiniteSubgroup,
    bulk_trivial: FiniteSubgroup,
    window_paulis: FiniteSubgroup,
    quotient: PairedFiniteQuotient,
    backend: FiniteIntegerBackend,
) -> TangentTranslationAction:
    ambient = analysis.ambient_projective_paulis
    ambient_map = FiniteGroupHomomorphism.create(
        ambient, ambient, spec.lift_matrix, backend
    )
    if ambient_map.kernel(backend).order(backend) != 1:
        raise ValueError(f"tangent translation {spec.name!r} is not injective")
    if ambient_map.image(backend).order(backend) != ambient.order(backend):
        raise ValueError(f"tangent translation {spec.name!r} is not surjective")
    modulus = analysis.module.phase_modulus
    pairing = analysis.coordinates.pairing_matrix
    pulled_back = spec.lift_matrix.transpose().matmul(pairing).matmul(spec.lift_matrix)
    pairing_difference = SparseIntMatrix(
        pairing.nrows,
        pairing.ncols,
        tuple(pulled_back.entries) + tuple(pairing.negate().entries),
    )
    if any(value % modulus for _, _, value in pairing_difference.entries):
        raise ValueError(f"tangent translation {spec.name!r} does not preserve the Pauli pairing")

    window_image = ambient.subgroup(
        spec.lift_matrix.matmul(window_paulis.preimage_lattice_basis), backend
    )
    centralizer_image = ambient.subgroup(
        spec.lift_matrix.matmul(local_centralizer.preimage_lattice_basis), backend
    )
    trivial_image = ambient.subgroup(
        spec.lift_matrix.matmul(bulk_trivial.preimage_lattice_basis), backend
    )
    if not window_paulis.contains_subgroup(window_image, backend):
        raise ValueError(f"tangent translation {spec.name!r} does not preserve W")
    if not local_centralizer.contains_subgroup(centralizer_image, backend):
        raise ValueError(f"tangent translation {spec.name!r} does not preserve C_W")
    if not bulk_trivial.contains_subgroup(trivial_image, backend):
        raise ValueError(f"tangent translation {spec.name!r} does not preserve S_W")

    numerator_coordinates = backend.solve_full_lattice(
        local_centralizer.preimage_lattice_basis,
        spec.lift_matrix.matmul(local_centralizer.preimage_lattice_basis),
    )
    quotient_group = _quotient_group(quotient, backend)
    quotient_map = FiniteGroupHomomorphism.create(
        quotient_group, quotient_group, numerator_coordinates, backend
    )
    if quotient_map.kernel(backend).order(backend) != 1:
        raise ArithmeticError("induced tangent action is not injective")
    return TangentTranslationAction(
        spec.name, ambient_map, quotient_map, numerator_coordinates
    )


def analyze_finite_boundary_algebra(
    analysis: FiniteStabilizerAnalysis,
    window: SupportWindow,
    backend: FiniteIntegerBackend,
    tangent_translations: Sequence[TangentTranslationSpec] = (),
    projected_primary_image: Optional[FiniteSubgroup] = None,
    primary_source_description: str = "",
) -> FiniteBoundaryAlgebra:
    """Compute ``C_W``, ``S_W`` and their induced paired quotient exactly."""

    if window.paulis.ambient != analysis.ambient_projective_paulis:
        raise ValueError("support window belongs to a different Pauli ambient group")
    local_centralizer = analysis.centralizer.intersection(window.paulis, backend)
    bulk_trivial = analysis.stabilizer.intersection(window.paulis, backend)
    if not local_centralizer.contains_subgroup(bulk_trivial, backend):
        raise ArithmeticError("S_bulk intersect W is not contained in C_W")
    paired = PairedFiniteAbelianGroup.create(
        analysis.ambient_projective_paulis,
        analysis.module.phase_modulus,
        analysis.coordinates.pairing_matrix,
    )
    quotient = paired.quotient_pairing(local_centralizer, bulk_trivial, backend)
    radical = paired.radical(local_centralizer, backend)
    if not radical.contains_subgroup(bulk_trivial, backend):
        raise ArithmeticError("bulk-trivial window operators are not in the radical")
    radical_quotient = radical.quotient_by(bulk_trivial, backend)
    primary = None
    if projected_primary_image is not None:
        if projected_primary_image.ambient != analysis.ambient_projective_paulis:
            raise ValueError("projected primary image belongs to a different Pauli ambient group")
        if not local_centralizer.contains_subgroup(projected_primary_image, backend):
            raise ValueError("projected primary image is not contained in C_W")
        primary_with_trivial = projected_primary_image.sum(bulk_trivial, backend)
        primary = PrimaryBoundaryImage(
            primary_with_trivial,
            primary_with_trivial.quotient_by(bulk_trivial, backend),
            primary_source_description,
        )
    lifts = tuple(
        analysis.coordinates.operator(column)
        for column in _columns(local_centralizer.preimage_lattice_basis)
    )
    actions = tuple(
        _translation_action(
            spec,
            analysis,
            local_centralizer,
            bulk_trivial,
            window.paulis,
            quotient,
            backend,
        )
        for spec in tangent_translations
    )
    return FiniteBoundaryAlgebra(
        analysis,
        window,
        local_centralizer,
        bulk_trivial,
        quotient,
        radical,
        radical_quotient,
        primary,
        lifts,
        actions,
    )


def scan_finite_window_stability(
    algebras: Sequence[FiniteBoundaryAlgebra],
) -> BoundaryStabilityScan:
    observations = tuple(
        BoundaryStabilityObservation(
            algebra.window.window_id,
            algebra.invariant_factors,
            algebra.radical_invariant_factors,
            tuple(action.name for action in algebra.tangent_translations),
        )
        for algebra in algebras
    )
    tail = 0
    if observations:
        signature = (
            observations[-1].invariant_factors,
            observations[-1].radical_invariant_factors,
            observations[-1].translation_names,
        )
        for observation in reversed(observations):
            current = (
                observation.invariant_factors,
                observation.radical_invariant_factors,
                observation.translation_names,
            )
            if current != signature:
                break
            tail += 1
    return BoundaryStabilityScan(observations, tail)


__all__ = [
    "BoundaryOperatorClassification",
    "BoundaryOperatorKind",
    "BoundaryStabilityObservation",
    "BoundaryStabilityScan",
    "FiniteBoundaryAlgebra",
    "PrimaryBoundaryImage",
    "SupportWindow",
    "TangentTranslationAction",
    "TangentTranslationSpec",
    "analyze_finite_boundary_algebra",
    "scan_finite_window_stability",
    "support_window_from_sites",
]
