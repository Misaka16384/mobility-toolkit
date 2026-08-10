"""Mobility-enriched support enumeration for axial X-cube line defects.

This module deliberately stops short of a Cheshire-species classification.
For a fixed oriented coordinate axis it exhausts the nonzero totally singular
subgroups of the five-generator support space used by the exploratory X-cube
reference.  There are 58 such subgroups.  Every emitted record is therefore a
``support_candidate`` and carries the missing algebra, junction, circuit, and
thermodynamic obligations needed to promote it.

The enumeration is repeated for x, y, and z axes.  Cubic symmetry relates the
three copies but is reported as an additional quotient rather than silently
changing the primary fixed-oriented-axis labels.  Planon dressing is retained
in the default labels; the corresponding foliated quotient is intentionally
left unsupported.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from math import gcd
from typing import Iterable, Optional, Tuple

from mobility_toolkit.core import ComputationResult, canonical_hash
from mobility_toolkit.finite import FiniteIntegerBackend

from mobility_toolkit.defects.cheshire_classification import (
    CheshireEvidenceTier,
    EvidenceStatus,
)
from mobility_toolkit.defects.fracton_cheshire import (
    analyze_xcube_fracton_line_reference,
    xcube_axial_line_reference_request,
)


_AXES = ("x", "y", "z")
_AXIS_LABELS = {
    "x": ("ell_x", "e_y", "m_y", "e_z", "m_z"),
    "y": ("ell_y", "e_z", "m_z", "e_x", "m_x"),
    "z": ("ell_z", "e_x", "m_x", "e_y", "m_y"),
}
_DEFAULT_EQUIVALENCE = (
    "fixed oriented coordinate axis + finite-depth equivalence + retained "
    "planon dressing"
)
_MISSING_OBLIGATIONS = (
    "construct an associative unital multiplication/cochain on the support",
    "construct position-independent endpoint and junction spaces",
    "verify orientation-aware Morita equivalence rather than support equality",
    "construct and replay a sequential creation circuit",
    "construct and replay finite-depth deformation and ordered-fusion circuits",
    "control finite-size scaling and the thermodynamic gap",
)


@dataclass(frozen=True)
class PrimitiveRationalDirection:
    """An oriented rational lattice line represented by a primitive vector."""

    components: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.primitive_rational_direction.v2"

    def __post_init__(self) -> None:
        if len(self.components) < 2:
            raise ValueError("a lattice direction needs at least two components")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in self.components
        ):
            raise TypeError("direction components must be plain integers")
        nonzero = tuple(abs(value) for value in self.components if value)
        if not nonzero:
            raise ValueError("the zero vector is not a line direction")
        divisor = nonzero[0]
        for value in nonzero[1:]:
            divisor = gcd(divisor, value)
        if divisor != 1:
            raise ValueError("direction components must be primitive")

    @property
    def reversed(self) -> "PrimitiveRationalDirection":
        return PrimitiveRationalDirection(
            tuple(-value for value in self.components)
        )

    def to_canonical_dict(self) -> dict:
        return {
            "components": self.components,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class StratifiedTubeRecord:
    """Geometry-only carrier for rational lines, endpoints, and junctions."""

    tube_id: str
    direction: PrimitiveRationalDirection
    bulk_cell_ids: Tuple[str, ...]
    boundary_strata_cell_ids: Tuple[Tuple[str, Tuple[str, ...]], ...]
    endpoint_ids: Tuple[str, ...]
    junction_ids: Tuple[str, ...]
    geometry_evidence_status: EvidenceStatus
    missing_physical_obligations: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.stratified_tube_record.v2"

    def __post_init__(self) -> None:
        if not self.tube_id:
            raise ValueError("tube_id must be nonempty")
        stratum_ids = tuple(
            stratum_id
            for stratum_id, _cell_ids in self.boundary_strata_cell_ids
        )
        if any(not item for item in stratum_ids):
            raise ValueError("stratum IDs must be nonempty")
        if len(set(stratum_ids)) != len(stratum_ids):
            raise ValueError("stratum IDs must be unique")
        if len(set(self.endpoint_ids)) != len(self.endpoint_ids):
            raise ValueError("endpoint IDs must be unique")
        if len(set(self.junction_ids)) != len(self.junction_ids):
            raise ValueError("junction IDs must be unique")

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_strata_cell_ids": self.boundary_strata_cell_ids,
            "bulk_cell_ids": self.bulk_cell_ids,
            "direction": self.direction,
            "endpoint_ids": self.endpoint_ids,
            "geometry_evidence_status": self.geometry_evidence_status,
            "junction_ids": self.junction_ids,
            "missing_physical_obligations":
                self.missing_physical_obligations,
            "schema": self.SCHEMA_ID,
            "tube_id": self.tube_id,
        }


@dataclass(frozen=True)
class FractonClassificationScope:
    """The inequivalent quotients that a fracton result must name."""

    microscopic_equivalence: bool
    finite_depth_equivalence: bool
    foliated_equivalence: bool
    quotient_orientation_reversal: bool
    quotient_cubic_symmetry: bool
    retain_planon_dressing: bool

    SCHEMA_ID = "mobility_toolkit.fracton_classification_scope.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "finite_depth_equivalence": self.finite_depth_equivalence,
            "foliated_equivalence": self.foliated_equivalence,
            "microscopic_equivalence": self.microscopic_equivalence,
            "quotient_cubic_symmetry": self.quotient_cubic_symmetry,
            "quotient_orientation_reversal":
                self.quotient_orientation_reversal,
            "retain_planon_dressing": self.retain_planon_dressing,
            "schema": self.SCHEMA_ID,
        }


DEFAULT_FRACTON_CLASSIFICATION_SCOPE = FractonClassificationScope(
    microscopic_equivalence=False,
    finite_depth_equivalence=True,
    foliated_equivalence=False,
    quotient_orientation_reversal=False,
    quotient_cubic_symmetry=False,
    retain_planon_dressing=True,
)


def _bit_parity(value: int) -> int:
    return value.bit_count() & 1


def _quadratic(vector: int) -> int:
    """q(ell,e1,m1,e2,m2) = e1*m1 + e2*m2 over GF(2)."""

    return (
        (((vector >> 1) & 1) & ((vector >> 2) & 1))
        ^ (((vector >> 3) & 1) & ((vector >> 4) & 1))
    )


def _bilinear(left: int, right: int) -> int:
    return _quadratic(left ^ right) ^ _quadratic(left) ^ _quadratic(right)


def _constituent_mobility_dimension(value: int) -> int:
    """Mobility of one nonzero sector in the fixed-axis five-generator slice."""

    if value == 0:
        raise ValueError("the vacuum does not define a constituent mobility")
    if value & 1:
        return 1
    occupies_first_transverse_plane = bool(value & 0b00110)
    occupies_second_transverse_plane = bool(value & 0b11000)
    if occupies_first_transverse_plane and occupies_second_transverse_plane:
        return 1
    return 2


def _span(generators: Iterable[int]) -> frozenset[int]:
    elements = {0}
    for generator in generators:
        elements |= {value ^ generator for value in tuple(elements)}
    return frozenset(elements)


def _canonical_generators(subspace: frozenset[int]) -> Tuple[int, ...]:
    """Return the lexicographically deterministic GF(2) row-echelon basis."""

    basis: list[int] = []
    pivots: list[int] = []
    for candidate in sorted(subspace):
        value = candidate
        for pivot, generator in zip(pivots, basis):
            if (value >> pivot) & 1:
                value ^= generator
        if value:
            pivot = value.bit_length() - 1
            insert_at = 0
            while insert_at < len(pivots) and pivots[insert_at] > pivot:
                insert_at += 1
            pivots.insert(insert_at, pivot)
            basis.insert(insert_at, value)
            for index, generator in enumerate(tuple(basis)):
                if index != insert_at and ((generator >> pivot) & 1):
                    basis[index] ^= value
    return tuple(basis)


@lru_cache(maxsize=1)
def _all_subspaces() -> Tuple[frozenset[int], ...]:
    # Memoised: this closes over every subspace of F2^5 by repeated spanning,
    # which dominates the axial enumeration (~19 ms) and depends on nothing.
    # The result is an immutable tuple of frozensets, so sharing it is safe.
    subspaces = {frozenset({0})}
    for vector in range(1, 1 << 5):
        additions = {
            _span(tuple(subspace) + (vector,))
            for subspace in tuple(subspaces)
            if vector not in subspace
        }
        subspaces.update(additions)
    return tuple(
        sorted(
            subspaces,
            key=lambda subgroup: (
                len(subgroup),
                _canonical_generators(subgroup),
            ),
        )
    )


@lru_cache(maxsize=1)
def _totally_singular_subspaces() -> Tuple[frozenset[int], ...]:
    return tuple(
        subgroup
        for subgroup in _all_subspaces()
        if len(subgroup) > 1 and all(_quadratic(value) == 0 for value in subgroup)
    )


def _vector_label(vector: int, labels: Tuple[str, ...]) -> str:
    if vector == 0:
        return "1"
    factors = tuple(
        label for index, label in enumerate(labels) if (vector >> index) & 1
    )
    return "*".join(factors)


def _orthogonal(subspace: frozenset[int]) -> frozenset[int]:
    return frozenset(
        vector
        for vector in range(1 << 5)
        if all(_bilinear(vector, support) == 0 for support in subspace)
    )


def _orthogonal_quotient_representatives(
    subspace: frozenset[int],
) -> Tuple[int, ...]:
    orthogonal = _orthogonal(subspace)
    unseen = set(orthogonal)
    representatives = []
    while unseen:
        representative = min(unseen)
        coset = {representative ^ support for support in subspace}
        unseen.difference_update(coset)
        if representative:
            representatives.append(representative)
    return tuple(representatives)


def _transverse_swap(vector: int) -> int:
    return (
        (vector & 1)
        | (((vector >> 1) & 1) << 3)
        | (((vector >> 2) & 1) << 4)
        | (((vector >> 3) & 1) << 1)
        | (((vector >> 4) & 1) << 2)
    )


def _transverse_cubic_orbit_count(
    subspaces: Tuple[frozenset[int], ...],
) -> int:
    remaining = set(subspaces)
    count = 0
    while remaining:
        subgroup = min(
            remaining, key=lambda item: (len(item), tuple(sorted(item)))
        )
        partner = frozenset(_transverse_swap(value) for value in subgroup)
        remaining.discard(subgroup)
        remaining.discard(partner)
        count += 1
    return count


@dataclass(frozen=True)
class MobilityEnrichedDatum:
    candidate_id: str
    axis: str
    orientation: str
    primitive_direction: PrimitiveRationalDirection
    support_dimension: int
    support_generators: Tuple[str, ...]
    condensed_support: Tuple[str, ...]
    translation_stabilizer: Tuple[str, ...]
    constituent_mobility_dimensions: Tuple[Tuple[str, int], ...]
    maximum_constituent_mobility_dimension: int
    fusion_sector: str
    planon_dressing: Tuple[str, ...]
    planon_dressing_retained: bool
    hidden_global_charge_representatives: Tuple[str, ...]
    endpoint_admissibility: str
    finite_size_degeneracy_scaling: str
    junction_data_status: EvidenceStatus
    crossing_data_status: EvidenceStatus
    associator_status: EvidenceStatus
    evidence_tier: CheshireEvidenceTier
    missing_obligations: Tuple[str, ...]
    record_hash: str

    SCHEMA_ID = "mobility_toolkit.mobility_enriched_datum.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "associator_status": self.associator_status,
            "axis": self.axis,
            "candidate_id": self.candidate_id,
            "condensed_support": self.condensed_support,
            "constituent_mobility_dimensions":
                self.constituent_mobility_dimensions,
            "crossing_data_status": self.crossing_data_status,
            "endpoint_admissibility": self.endpoint_admissibility,
            "evidence_tier": self.evidence_tier,
            "finite_size_degeneracy_scaling":
                self.finite_size_degeneracy_scaling,
            "fusion_sector": self.fusion_sector,
            "hidden_global_charge_representatives":
                self.hidden_global_charge_representatives,
            "junction_data_status": self.junction_data_status,
            "maximum_constituent_mobility_dimension":
                self.maximum_constituent_mobility_dimension,
            "missing_obligations": self.missing_obligations,
            "orientation": self.orientation,
            "planon_dressing": self.planon_dressing,
            "planon_dressing_retained": self.planon_dressing_retained,
            "primitive_direction": self.primitive_direction,
            "record_hash": self.record_hash,
            "schema": self.SCHEMA_ID,
            "support_dimension": self.support_dimension,
            "support_generators": self.support_generators,
            "translation_stabilizer": self.translation_stabilizer,
        }


@dataclass(frozen=True)
class FractonEquivalenceSummary:
    default_equivalence_relation: str
    raw_fixed_axis_count: int
    oriented_fixed_axis_count: int
    orientation_reversal_orbit_count: int
    all_axes_raw_count: int
    cubic_symmetry_orbit_count: int
    planon_generated_support_count: int
    all_constituents_planon_mobile_support_count: int
    all_constituents_line_mobile_support_count: int
    mixed_constituent_mobility_support_count: int
    nonzero_intrinsic_lineon_projection_count: int
    algebraic_planon_quotient_nontrivial_count: int
    foliated_planon_dressing_quotient_count: Optional[int]
    foliated_quotient_status: EvidenceStatus
    explanation: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.fracton_equivalence_summary.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "all_axes_raw_count": self.all_axes_raw_count,
            "cubic_symmetry_orbit_count": self.cubic_symmetry_orbit_count,
            "default_equivalence_relation": self.default_equivalence_relation,
            "explanation": self.explanation,
            "foliated_planon_dressing_quotient_count":
                self.foliated_planon_dressing_quotient_count,
            "foliated_quotient_status": self.foliated_quotient_status,
            "algebraic_planon_quotient_nontrivial_count":
                self.algebraic_planon_quotient_nontrivial_count,
            "all_constituents_line_mobile_support_count":
                self.all_constituents_line_mobile_support_count,
            "all_constituents_planon_mobile_support_count":
                self.all_constituents_planon_mobile_support_count,
            "mixed_constituent_mobility_support_count":
                self.mixed_constituent_mobility_support_count,
            "nonzero_intrinsic_lineon_projection_count":
                self.nonzero_intrinsic_lineon_projection_count,
            "orientation_reversal_orbit_count":
                self.orientation_reversal_orbit_count,
            "oriented_fixed_axis_count": self.oriented_fixed_axis_count,
            "planon_generated_support_count":
                self.planon_generated_support_count,
            "raw_fixed_axis_count": self.raw_fixed_axis_count,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class ConditionalCountDiagnostic:
    diagnostic_id: str
    count: int
    assumptions: Tuple[str, ...]
    evidence_status: EvidenceStatus
    forbidden_interpretation: str

    SCHEMA_ID = "mobility_toolkit.conditional_count_diagnostic.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "count": self.count,
            "diagnostic_id": self.diagnostic_id,
            "evidence_status": self.evidence_status,
            "forbidden_interpretation": self.forbidden_interpretation,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class XCubeCheshireCandidateCatalog:
    selected_axes: Tuple[str, ...]
    orientation: str
    candidates: Tuple[MobilityEnrichedDatum, ...]
    equivalence_summary: FractonEquivalenceSummary
    conditional_diagnostics: Tuple[ConditionalCountDiagnostic, ...]
    finite_static_reference: Optional[ComputationResult]
    support_search_complete: bool
    classification_complete: bool
    highest_uniform_evidence_tier: CheshireEvidenceTier
    evidence_status: EvidenceStatus
    missing_obligations: Tuple[str, ...]
    warnings: Tuple[str, ...]
    transcript_hash: str

    SCHEMA_ID = "mobility_toolkit.xcube_cheshire_candidate_catalog.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "candidates": self.candidates,
            "classification_complete": self.classification_complete,
            "conditional_diagnostics": self.conditional_diagnostics,
            "equivalence_summary": self.equivalence_summary,
            "evidence_status": self.evidence_status,
            "finite_static_reference": self.finite_static_reference,
            "highest_uniform_evidence_tier": self.highest_uniform_evidence_tier,
            "missing_obligations": self.missing_obligations,
            "orientation": self.orientation,
            "schema": self.SCHEMA_ID,
            "selected_axes": self.selected_axes,
            "support_search_complete": self.support_search_complete,
            "transcript_hash": self.transcript_hash,
            "warnings": self.warnings,
        }


def _candidate(
    axis: str,
    orientation: str,
    subgroup: frozenset[int],
) -> MobilityEnrichedDatum:
    labels = _AXIS_LABELS[axis]
    generators = _canonical_generators(subgroup)
    generator_labels = tuple(_vector_label(value, labels) for value in generators)
    support_labels = tuple(
        _vector_label(value, labels) for value in sorted(subgroup) if value
    )
    planons = tuple(
        _vector_label(value, labels)
        for value in sorted(subgroup)
        if value and not (value & 1)
    )
    constituent_mobility = tuple(
        (
            label,
            _constituent_mobility_dimension(value),
        )
        for value, label in (
            (value, _vector_label(value, labels))
            for value in sorted(subgroup)
            if value
        )
    )
    hidden = tuple(
        _vector_label(value, labels)
        for value in _orthogonal_quotient_representatives(subgroup)
    )
    support_key = "-".join(f"{value:02x}" for value in generators)
    candidate_id = f"xcube:{axis}{orientation}:{support_key}"
    record_payload = {
        "axis": axis,
        "candidate_id": candidate_id,
        "generators": generators,
        "orientation": orientation,
        "support": tuple(sorted(subgroup)),
    }
    return MobilityEnrichedDatum(
        candidate_id=candidate_id,
        axis=axis,
        orientation=orientation,
        primitive_direction=PrimitiveRationalDirection(
            {
                "x": (1 if orientation == "+" else -1, 0, 0),
                "y": (0, 1 if orientation == "+" else -1, 0),
                "z": (0, 0, 1 if orientation == "+" else -1),
            }[axis]
        ),
        support_dimension=len(generators),
        support_generators=generator_labels,
        condensed_support=support_labels,
        translation_stabilizer=(f"translation_along_{axis}",),
        constituent_mobility_dimensions=constituent_mobility,
        maximum_constituent_mobility_dimension=max(
            dimension for _, dimension in constituent_mobility
        ),
        fusion_sector="totally_singular_support_subgroup_over_GF2",
        planon_dressing=planons,
        planon_dressing_retained=True,
        hidden_global_charge_representatives=hidden,
        endpoint_admissibility=(
            "undetermined: support isotropy is necessary but does not construct "
            "an endpoint module"
        ),
        finite_size_degeneracy_scaling=(
            "not_computed_for_this_support: no degeneracy-to-species inference"
        ),
        junction_data_status=EvidenceStatus.UNSUPPORTED,
        crossing_data_status=EvidenceStatus.UNSUPPORTED,
        associator_status=EvidenceStatus.UNSUPPORTED,
        evidence_tier=CheshireEvidenceTier.SUPPORT_CANDIDATE,
        missing_obligations=_MISSING_OBLIGATIONS,
        record_hash=canonical_hash("xcube-support-candidate-v2", record_payload),
    )


def xcube_cheshire_candidates(
    *,
    axis: str = "all",
    orientation: str = "+",
    include_finite_static_reference: bool = False,
    finite_reference_line_length: int = 1,
    backend: Optional[FiniteIntegerBackend] = None,
) -> XCubeCheshireCandidateCatalog:
    """Exhaust the fixed-axis support slice without promoting it to species."""

    if axis not in (*_AXES, "all"):
        raise ValueError("axis must be x, y, z, or all")
    if orientation not in {"+", "-"}:
        raise ValueError("orientation must be '+' or '-'")
    if (
        isinstance(finite_reference_line_length, bool)
        or not isinstance(finite_reference_line_length, int)
        or finite_reference_line_length < 1
    ):
        raise ValueError("finite_reference_line_length must be a positive integer")
    if include_finite_static_reference and backend is None:
        raise ValueError("a finite integer backend is required for the static reference")
    if include_finite_static_reference and orientation != "+":
        raise ValueError(
            "the finite static X-cube reference is source-locked to the +z "
            "orientation; no orientation-reversal certificate is implemented"
        )

    singular_subspaces = _totally_singular_subspaces()
    if len(singular_subspaces) != 58:
        raise RuntimeError(
            "the exact five-generator X-cube support enumeration did not return 58"
        )
    selected_axes = _AXES if axis == "all" else (axis,)
    candidates = tuple(
        _candidate(selected_axis, orientation, subgroup)
        for selected_axis in selected_axes
        for subgroup in singular_subspaces
    )
    finite_reference = None
    if include_finite_static_reference:
        if axis not in {"z", "all"}:
            raise ValueError(
                "the current finite static X-cube reference is implemented only "
                "for the z-axis"
            )
        assert backend is not None
        finite_reference = analyze_xcube_fracton_line_reference(
            xcube_axial_line_reference_request(finite_reference_line_length),
            backend,
        )
        if finite_reference.exactness.value != "unsupported":
            upgraded = []
            for item in candidates:
                if (
                    item.axis == "z"
                    and item.support_generators == ("ell_z",)
                ):
                    upgraded.append(
                        replace(
                            item,
                            endpoint_admissibility=(
                                "bounded finite-static local q2 z-lineon "
                                "condensate completion constructed"
                            ),
                            finite_size_degeneracy_scaling=(
                                "rank-one hidden-charge sector is exact for "
                                "the attached finite completion; no "
                                "thermodynamic extrapolation"
                            ),
                            evidence_tier=(
                                CheshireEvidenceTier.STATIC_CHESHIRE_CANDIDATE
                            ),
                            missing_obligations=tuple(
                                obligation
                                for obligation in item.missing_obligations
                                if "finite-size scaling" not in obligation
                            ),
                            record_hash=canonical_hash(
                                "xcube-static-candidate-upgrade-v2",
                                {
                                    "finite_reference":
                                        finite_reference.canonical_input_hash,
                                    "support_record": item.record_hash,
                                },
                            ),
                        )
                    )
                else:
                    upgraded.append(item)
            candidates = tuple(upgraded)

    cubic_orbits = _transverse_cubic_orbit_count(singular_subspaces)
    planon_generated_count = sum(
        all(not (value & 1) for value in subgroup)
        for subgroup in singular_subspaces
    )
    lineon_projection_count = len(singular_subspaces) - planon_generated_count
    mobility_profiles = tuple(
        frozenset(
            _constituent_mobility_dimension(value)
            for value in subgroup
            if value
        )
        for subgroup in singular_subspaces
    )
    all_planon_mobile_count = mobility_profiles.count(frozenset({2}))
    all_line_mobile_count = mobility_profiles.count(frozenset({1}))
    mixed_mobility_count = mobility_profiles.count(frozenset({1, 2}))
    if (
        all_planon_mobile_count
        + all_line_mobile_count
        + mixed_mobility_count
        != len(singular_subspaces)
    ):
        raise ArithmeticError("mobility-profile partition did not exhaust supports")
    summary = FractonEquivalenceSummary(
        default_equivalence_relation=_DEFAULT_EQUIVALENCE,
        raw_fixed_axis_count=58,
        oriented_fixed_axis_count=58,
        orientation_reversal_orbit_count=58,
        all_axes_raw_count=174,
        cubic_symmetry_orbit_count=cubic_orbits,
        planon_generated_support_count=planon_generated_count,
        all_constituents_planon_mobile_support_count=all_planon_mobile_count,
        all_constituents_line_mobile_support_count=all_line_mobile_count,
        mixed_constituent_mobility_support_count=mixed_mobility_count,
        nonzero_intrinsic_lineon_projection_count=lineon_projection_count,
        algebraic_planon_quotient_nontrivial_count=1,
        foliated_planon_dressing_quotient_count=None,
        foliated_quotient_status=EvidenceStatus.UNSUPPORTED,
        explanation=(
            "Over Z2, orientation reversal preserves each support subgroup but "
            "does not certify the corresponding defect or algebra.",
            "Cubic permutations identify coordinate-axis copies and the "
            "transverse-axis swap; this gives 41 support orbits.",
            "Fifteen supports lie in the subgroup generated by planons, but only "
            "four have exclusively two-dimensionally mobile nontrivial "
            "constituents; products of transverse planons can be line-mobile.",
            "Algebraically quotienting all planons leaves one nontrivial lineon "
            "projection, but a physical foliated-equivalence species count "
            "requires explicit planon attachment circuits and remains unsupported.",
        ),
    )
    diagnostics = (
        ConditionalCountDiagnostic(
            diagnostic_id="support_cochain_count_134",
            count=134,
            assumptions=(
                "attach ordinary support-group cohomology data",
                "ignore position-dependent fracton junction constraints",
                "do not quotient by a certified mobility-enriched Morita relation",
            ),
            evidence_status=EvidenceStatus.CONDITIONAL,
            forbidden_interpretation="not an X-cube Cheshire species count",
        ),
        ConditionalCountDiagnostic(
            diagnostic_id="unrestricted_cochain_count_4590",
            count=4590,
            assumptions=(
                "include all cochain decorations in the exploratory counting domain",
                "ignore microscopic circuit realizability",
                "ignore fracton associativity and junction obstructions",
            ),
            evidence_status=EvidenceStatus.CONDITIONAL,
            forbidden_interpretation="not an X-cube Cheshire species count",
        ),
    )
    warnings = (
        "The number 58 is complete only for nonzero totally singular support "
        "subgroups of one fixed five-generator axial slice.",
        "classification_complete=false: no multiplication, mobility-enriched "
        "Morita quotient, or creation/deformation/fusion circuit was constructed.",
        "Primary labels retain the oriented axis and planon dressing; orientation, "
        "cubic-symmetry, and foliated quotients are reported separately.",
        "Finite static degeneracy, if requested, is evidence about the supplied "
        "patch only and is not a thermodynamic species invariant.",
    )
    transcript_hash = canonical_hash(
        "xcube-cheshire-candidates-v2",
        {
            "candidate_hashes": tuple(item.record_hash for item in candidates),
            "diagnostics": diagnostics,
            "orientation": orientation,
            "selected_axes": selected_axes,
            "support_search_complete": True,
        },
    )
    return XCubeCheshireCandidateCatalog(
        selected_axes=selected_axes,
        orientation=orientation,
        candidates=candidates,
        equivalence_summary=summary,
        conditional_diagnostics=diagnostics,
        finite_static_reference=finite_reference,
        support_search_complete=True,
        classification_complete=False,
        highest_uniform_evidence_tier=CheshireEvidenceTier.SUPPORT_CANDIDATE,
        evidence_status=EvidenceStatus.COMPUTED_EXACT,
        missing_obligations=_MISSING_OBLIGATIONS,
        warnings=warnings,
        transcript_hash=transcript_hash,
    )


__all__ = [
    "ConditionalCountDiagnostic",
    "DEFAULT_FRACTON_CLASSIFICATION_SCOPE",
    "FractonClassificationScope",
    "FractonEquivalenceSummary",
    "MobilityEnrichedDatum",
    "PrimitiveRationalDirection",
    "StratifiedTubeRecord",
    "XCubeCheshireCandidateCatalog",
    "xcube_cheshire_candidates",
]
