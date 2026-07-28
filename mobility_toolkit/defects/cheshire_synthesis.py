"""Certified finite tubular-to-line synthesis for static Cheshire defects.

This module deliberately proves less than a phase-classification routine.  It
revalidates a finite static Hamiltonian at every supplied tube radius and
compares an explicit list of static invariants between adjacent radii.  Passing
all checks proves preservation of those invariants for those finite samples
only.  It does not construct a finite-depth circuit and does not prove phase,
deformation, or thermodynamic equivalence.

The generic entry point accepts either an already materialized
:class:`FiniteTubeLineDefectFamily` or a :class:`CondensationCandidate` whose
builder returns a :class:`~mobility_toolkit.defects.cheshire.CheshireStaticAnalysis`.
E1/E2 boundary-enumeration certificates may be attached as provenance, but an
explicit Cheshire Hamiltonian builder is still required: an isotropic boundary
subgroup is not, by itself, a line-defect Hamiltonian.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Tuple

from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.core.results import Exactness
from mobility_toolkit.defects.cheshire import (
    CheshireStaticAnalysis,
    ClosedLoop,
    LineDefect,
    OpenSegment,
    TubularDefect,
    analyze_toric_cheshire,
)
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.geometry.cell_complex import CubicalComplex


STATIC_SYNTHESIS_SCOPE = (
    "Exact only for the supplied finite static Hamiltonians, tube windows, "
    "candidate list, radii, and declared invariants. No finite-depth circuit, "
    "phase equivalence, deformation equivalence, thermodynamic stabilization, "
    "fusion dynamics, or completeness outside the recorded search domain is claimed."
)

DEFAULT_DECLARED_INVARIANTS = (
    "line_topologies",
    "local_logical_invariant_factors",
    "fixed_sector_logical_invariant_factors",
    "defect_local_invariant_factors",
    "defect_local_pairing_hashes",
    "defect_local_radical_invariant_factors",
    "charge_termination",
    "magnetic_termination",
    "local_gsd_factor",
    "fixed_sector_gsd_factor",
)

_ALLOWED_INVARIANTS = frozenset(
    DEFAULT_DECLARED_INVARIANTS
    + (
        "local_hamiltonian_hash",
        "fixed_sector_hamiltonian_hash",
    )
)


def _tuple_radii(radii: Iterable[int]) -> Tuple[int, ...]:
    values = tuple(radii)
    if not values:
        raise ValueError("at least one tube radius is required")
    if any(
        isinstance(radius, bool) or not isinstance(radius, int) or radius < 0
        for radius in values
    ):
        raise ValueError("tube radii must be nonnegative integers")
    if any(left <= right for left, right in zip(values, values[1:])):
        raise ValueError("tubular-to-line radii must be strictly decreasing")
    if values[-1] != 0:
        raise ValueError("a tubular-to-line synthesis must end at radius zero")
    return values


def _tuple_invariants(values: Iterable[str]) -> Tuple[str, ...]:
    result = tuple(values)
    if not result:
        raise ValueError("at least one declared invariant is required")
    if len(set(result)) != len(result):
        raise ValueError("declared invariant names must be unique")
    unknown = tuple(value for value in result if value not in _ALLOWED_INVARIANTS)
    if unknown:
        raise ValueError("unknown declared Cheshire invariants: " + ", ".join(unknown))
    return result


@dataclass(frozen=True)
class StaticRadiusSample:
    radius_lattice_steps: int
    analysis: CheshireStaticAnalysis

    SCHEMA_ID = "mobility_toolkit.cheshire_static_radius_sample.v1"

    def __post_init__(self) -> None:
        if (
            isinstance(self.radius_lattice_steps, bool)
            or not isinstance(self.radius_lattice_steps, int)
            or self.radius_lattice_steps < 0
        ):
            raise ValueError("sample radius must be a nonnegative integer")
        if not isinstance(self.analysis, CheshireStaticAnalysis):
            raise TypeError("sample analysis must be a CheshireStaticAnalysis")

    def to_canonical_dict(self) -> dict:
        return {
            "analysis": self.analysis,
            "radius_lattice_steps": self.radius_lattice_steps,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class FiniteTubeLineDefectFamily:
    candidate_id: str
    samples: Tuple[StaticRadiusSample, ...]
    declared_invariants: Tuple[str, ...] = DEFAULT_DECLARED_INVARIANTS
    expected_charge_termination: bool = True
    expected_magnetic_termination: bool = False
    source_description: str = "explicit supplied finite tube/line defect family"

    SCHEMA_ID = "mobility_toolkit.finite_tube_line_defect_family.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id:
            raise ValueError("candidate_id must be a nonempty string")
        samples = tuple(self.samples)
        _tuple_radii(sample.radius_lattice_steps for sample in samples)
        object.__setattr__(self, "samples", samples)
        object.__setattr__(
            self, "declared_invariants", _tuple_invariants(self.declared_invariants)
        )
        if not isinstance(self.source_description, str) or not self.source_description:
            raise ValueError("source_description must be nonempty")

    def to_canonical_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "declared_invariants": self.declared_invariants,
            "expected_charge_termination": self.expected_charge_termination,
            "expected_magnetic_termination": self.expected_magnetic_termination,
            "samples": self.samples,
            "schema": self.SCHEMA_ID,
            "source_description": self.source_description,
        }


@dataclass(frozen=True)
class CondensationCandidate:
    """A supplied condensation pattern plus an exact finite-radius builder.

    ``builder`` is intentionally not serialized.  Its returned analyses and
    their canonical hashes are recorded in the result.  A supplied E1/E2
    certificate is provenance only; this class never infers a line Hamiltonian
    from boundary algebra data.
    """

    candidate_id: str
    builder: Callable[[int], CheshireStaticAnalysis]
    declared_invariants: Tuple[str, ...] = DEFAULT_DECLARED_INVARIANTS
    expected_charge_termination: bool = True
    expected_magnetic_termination: bool = False
    source_description: str = "user-supplied condensation candidate"
    boundary_search_certificate: Any = None

    SCHEMA_ID = "mobility_toolkit.cheshire_condensation_candidate.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id:
            raise ValueError("candidate_id must be a nonempty string")
        if not callable(self.builder):
            raise TypeError("condensation candidate builder must be callable")
        object.__setattr__(
            self, "declared_invariants", _tuple_invariants(self.declared_invariants)
        )
        if not isinstance(self.source_description, str) or not self.source_description:
            raise ValueError("source_description must be nonempty")

    @property
    def discovery_basis(self) -> str:
        certificate = self.boundary_search_certificate
        if certificate is None:
            return "supplied_condensation"
        if bool(getattr(certificate, "bounded_complete", False)):
            return "supplied_condensation_with_bounded_complete_e2_provenance"
        if bool(getattr(certificate, "certified_complete", False)):
            return "supplied_condensation_with_complete_e1_provenance"
        return "supplied_condensation_with_noncomplete_search_provenance"

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_search_certificate": self.boundary_search_certificate,
            "candidate_id": self.candidate_id,
            "declared_invariants": self.declared_invariants,
            "discovery_basis": self.discovery_basis,
            "expected_charge_termination": self.expected_charge_termination,
            "expected_magnetic_termination": self.expected_magnetic_termination,
            "schema": self.SCHEMA_ID,
            "source_description": self.source_description,
        }


@dataclass(frozen=True)
class CheshireFiniteInvariantSnapshot:
    radius_lattice_steps: int
    tube_site_counts: Tuple[int, ...]
    line_topologies: Tuple[str, ...]
    local_logical_invariant_factors: Tuple[int, ...]
    fixed_sector_logical_invariant_factors: Tuple[int, ...]
    defect_local_invariant_factors: Tuple[Tuple[int, ...], ...]
    defect_local_pairing_hashes: Tuple[str, ...]
    defect_local_radical_invariant_factors: Tuple[Tuple[int, ...], ...]
    charge_termination: Tuple[bool, ...]
    magnetic_termination: Tuple[bool, ...]
    local_gsd_factor: Tuple[int, int]
    fixed_sector_gsd_factor: Tuple[int, int]
    local_hamiltonian_hash: str
    fixed_sector_hamiltonian_hash: str

    SCHEMA_ID = "mobility_toolkit.cheshire_finite_invariant_snapshot.v1"

    def declared_value(self, name: str) -> Any:
        if name not in _ALLOWED_INVARIANTS:
            raise ValueError("unknown declared Cheshire invariant: " + name)
        return getattr(self, name)

    def to_canonical_dict(self) -> dict:
        return {
            name: getattr(self, name)
            for name in (
                "radius_lattice_steps",
                "tube_site_counts",
                "line_topologies",
                "local_logical_invariant_factors",
                "fixed_sector_logical_invariant_factors",
                "defect_local_invariant_factors",
                "defect_local_pairing_hashes",
                "defect_local_radical_invariant_factors",
                "charge_termination",
                "magnetic_termination",
                "local_gsd_factor",
                "fixed_sector_gsd_factor",
                "local_hamiltonian_hash",
                "fixed_sector_hamiltonian_hash",
            )
        } | {"schema": self.SCHEMA_ID}


@dataclass(frozen=True)
class RadiusStepCertificate:
    radius_lattice_steps: int
    analysis_hash: str
    snapshot_hash: str
    local_hamiltonian_phase_verified: bool
    local_hamiltonian_commutation_verified: bool
    stabilizer_analyses_verified: bool
    defect_local_pairings_verified: bool
    charge_termination_verified: bool
    magnetic_termination_verified: bool
    representation_certificates_verified: bool

    SCHEMA_ID = "mobility_toolkit.cheshire_radius_step_certificate.v1"

    @property
    def verified(self) -> bool:
        return all(
            (
                self.local_hamiltonian_phase_verified,
                self.local_hamiltonian_commutation_verified,
                self.stabilizer_analyses_verified,
                self.defect_local_pairings_verified,
                self.charge_termination_verified,
                self.magnetic_termination_verified,
                self.representation_certificates_verified,
            )
        )

    def to_canonical_dict(self) -> dict:
        return {
            "analysis_hash": self.analysis_hash,
            "charge_termination_verified": self.charge_termination_verified,
            "defect_local_pairings_verified": self.defect_local_pairings_verified,
            "local_hamiltonian_commutation_verified": self.local_hamiltonian_commutation_verified,
            "local_hamiltonian_phase_verified": self.local_hamiltonian_phase_verified,
            "magnetic_termination_verified": self.magnetic_termination_verified,
            "radius_lattice_steps": self.radius_lattice_steps,
            "representation_certificates_verified": self.representation_certificates_verified,
            "schema": self.SCHEMA_ID,
            "snapshot_hash": self.snapshot_hash,
            "stabilizer_analyses_verified": self.stabilizer_analyses_verified,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class AdjacentInvariantCertificate:
    outer_radius: int
    inner_radius: int
    declared_invariants: Tuple[str, ...]
    comparisons: Tuple[Tuple[str, bool], ...]
    outer_snapshot_hash: str
    inner_snapshot_hash: str

    SCHEMA_ID = "mobility_toolkit.cheshire_adjacent_invariant_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.outer_radius > self.inner_radius
            and tuple(name for name, _value in self.comparisons)
            == self.declared_invariants
            and all(value for _name, value in self.comparisons)
        )

    def to_canonical_dict(self) -> dict:
        return {
            "comparisons": self.comparisons,
            "declared_invariants": self.declared_invariants,
            "inner_radius": self.inner_radius,
            "inner_snapshot_hash": self.inner_snapshot_hash,
            "outer_radius": self.outer_radius,
            "outer_snapshot_hash": self.outer_snapshot_hash,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class TubularToLineSynthesis:
    candidate_id: str
    samples: Tuple[StaticRadiusSample, ...]
    snapshots: Tuple[CheshireFiniteInvariantSnapshot, ...]
    step_certificates: Tuple[RadiusStepCertificate, ...]
    adjacent_certificates: Tuple[AdjacentInvariantCertificate, ...]
    declared_invariants: Tuple[str, ...]
    transcript_hash: str
    exactness: Exactness
    theorem_scope: str = STATIC_SYNTHESIS_SCOPE
    circuit_constructed: bool = False
    phase_equivalence_claimed: bool = False

    SCHEMA_ID = "mobility_toolkit.tubular_to_line_synthesis.v1"

    @property
    def finite_invariants_preserved(self) -> bool:
        return (
            bool(self.step_certificates)
            and all(item.verified for item in self.step_certificates)
            and all(item.verified for item in self.adjacent_certificates)
            and self.samples[-1].radius_lattice_steps == 0
            and not self.circuit_constructed
            and not self.phase_equivalence_claimed
        )

    def to_canonical_dict(self) -> dict:
        return {
            "adjacent_certificates": self.adjacent_certificates,
            "candidate_id": self.candidate_id,
            "circuit_constructed": self.circuit_constructed,
            "declared_invariants": self.declared_invariants,
            "exactness": self.exactness,
            "finite_invariants_preserved": self.finite_invariants_preserved,
            "phase_equivalence_claimed": self.phase_equivalence_claimed,
            "samples": self.samples,
            "schema": self.SCHEMA_ID,
            "snapshots": self.snapshots,
            "step_certificates": self.step_certificates,
            "theorem_scope": self.theorem_scope,
            "transcript_hash": self.transcript_hash,
        }


def _pairing_verified(report: Any) -> bool:
    algebra = report.defect_local_algebra
    pairing = algebra.logical_algebra.presentation_pairing_matrix.to_rows()
    modulus = algebra.logical_algebra.modulus
    rank = len(pairing)
    if any(len(row) != rank for row in pairing):
        return False
    return all(
        pairing[row][row] % modulus == 0
        and (pairing[row][column] + pairing[column][row]) % modulus == 0
        for row in range(rank)
        for column in range(rank)
    )


def _terms_phase_verified(terms: Sequence[Any]) -> bool:
    return all(
        term.operator.phase == 0 and not term.operator.scalar_obstruction
        for term in terms
    )


def _terms_commute(terms: Sequence[Any]) -> bool:
    operators = tuple(term.operator for term in terms)
    return all(
        left.commutes_with(right)
        for index, left in enumerate(operators)
        for right in operators[index:]
    )


def _snapshot(
    radius: int, analysis: CheshireStaticAnalysis
) -> CheshireFiniteInvariantSnapshot:
    reports = analysis.defect_reports
    return CheshireFiniteInvariantSnapshot(
        radius,
        tuple(len(report.tube.tube_site_ids) for report in reports),
        tuple(report.line_defect.topology.value for report in reports),
        analysis.local_analysis.logical_invariant_factors,
        analysis.fixed_sector_analysis.logical_invariant_factors,
        tuple(report.defect_local_algebra.invariant_factors for report in reports),
        tuple(
            canonical_hash(
                "cheshire-defect-local-pairing-v1",
                report.defect_local_algebra.logical_algebra,
            )
            for report in reports
        ),
        tuple(
            report.defect_local_algebra.radical_invariant_factors
            for report in reports
        ),
        tuple(report.charge_termination.terminates_on_defect for report in reports),
        tuple(report.magnetic_termination.terminates_on_defect for report in reports),
        (
            analysis.local_gsd_factor.numerator,
            analysis.local_gsd_factor.denominator,
        ),
        (
            analysis.fixed_sector_gsd_factor.numerator,
            analysis.fixed_sector_gsd_factor.denominator,
        ),
        canonical_hash("cheshire-local-hamiltonian-v1", analysis.local_terms),
        canonical_hash(
            "cheshire-fixed-sector-hamiltonian-v1", analysis.fixed_sector_terms
        ),
    )


def _step_certificate(
    sample: StaticRadiusSample,
    snapshot: CheshireFiniteInvariantSnapshot,
    expected_charge_termination: bool,
    expected_magnetic_termination: bool,
) -> RadiusStepCertificate:
    analysis = sample.analysis
    reports = analysis.defect_reports
    radius_matches = all(
        report.tube.radius_lattice_steps == sample.radius_lattice_steps
        and report.defect_local_algebra.window_site_ids
        == tuple(sorted(report.tube.tube_site_ids))
        for report in reports
    )
    charge_verified = bool(reports) and all(
        report.charge_termination.terminates_on_defect
        == expected_charge_termination
        for report in reports
    )
    magnetic_verified = bool(reports) and all(
        report.magnetic_termination.terminates_on_defect
        == expected_magnetic_termination
        and (
            expected_magnetic_termination
            or (
                report.magnetic_termination.no_solution_certificate is not None
                and report.magnetic_termination.no_solution_certificate.verified
            )
        )
        for report in reports
    )
    representation_verified = (
        radius_matches
        and analysis.pinned_elimination_certificate.verified
        and analysis.tubular_deleted_representation.certificate.verified
        and all(
            report.transformation_certificate.product_identity_verified
            and report.transformation_certificate.local_commutation_verified
            for report in reports
        )
    )
    return RadiusStepCertificate(
        sample.radius_lattice_steps,
        canonical_hash("cheshire-radius-analysis-v1", analysis),
        canonical_hash("cheshire-radius-snapshot-v1", snapshot),
        _terms_phase_verified(analysis.local_terms)
        and _terms_phase_verified(analysis.fixed_sector_terms),
        _terms_commute(analysis.local_terms)
        and _terms_commute(analysis.fixed_sector_terms),
        analysis.local_analysis.validation.valid
        and analysis.fixed_sector_analysis.validation.valid,
        bool(reports) and all(_pairing_verified(report) for report in reports),
        charge_verified,
        magnetic_verified,
        representation_verified,
    )


def _synthesis_transcript(
    candidate_id: str,
    declared_invariants: Tuple[str, ...],
    steps: Tuple[RadiusStepCertificate, ...],
    adjacent: Tuple[AdjacentInvariantCertificate, ...],
) -> str:
    return canonical_hash(
        "cheshire-tubular-to-line-transcript-v1",
        {
            "adjacent": adjacent,
            "candidate_id": candidate_id,
            "declared_invariants": declared_invariants,
            "steps": steps,
        },
    )


def _family_from_candidate(
    candidate: CondensationCandidate, radii: Sequence[int]
) -> FiniteTubeLineDefectFamily:
    values = _tuple_radii(radii)
    samples = tuple(StaticRadiusSample(radius, candidate.builder(radius)) for radius in values)
    return FiniteTubeLineDefectFamily(
        candidate.candidate_id,
        samples,
        candidate.declared_invariants,
        candidate.expected_charge_termination,
        candidate.expected_magnetic_termination,
        candidate.source_description + "; " + candidate.discovery_basis,
    )


def synthesize_tubular_to_line(
    candidate_or_family: Any,
    radii: Optional[Sequence[int]] = None,
) -> TubularToLineSynthesis:
    """Revalidate and compare one finite tubular-to-line family."""

    if isinstance(candidate_or_family, CondensationCandidate):
        if radii is None:
            raise ValueError("radii are required for a condensation candidate")
        family = _family_from_candidate(candidate_or_family, radii)
    elif isinstance(candidate_or_family, FiniteTubeLineDefectFamily):
        if radii is not None:
            raise ValueError("radii must not be repeated for an explicit finite family")
        family = candidate_or_family
    else:
        raise TypeError(
            "expected a CondensationCandidate or FiniteTubeLineDefectFamily"
        )

    snapshots = tuple(
        _snapshot(sample.radius_lattice_steps, sample.analysis)
        for sample in family.samples
    )
    steps = tuple(
        _step_certificate(
            sample,
            snapshot,
            family.expected_charge_termination,
            family.expected_magnetic_termination,
        )
        for sample, snapshot in zip(family.samples, snapshots)
    )
    adjacent = tuple(
        AdjacentInvariantCertificate(
            outer.radius_lattice_steps,
            inner.radius_lattice_steps,
            family.declared_invariants,
            tuple(
                (
                    name,
                    outer.declared_value(name) == inner.declared_value(name),
                )
                for name in family.declared_invariants
            ),
            canonical_hash("cheshire-radius-snapshot-v1", outer),
            canonical_hash("cheshire-radius-snapshot-v1", inner),
        )
        for outer, inner in zip(snapshots, snapshots[1:])
    )
    transcript = _synthesis_transcript(
        family.candidate_id, family.declared_invariants, steps, adjacent
    )
    result = TubularToLineSynthesis(
        family.candidate_id,
        family.samples,
        snapshots,
        steps,
        adjacent,
        family.declared_invariants,
        transcript,
        Exactness.BOUNDED_EXACT,
    )
    if not all(step.verified for step in steps):
        raise ValueError("one or more finite Cheshire radius-step certificates failed")
    return result


def verify_tubular_to_line_synthesis(result: TubularToLineSynthesis) -> bool:
    """Semantically replay a synthesis, detecting hashes resealed after tampering."""

    if not isinstance(result, TubularToLineSynthesis):
        return False
    try:
        family = FiniteTubeLineDefectFamily(
            result.candidate_id,
            result.samples,
            result.declared_invariants,
            result.step_certificates[0].charge_termination_verified
            and all(snapshot.charge_termination for snapshot in result.snapshots),
            not (
                result.step_certificates[0].magnetic_termination_verified
                and all(not value for snapshot in result.snapshots for value in snapshot.magnetic_termination)
            ),
        )
    except (IndexError, TypeError, ValueError):
        return False
    expected_charge = all(
        value for snapshot in result.snapshots for value in snapshot.charge_termination
    )
    expected_magnetic = all(
        value for snapshot in result.snapshots for value in snapshot.magnetic_termination
    )
    family = replace(
        family,
        expected_charge_termination=expected_charge,
        expected_magnetic_termination=expected_magnetic,
    )
    try:
        replay = synthesize_tubular_to_line(family)
    except (ArithmeticError, TypeError, ValueError):
        return False
    return (
        replay.snapshots == result.snapshots
        and replay.step_certificates == result.step_certificates
        and replay.adjacent_certificates == result.adjacent_certificates
        and replay.transcript_hash == result.transcript_hash
        and result.finite_invariants_preserved
        and result.exactness == Exactness.BOUNDED_EXACT
        and not result.circuit_constructed
        and not result.phase_equivalence_claimed
    )


@dataclass(frozen=True)
class CheshireSpeciesSearchDomain:
    candidate_ids: Tuple[str, ...]
    radii: Tuple[int, ...]
    candidate_list_complete_by_declaration: bool

    SCHEMA_ID = "mobility_toolkit.cheshire_species_search_domain.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidate_ids": self.candidate_ids,
            "candidate_list_complete_by_declaration": self.candidate_list_complete_by_declaration,
            "radii": self.radii,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class CheshireSpeciesDecision:
    candidate_id: str
    accepted: bool
    synthesis_hash: str
    rejection_reason: str = ""

    SCHEMA_ID = "mobility_toolkit.cheshire_species_decision.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "candidate_id": self.candidate_id,
            "rejection_reason": self.rejection_reason,
            "schema": self.SCHEMA_ID,
            "synthesis_hash": self.synthesis_hash,
        }


@dataclass(frozen=True)
class CheshireSpeciesSearchCertificate:
    domain: CheshireSpeciesSearchDomain
    decisions: Tuple[CheshireSpeciesDecision, ...]
    transcript_hash: str
    exactness: Exactness
    theorem_scope: str = STATIC_SYNTHESIS_SCOPE

    SCHEMA_ID = "mobility_toolkit.cheshire_species_search_certificate.v1"

    @property
    def bounded_complete(self) -> bool:
        return (
            self.domain.candidate_list_complete_by_declaration
            and tuple(decision.candidate_id for decision in self.decisions)
            == self.domain.candidate_ids
            and self.exactness == Exactness.BOUNDED_EXACT
            and self.transcript_hash
            == canonical_hash(
                "cheshire-species-search-transcript-v1",
                {"decisions": self.decisions, "domain": self.domain},
            )
        )

    def to_canonical_dict(self) -> dict:
        return {
            "bounded_complete": self.bounded_complete,
            "decisions": self.decisions,
            "domain": self.domain,
            "exactness": self.exactness,
            "schema": self.SCHEMA_ID,
            "theorem_scope": self.theorem_scope,
            "transcript_hash": self.transcript_hash,
        }


@dataclass(frozen=True)
class CheshireSpeciesEnumeration:
    syntheses: Tuple[TubularToLineSynthesis, ...]
    certificate: CheshireSpeciesSearchCertificate

    SCHEMA_ID = "mobility_toolkit.cheshire_species_enumeration.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "schema": self.SCHEMA_ID,
            "syntheses": self.syntheses,
        }


def enumerate_cheshire_species(
    candidates: Sequence[CondensationCandidate],
    radii: Sequence[int],
) -> CheshireSpeciesEnumeration:
    """Exhaust a declared finite candidate list, not an implicit larger space."""

    values = _tuple_radii(radii)
    candidates = tuple(candidates)
    ids = tuple(candidate.candidate_id for candidate in candidates)
    if not ids:
        raise ValueError("at least one Cheshire candidate is required")
    if len(set(ids)) != len(ids):
        raise ValueError("Cheshire candidate IDs must be unique")
    domain = CheshireSpeciesSearchDomain(ids, values, True)
    decisions = []
    syntheses = []
    for candidate in candidates:
        try:
            synthesis = synthesize_tubular_to_line(candidate, values)
        except (ArithmeticError, TypeError, ValueError) as exc:
            decisions.append(
                CheshireSpeciesDecision(candidate.candidate_id, False, "", str(exc))
            )
        else:
            syntheses.append(synthesis)
            decisions.append(
                CheshireSpeciesDecision(
                    candidate.candidate_id,
                    synthesis.finite_invariants_preserved,
                    canonical_hash("cheshire-species-synthesis-v1", synthesis),
                )
            )
    decisions_tuple = tuple(decisions)
    transcript = canonical_hash(
        "cheshire-species-search-transcript-v1",
        {"decisions": decisions_tuple, "domain": domain},
    )
    certificate = CheshireSpeciesSearchCertificate(
        domain, decisions_tuple, transcript, Exactness.BOUNDED_EXACT
    )
    return CheshireSpeciesEnumeration(tuple(syntheses), certificate)


def verify_cheshire_species_enumeration(
    result: CheshireSpeciesEnumeration,
) -> bool:
    if not isinstance(result, CheshireSpeciesEnumeration):
        return False
    if not result.certificate.bounded_complete:
        return False
    by_id = {synthesis.candidate_id: synthesis for synthesis in result.syntheses}
    for decision in result.certificate.decisions:
        if decision.accepted:
            synthesis = by_id.get(decision.candidate_id)
            if (
                synthesis is None
                or not verify_tubular_to_line_synthesis(synthesis)
                or decision.synthesis_hash
                != canonical_hash("cheshire-species-synthesis-v1", synthesis)
            ):
                return False
        elif decision.candidate_id in by_id:
            return False
    return True


def _normalize_line(value: Any) -> LineDefect:
    if isinstance(value, LineDefect):
        return value
    if isinstance(value, (OpenSegment, ClosedLoop)):
        return value.line
    raise TypeError("reference defects must be LineDefect, OpenSegment, or ClosedLoop")


def toric_cheshire_condensation_candidate(
    complex_: CubicalComplex,
    defects: Sequence[Any],
    backend: FiniteIntegerBackend,
    candidate_id: Optional[str] = None,
) -> CondensationCandidate:
    """Return the source-locked 3+1D Z2 toric open/closed Cheshire candidate."""

    lines = tuple(_normalize_line(defect) for defect in defects)
    if not lines:
        raise ValueError("at least one toric Cheshire line is required")
    label = candidate_id or "toric-z2-" + "-".join(
        line.topology.value for line in lines
    )
    cache: Dict[Tuple[Tuple[str, ...], ...], CheshireStaticAnalysis] = {}

    def builder(radius: int) -> CheshireStaticAnalysis:
        tubes = tuple(TubularDefect.around_line(complex_, line, radius) for line in lines)
        signature = tuple(tube.tube_site_ids for tube in tubes)
        cached = cache.get(signature)
        if cached is None:
            cached = analyze_toric_cheshire(
                complex_, lines, backend, tube_radius_lattice_steps=radius
            )
            cache[signature] = cached
            return cached
        reports = tuple(
            replace(report, tube=tube)
            for report, tube in zip(cached.defect_reports, tubes)
        )
        return replace(cached, defect_reports=reports)

    return CondensationCandidate(
        label,
        builder,
        source_description=(
            "Tantivasadakarn--Chen arXiv:2307.03180 Eq. (6)--(8), explicit "
            "finite 3+1D Z2 toric open/closed static construction"
        ),
    )


__all__ = [
    "AdjacentInvariantCertificate",
    "CheshireFiniteInvariantSnapshot",
    "CheshireSpeciesDecision",
    "CheshireSpeciesEnumeration",
    "CheshireSpeciesSearchCertificate",
    "CheshireSpeciesSearchDomain",
    "CondensationCandidate",
    "DEFAULT_DECLARED_INVARIANTS",
    "FiniteTubeLineDefectFamily",
    "RadiusStepCertificate",
    "STATIC_SYNTHESIS_SCOPE",
    "StaticRadiusSample",
    "TubularToLineSynthesis",
    "enumerate_cheshire_species",
    "synthesize_tubular_to_line",
    "toric_cheshire_condensation_candidate",
    "verify_cheshire_species_enumeration",
    "verify_tubular_to_line_synthesis",
]
