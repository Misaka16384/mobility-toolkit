"""Bounded-periodic (E2) enumeration over a precompiled boundary algebra.

This module deliberately separates three statements:

* E1 exhausts isotropic subgroups of one finite paired algebra.
* E2 filters those subgroups by explicitly certified tangent translations.
* The supplied finite algebra is a realization of one declared
  :class:`~mobility_toolkit.boundary_halfspace.search.BoundedPeriodicSearchDomain`.

Only the conjunction of all three statements yields ``bounded_exact``.  The
current implementation supports the no-ancilla
``translation_compatible_submodules`` family.  It does not manufacture
ancillary boundary degrees of freedom or local Hamiltonian completions.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional, Sequence, Tuple

from mobility_toolkit.boundary.algebra import (
    FiniteBoundaryAlgebra,
    support_window_from_sites,
)
from mobility_toolkit.boundary.enumeration.finite import (
    E1CompletenessCertificate,
    E1EnumerationCheckpoint,
    E1SubgroupCandidate,
    EnumerationBudget,
    enumerate_e1_subgroups,
    paired_boundary_presentation,
    replay_e1_output_transcript,
)
from mobility_toolkit.boundary_halfspace.search import BoundedPeriodicSearchDomain
from mobility_toolkit.core import Exactness, SparseIntMatrix
from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FiniteGroupHomomorphism,
    FiniteIntegerBackend,
    NotInLattice,
)


OutputTranscriptEntry = Tuple[str, str]


def _matrix_from_columns(
    columns: Sequence[Sequence[int]], nrows: int
) -> SparseIntMatrix:
    values = tuple(tuple(column) for column in columns)
    return SparseIntMatrix(
        nrows,
        len(values),
        tuple(
            (row, column, value)
            for column, vector in enumerate(values)
            for row, value in enumerate(vector)
            if value
        ),
    )


def _matrix_vector(
    matrix: SparseIntMatrix, vector: Sequence[int]
) -> Tuple[int, ...]:
    values = tuple(vector)
    if matrix.ncols != len(values):
        raise ValueError("translation action and candidate vector ranks differ")
    rows = matrix.to_rows()
    return tuple(
        sum(row[column] * values[column] for column in range(matrix.ncols))
        for row in rows
    )


def _divisors(value: int) -> Tuple[int, ...]:
    return tuple(item for item in range(1, value + 1) if value % item == 0)


def bounded_periodic_search_extent(
    domain: BoundedPeriodicSearchDomain,
) -> Tuple[Tuple[str, int], ...]:
    """Return the exact finite-window metadata required by an E2 realization."""

    values = [
        ("completion_depth", domain.completion_depth),
        ("max_inward_depth", domain.support_bound.max_inward_depth),
        ("max_sites_per_term", domain.support_bound.max_sites_per_term),
    ]
    values.extend(
        (f"tangent_radius_{axis}", radius)
        for axis, radius in enumerate(domain.support_bound.tangent_radii)
    )
    values.extend(
        (f"unit_cell_period_{axis}", period)
        for axis, period in enumerate(domain.unit_cell_period)
    )
    return tuple(sorted(values))


@dataclass(frozen=True)
class E2TangentAction:
    """One microscopic tangent translation on the finite quotient."""

    name: str
    quotient_action: FiniteGroupHomomorphism

    SCHEMA_ID = "mobility_toolkit.e2_tangent_action.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("E2 tangent action name must be nonempty")

    def to_canonical_dict(self) -> dict:
        return {
            "name": self.name,
            "quotient_action": self.quotient_action,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True, order=True)
class E2SiteCoordinate:
    """An explicit site position in the adapted tangent/depth coordinates."""

    site_id: str
    tangent: Tuple[int, ...]
    depth: int

    SCHEMA_ID = "mobility_toolkit.e2_site_coordinate.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.site_id, str) or not self.site_id:
            raise ValueError("E2 site coordinate requires a nonempty site_id")
        tangent = tuple(self.tangent)
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in tangent
        ):
            raise TypeError("E2 tangent site coordinates must be integers")
        if (
            isinstance(self.depth, bool)
            or not isinstance(self.depth, int)
            or self.depth < 0
        ):
            raise ValueError("E2 site depth must be a nonnegative integer")
        object.__setattr__(self, "tangent", tangent)

    def to_canonical_dict(self) -> dict:
        return {
            "depth": self.depth,
            "schema": self.SCHEMA_ID,
            "site_id": self.site_id,
            "tangent": self.tangent,
        }


@dataclass(frozen=True)
class BoundedPeriodicAlgebraRealization:
    """Machine-checkable binding between a finite algebra and an E2 domain."""

    domain_hash: str
    algebra_input_hash: str
    finite_window_id: str
    finite_window_site_ids: Tuple[str, ...]
    finite_window_search_extent: Tuple[Tuple[str, int], ...]
    site_coordinates: Tuple[E2SiteCoordinate, ...]
    support_compiler: str
    support_compiler_version: str
    support_image_hashes: Tuple[Tuple[Tuple[str, ...], str], ...]
    translated_support_image_hashes: Tuple[str, ...]
    support_coverage_hash: str
    action_names: Tuple[str, ...]
    action_hashes: Tuple[str, ...]
    automorphisms_verified: bool
    pairing_preservation_verified: bool
    translation_commutation_verified: bool
    support_domain_binding_verified: bool
    coefficient_domain_verified: bool

    SCHEMA_ID = "mobility_toolkit.e2_algebra_realization.v1"

    @property
    def verified(self) -> bool:
        return (
            self.automorphisms_verified
            and self.pairing_preservation_verified
            and self.translation_commutation_verified
            and self.support_domain_binding_verified
            and self.coefficient_domain_verified
        )

    def to_canonical_dict(self) -> dict:
        return {
            "action_hashes": self.action_hashes,
            "action_names": self.action_names,
            "algebra_input_hash": self.algebra_input_hash,
            "automorphisms_verified": self.automorphisms_verified,
            "coefficient_domain_verified": self.coefficient_domain_verified,
            "domain_hash": self.domain_hash,
            "finite_window_id": self.finite_window_id,
            "finite_window_search_extent": self.finite_window_search_extent,
            "finite_window_site_ids": self.finite_window_site_ids,
            "pairing_preservation_verified": self.pairing_preservation_verified,
            "schema": self.SCHEMA_ID,
            "site_coordinates": self.site_coordinates,
            "support_compiler": self.support_compiler,
            "support_compiler_version": self.support_compiler_version,
            "support_coverage_hash": self.support_coverage_hash,
            "support_domain_binding_verified":
                self.support_domain_binding_verified,
            "support_image_hashes": self.support_image_hashes,
            "translated_support_image_hashes":
                self.translated_support_image_hashes,
            "translation_commutation_verified":
                self.translation_commutation_verified,
            "verified": self.verified,
        }


def _maps_equal_on_quotient(
    left: SparseIntMatrix,
    right: SparseIntMatrix,
    group: FiniteAbelianGroup,
    backend: FiniteIntegerBackend,
) -> bool:
    difference = SparseIntMatrix(
        left.nrows,
        left.ncols,
        tuple(left.entries) + tuple(right.negate().entries),
    )
    try:
        backend.solve_full_lattice(group.relation_lattice_basis, difference)
    except NotInLattice:
        return False
    return True


def _normalized_site_coordinates(
    algebra: FiniteBoundaryAlgebra,
    domain: BoundedPeriodicSearchDomain,
    site_coordinates: Sequence[E2SiteCoordinate],
) -> Tuple[E2SiteCoordinate, ...]:
    coordinates = tuple(sorted(tuple(site_coordinates)))
    if len({coordinate.site_id for coordinate in coordinates}) != len(coordinates):
        raise ValueError("E2 realization repeats a site coordinate")
    if tuple(coordinate.site_id for coordinate in coordinates) != tuple(
        sorted(algebra.window.site_ids)
    ):
        raise ValueError(
            "E2 site coordinates must cover exactly the finite support-window sites"
        )
    tangent_rank = domain.half_space.normal.dimension - 1
    if any(len(coordinate.tangent) != tangent_rank for coordinate in coordinates):
        raise ValueError("E2 site-coordinate tangent rank mismatch")
    return coordinates


def _eligible_support_sites(
    coordinates: Sequence[E2SiteCoordinate],
    domain: BoundedPeriodicSearchDomain,
) -> Tuple[str, ...]:
    return tuple(
        coordinate.site_id
        for coordinate in coordinates
        if coordinate.depth <= domain.support_bound.max_inward_depth
        and all(
            abs(value) <= radius
            for value, radius in zip(
                coordinate.tangent,
                domain.support_bound.tangent_radii,
            )
        )
    )


def _compile_anchor_support_images(
    algebra: FiniteBoundaryAlgebra,
    domain: BoundedPeriodicSearchDomain,
    coordinates: Sequence[E2SiteCoordinate],
    backend: FiniteIntegerBackend,
):
    """Compile every allowed support subset to its exact quotient image."""

    paired = paired_boundary_presentation(algebra, backend)
    quotient_group = paired.group
    eligible = _eligible_support_sites(coordinates, domain)
    max_sites = min(domain.support_bound.max_sites_per_term, len(eligible))
    images = []
    images.append(((), quotient_group.trivial_subgroup(backend)))
    for size in range(1, max_sites + 1):
        for site_subset in itertools.combinations(eligible, size):
            support_window = support_window_from_sites(
                algebra.analysis,
                site_subset,
                backend,
                window_id="e2-support:" + ",".join(site_subset),
            )
            supported_centralizer = algebra.local_centralizer.intersection(
                support_window.paulis, backend
            )
            numerator_coordinates = backend.solve_full_lattice(
                algebra.local_centralizer.preimage_lattice_basis,
                supported_centralizer.preimage_lattice_basis,
            )
            quotient_image = quotient_group.subgroup(
                numerator_coordinates, backend
            )
            images.append((tuple(site_subset), quotient_image))
    return tuple(images)


def _translate_support_image(
    subgroup,
    action: E2TangentAction,
    group: FiniteAbelianGroup,
    backend: FiniteIntegerBackend,
):
    mapped_basis = action.quotient_action.lift_matrix.matmul(
        subgroup.preimage_lattice_basis
    )
    return group.subgroup(mapped_basis, backend)


def _compile_translated_support_images(
    anchor_images,
    actions: Sequence[E2TangentAction],
    group: FiniteAbelianGroup,
    backend: FiniteIntegerBackend,
):
    """BFS the complete finite orbit of every anchor support image."""

    seen = {}
    pending = []
    for _, subgroup in anchor_images:
        subgroup_hash = canonical_hash("e2-translated-support-image-v1", subgroup)
        if subgroup_hash not in seen:
            seen[subgroup_hash] = subgroup
            pending.append(subgroup)
    while pending:
        subgroup = pending.pop(0)
        for action in actions:
            translated = _translate_support_image(
                subgroup, action, group, backend
            )
            translated_hash = canonical_hash(
                "e2-translated-support-image-v1", translated
            )
            if translated_hash not in seen:
                seen[translated_hash] = translated
                pending.append(translated)
    return tuple(seen[key] for key in sorted(seen))


def bind_bounded_periodic_algebra(
    algebra: FiniteBoundaryAlgebra,
    domain: BoundedPeriodicSearchDomain,
    actions: Sequence[E2TangentAction],
    backend: FiniteIntegerBackend,
    site_coordinates: Sequence[E2SiteCoordinate],
) -> BoundedPeriodicAlgebraRealization:
    """Verify and bind a precompiled finite algebra to an E2 search domain."""

    values = tuple(actions)
    coordinates = _normalized_site_coordinates(
        algebra, domain, site_coordinates
    )
    tangent_rank = domain.half_space.normal.dimension - 1
    if len(values) != tangent_rank:
        raise ValueError("E2 tangent action count must equal tangent-lattice rank")
    names = tuple(action.name for action in values)
    if len(set(names)) != len(names):
        raise ValueError("E2 tangent action names must be unique")
    expected_extent = bounded_periodic_search_extent(domain)
    if algebra.window.search_extent != expected_extent:
        raise ValueError(
            "finite boundary algebra search_extent does not bind the declared "
            "E2 support, completion, and period bounds"
        )
    local_factors = tuple(
        system.invariant_factors
        for system in algebra.analysis.module.local_systems
    )
    allowed_domains = {"finite_fga"}
    if (
        local_factors
        and all(len(factors) == 1 for factors in local_factors)
        and len({factors[0] for factors in local_factors}) == 1
    ):
        allowed_domains.add(
            f"finite_fga:uniform_z{local_factors[0][0]}"
        )
    else:
        allowed_domains.add("finite_fga:mixed")
    if domain.coefficient_domain not in allowed_domains:
        raise ValueError(
            "E2 coefficient_domain does not match the precompiled Pauli module"
        )

    paired = paired_boundary_presentation(algebra, backend)
    group = paired.group
    for action in values:
        homomorphism = action.quotient_action
        if homomorphism.source != group or homomorphism.target != group:
            raise ValueError("E2 tangent action belongs to a different paired group")
        if homomorphism.kernel(backend).order(backend) != 1:
            raise ValueError(f"E2 tangent action {action.name!r} is not injective")
        if homomorphism.image(backend).order(backend) != group.order(backend):
            raise ValueError(f"E2 tangent action {action.name!r} is not surjective")
        pulled_back = (
            homomorphism.lift_matrix.transpose()
            .matmul(paired.pairing_matrix)
            .matmul(homomorphism.lift_matrix)
        )
        difference = SparseIntMatrix(
            paired.pairing_matrix.nrows,
            paired.pairing_matrix.ncols,
            tuple(pulled_back.entries)
            + tuple(paired.pairing_matrix.negate().entries),
        )
        if any(value % paired.modulus for _, _, value in difference.entries):
            raise ValueError(
                f"E2 tangent action {action.name!r} does not preserve the pairing"
            )

    for left_index, left in enumerate(values):
        for right in values[left_index + 1:]:
            left_right = left.quotient_action.lift_matrix.matmul(
                right.quotient_action.lift_matrix
            )
            right_left = right.quotient_action.lift_matrix.matmul(
                left.quotient_action.lift_matrix
            )
            if not _maps_equal_on_quotient(
                left_right, right_left, group, backend
            ):
                raise ValueError(
                    "E2 tangent actions do not define commuting lattice translations"
                )

    algebra_input_hash = canonical_hash(
        "e1-finite-paired-algebra-v1",
        {"paired": paired, "window": algebra.window},
    )
    anchor_support_images = _compile_anchor_support_images(
        algebra, domain, coordinates, backend
    )
    support_image_hashes = tuple(
        (
            site_subset,
            canonical_hash("e2-support-quotient-image-v1", subgroup),
        )
        for site_subset, subgroup in anchor_support_images
    )
    translated_support_images = _compile_translated_support_images(
        anchor_support_images, values, group, backend
    )
    translated_support_image_hashes = tuple(
        canonical_hash("e2-translated-support-image-v1", subgroup)
        for subgroup in translated_support_images
    )
    support_coverage_hash = canonical_hash(
        "e2-support-coverage-v1",
        {
            "algebra_input_hash": algebra_input_hash,
            "domain": domain,
            "site_coordinates": coordinates,
            "support_compiler": "finite-fga-support-image-compiler",
            "support_compiler_version": "1",
            "support_image_hashes": support_image_hashes,
            "translated_support_image_hashes":
                translated_support_image_hashes,
        },
    )
    return BoundedPeriodicAlgebraRealization(
        domain_hash=canonical_hash("e2-search-domain-v1", domain),
        algebra_input_hash=algebra_input_hash,
        finite_window_id=algebra.window.window_id,
        finite_window_site_ids=algebra.window.site_ids,
        finite_window_search_extent=algebra.window.search_extent,
        site_coordinates=coordinates,
        support_compiler="finite-fga-support-image-compiler",
        support_compiler_version="1",
        support_image_hashes=support_image_hashes,
        translated_support_image_hashes=translated_support_image_hashes,
        support_coverage_hash=support_coverage_hash,
        action_names=names,
        action_hashes=tuple(
            canonical_hash("e2-tangent-action-v1", action)
            for action in values
        ),
        automorphisms_verified=True,
        pairing_preservation_verified=True,
        translation_commutation_verified=True,
        support_domain_binding_verified=True,
        coefficient_domain_verified=True,
    )


@dataclass(frozen=True)
class E2TranslationInvariantCandidate:
    e1_candidate: E1SubgroupCandidate
    declared_period: Tuple[int, ...]
    fundamental_period: Tuple[int, ...]
    action_names: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.e2_translation_invariant_candidate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "action_names": self.action_names,
            "declared_period": self.declared_period,
            "e1_candidate": self.e1_candidate,
            "fundamental_period": self.fundamental_period,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class E2CandidateDecision:
    """Replayable semantic decision for one complete E1 candidate."""

    e1_candidate: E1SubgroupCandidate
    support_generable: bool
    fundamental_period: Tuple[Optional[int], ...]
    accepted: bool

    SCHEMA_ID = "mobility_toolkit.e2_candidate_decision.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "e1_candidate": self.e1_candidate,
            "fundamental_period": self.fundamental_period,
            "schema": self.SCHEMA_ID,
            "support_generable": self.support_generable,
        }


class E2Termination(str, Enum):
    EXHAUSTED = "exhausted"
    RESOURCE_LIMIT = "resource_limit"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class E2CompletenessCertificate:
    domain: BoundedPeriodicSearchDomain
    realization: BoundedPeriodicAlgebraRealization
    e1_certificate: Optional[E1CompletenessCertificate]
    termination: E2Termination
    processed_e1_candidates: int
    accepted_candidates: int
    candidate_transcript_hash: str
    output_transcript_hash: str
    page_work_units: int
    total_work_units: int
    unsupported_reasons: Tuple[str, ...]
    exactness: Exactness
    verification: Tuple[str, ...]
    theorem_scope: str = (
        "complete only for isotropic subgroups of the supplied finite paired "
        "algebra generated by local seeds drawn from the complete finite "
        "microscopic-translation orbit of the explicit anchor support envelope, "
        "and independently invariant under the declared period translations; "
        "it is neither E3 symbolic completeness nor a thermodynamic boundary "
        "classification theorem"
    )

    SCHEMA_ID = "mobility_toolkit.e2_completeness_certificate.v1"

    @property
    def bounded_complete(self) -> bool:
        return (
            self.termination == E2Termination.EXHAUSTED
            and self.exactness == Exactness.BOUNDED_EXACT
        )

    def to_canonical_dict(self) -> dict:
        return {
            "accepted_candidates": self.accepted_candidates,
            "bounded_complete": self.bounded_complete,
            "candidate_transcript_hash": self.candidate_transcript_hash,
            "domain": self.domain,
            "e1_certificate": self.e1_certificate,
            "exactness": self.exactness,
            "output_transcript_hash": self.output_transcript_hash,
            "page_work_units": self.page_work_units,
            "processed_e1_candidates": self.processed_e1_candidates,
            "realization": self.realization,
            "schema": self.SCHEMA_ID,
            "termination": self.termination,
            "theorem_scope": self.theorem_scope,
            "total_work_units": self.total_work_units,
            "unsupported_reasons": self.unsupported_reasons,
            "verification": self.verification,
        }


@dataclass(frozen=True)
class E2EnumerationCheckpoint:
    domain_hash: str
    realization_hash: str
    e1_checkpoint: Optional[E1EnumerationCheckpoint] = None
    e1_certificate: Optional[E1CompletenessCertificate] = None
    e1_complete: bool = False
    pending_e1_candidates: Tuple[E1SubgroupCandidate, ...] = ()
    candidate_transcript: Tuple[E2CandidateDecision, ...] = ()
    candidate_transcript_hash: str = ""
    accepted_output_prefix: Tuple[OutputTranscriptEntry, ...] = ()
    output_transcript_hash: str = ""
    total_work_units: int = 0
    checkpoint_hash: str = ""

    SCHEMA_ID = "mobility_toolkit.e2_enumeration_checkpoint.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "accepted_output_prefix": self.accepted_output_prefix,
            "candidate_transcript": self.candidate_transcript,
            "candidate_transcript_hash": self.candidate_transcript_hash,
            "checkpoint_hash": self.checkpoint_hash,
            "domain_hash": self.domain_hash,
            "e1_certificate": self.e1_certificate,
            "e1_checkpoint": self.e1_checkpoint,
            "e1_complete": self.e1_complete,
            "output_transcript_hash": self.output_transcript_hash,
            "pending_e1_candidates": self.pending_e1_candidates,
            "realization_hash": self.realization_hash,
            "schema": self.SCHEMA_ID,
            "total_work_units": self.total_work_units,
        }


@dataclass(frozen=True)
class E2EnumerationPage:
    candidates: Tuple[E2TranslationInvariantCandidate, ...]
    checkpoint: Optional[E2EnumerationCheckpoint]
    certificate: E2CompletenessCertificate

    SCHEMA_ID = "mobility_toolkit.e2_enumeration_page.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidates": self.candidates,
            "certificate": self.certificate,
            "checkpoint": self.checkpoint,
            "schema": self.SCHEMA_ID,
        }


def _candidate_hash(candidate: E1SubgroupCandidate) -> str:
    return canonical_hash("e2-input-e1-candidate-v1", candidate)


def _candidate_genesis(domain_hash: str, realization_hash: str) -> str:
    return canonical_hash(
        "e2-candidate-transcript-genesis-v1",
        {"domain_hash": domain_hash, "realization_hash": realization_hash},
    )


def _candidate_step(
    previous_hash: str,
    index: int,
    entry: E2CandidateDecision,
) -> str:
    return canonical_hash(
        "e2-candidate-transcript-step-v1",
        {
            "entry": entry,
            "index": index,
            "previous_hash": previous_hash,
        },
    )


def _replay_candidate_transcript(
    domain_hash: str,
    realization_hash: str,
    transcript: Sequence[E2CandidateDecision],
) -> str:
    digest = _candidate_genesis(domain_hash, realization_hash)
    for index, entry in enumerate(transcript):
        digest = _candidate_step(digest, index, entry)
    return digest


def _output_genesis(domain_hash: str, realization_hash: str) -> str:
    return canonical_hash(
        "e2-output-transcript-genesis-v1",
        {"domain_hash": domain_hash, "realization_hash": realization_hash},
    )


def _output_step(
    previous_hash: str, index: int, entry: OutputTranscriptEntry
) -> str:
    return canonical_hash(
        "e2-output-transcript-step-v1",
        {
            "entry": entry,
            "index": index,
            "previous_hash": previous_hash,
        },
    )


def _replay_output(
    domain_hash: str,
    realization_hash: str,
    prefix: Sequence[OutputTranscriptEntry],
) -> str:
    digest = _output_genesis(domain_hash, realization_hash)
    for index, entry in enumerate(prefix):
        digest = _output_step(digest, index, entry)
    return digest


def _checkpoint_payload(checkpoint: E2EnumerationCheckpoint) -> dict:
    return {
        "accepted_output_prefix": checkpoint.accepted_output_prefix,
        "candidate_transcript": checkpoint.candidate_transcript,
        "candidate_transcript_hash": checkpoint.candidate_transcript_hash,
        "domain_hash": checkpoint.domain_hash,
        "e1_certificate": checkpoint.e1_certificate,
        "e1_checkpoint": checkpoint.e1_checkpoint,
        "e1_complete": checkpoint.e1_complete,
        "output_transcript_hash": checkpoint.output_transcript_hash,
        "pending_e1_candidates": checkpoint.pending_e1_candidates,
        "realization_hash": checkpoint.realization_hash,
        "total_work_units": checkpoint.total_work_units,
    }


def _seal_checkpoint(
    checkpoint: E2EnumerationCheckpoint,
) -> E2EnumerationCheckpoint:
    unsealed = replace(checkpoint, checkpoint_hash="")
    return replace(
        unsealed,
        checkpoint_hash=canonical_hash(
            "e2-enumeration-checkpoint-state-v1",
            _checkpoint_payload(unsealed),
        ),
    )


def _validate_checkpoint(
    checkpoint: E2EnumerationCheckpoint,
    realization: BoundedPeriodicAlgebraRealization,
    domain: BoundedPeriodicSearchDomain,
    actions: Sequence[E2TangentAction],
    group: FiniteAbelianGroup,
    support_images,
    backend: FiniteIntegerBackend,
) -> None:
    realization_hash = canonical_hash("e2-algebra-realization-v1", realization)
    if checkpoint.domain_hash != realization.domain_hash:
        raise ValueError("E2 checkpoint belongs to a different search domain")
    if checkpoint.realization_hash != realization_hash:
        raise ValueError("E2 checkpoint belongs to a different algebra realization")
    if not checkpoint.checkpoint_hash:
        raise ValueError("E2 checkpoint is unsealed")
    if _seal_checkpoint(checkpoint).checkpoint_hash != checkpoint.checkpoint_hash:
        raise ValueError("E2 checkpoint state hash is invalid")
    if (
        isinstance(checkpoint.total_work_units, bool)
        or not isinstance(checkpoint.total_work_units, int)
        or checkpoint.total_work_units < 0
    ):
        raise ValueError("E2 checkpoint has invalid resource accounting")
    if checkpoint.e1_complete:
        if checkpoint.e1_checkpoint is not None:
            raise ValueError("completed E1 state still has a checkpoint")
        if (
            checkpoint.e1_certificate is None
            or not checkpoint.e1_certificate.certified_complete
            or checkpoint.e1_certificate.exactness
            != Exactness.CERTIFIED_EXACT
        ):
            raise ValueError("completed E1 state lacks a complete certificate")
    if checkpoint.e1_certificate is not None:
        if (
            checkpoint.e1_certificate.domain.algebra_input_hash
            != realization.algebra_input_hash
        ):
            raise ValueError("E2 checkpoint contains a foreign E1 certificate")
        emitted = checkpoint.e1_certificate.output_prefix_length
        if (
            len(checkpoint.candidate_transcript)
            + len(checkpoint.pending_e1_candidates)
            != emitted
        ):
            raise ValueError(
                "E2 checkpoint does not account for every emitted E1 candidate"
            )
        issued_e1_candidates = tuple(
            decision.e1_candidate
            for decision in checkpoint.candidate_transcript
        ) + checkpoint.pending_e1_candidates
        replayed_e1_output_hash = replay_e1_output_transcript(
            realization.algebra_input_hash,
            checkpoint.e1_certificate.candidate_transcript_hash,
            issued_e1_candidates,
        )
        if (
            replayed_e1_output_hash
            != checkpoint.e1_certificate.output_transcript_hash
        ):
            raise ValueError(
                "E2 checkpoint candidates do not replay the certified E1 output transcript"
            )
    if any(
        candidate.algebra_input_hash != realization.algebra_input_hash
        for candidate in checkpoint.pending_e1_candidates
    ):
        raise ValueError("E2 checkpoint contains a foreign E1 candidate")
    expected_candidate_hash = _replay_candidate_transcript(
        checkpoint.domain_hash,
        checkpoint.realization_hash,
        checkpoint.candidate_transcript,
    )
    if checkpoint.candidate_transcript_hash != expected_candidate_hash:
        raise ValueError("E2 checkpoint candidate transcript hash is invalid")
    transcript_sources = tuple(
        _candidate_hash(decision.e1_candidate)
        for decision in checkpoint.candidate_transcript
    )
    if (
        any(not source_hash for source_hash in transcript_sources)
        or len(set(transcript_sources)) != len(transcript_sources)
    ):
        raise ValueError("E2 checkpoint repeats or omits an E1 candidate hash")
    for decision in checkpoint.candidate_transcript:
        expected_decision = _evaluate_candidate(
            decision.e1_candidate,
            group,
            actions,
            domain,
            support_images,
            backend,
        )
        if decision != expected_decision:
            raise ValueError(
                "E2 checkpoint contains a semantically invalid candidate decision"
            )
    accepted_decisions = tuple(
        decision
        for decision in checkpoint.candidate_transcript
        if decision.accepted
    )
    accepted_hashes = tuple(
        _candidate_hash(decision.e1_candidate)
        for decision in accepted_decisions
    )
    if tuple(entry[0] for entry in checkpoint.accepted_output_prefix) != accepted_hashes:
        raise ValueError("E2 checkpoint output prefix disagrees with acceptance")
    expected_result_hashes = tuple(
        canonical_hash(
            "e2-candidate-output-v1",
            _result_from_decision(decision, domain, realization.action_names),
        )
        for decision in accepted_decisions
    )
    if tuple(entry[1] for entry in checkpoint.accepted_output_prefix) != (
        expected_result_hashes
    ):
        raise ValueError("E2 checkpoint output transcript changed a result")
    expected_output_hash = _replay_output(
        checkpoint.domain_hash,
        checkpoint.realization_hash,
        checkpoint.accepted_output_prefix,
    )
    if checkpoint.output_transcript_hash != expected_output_hash:
        raise ValueError("E2 checkpoint output transcript hash is invalid")
    if any(
        not source_hash or not result_hash
        for source_hash, result_hash in checkpoint.accepted_output_prefix
    ):
        raise ValueError("E2 checkpoint has a malformed output transcript")


def _candidate_subgroup(
    candidate: E1SubgroupCandidate,
    group: FiniteAbelianGroup,
    backend: FiniteIntegerBackend,
):
    matrix = _matrix_from_columns(
        candidate.generator_vectors, group.presentation_rank
    )
    return group.subgroup(matrix, backend)


def _invariant_under_power(
    candidate: E1SubgroupCandidate,
    group: FiniteAbelianGroup,
    action: FiniteGroupHomomorphism,
    period: int,
    backend: FiniteIntegerBackend,
) -> bool:
    subgroup = _candidate_subgroup(candidate, group, backend)
    for generator in candidate.generator_vectors:
        mapped = tuple(generator)
        for _ in range(period):
            mapped = _matrix_vector(action.lift_matrix, mapped)
        if not subgroup.contains(mapped, backend):
            return False
    return True


def _fundamental_periods(
    candidate: E1SubgroupCandidate,
    group: FiniteAbelianGroup,
    actions: Sequence[E2TangentAction],
    declared_period: Sequence[int],
    backend: FiniteIntegerBackend,
) -> Tuple[Tuple[Optional[int], ...], bool]:
    periods = []
    accepted = True
    for action, period in zip(actions, declared_period):
        fundamental = next(
            (
                divisor
                for divisor in _divisors(period)
                if _invariant_under_power(
                    candidate,
                    group,
                    action.quotient_action,
                    divisor,
                    backend,
                )
            ),
            None,
        )
        periods.append(fundamental)
        if fundamental is None:
            accepted = False
    return tuple(periods), accepted


def _support_generable(
    candidate: E1SubgroupCandidate,
    group: FiniteAbelianGroup,
    support_images,
    backend: FiniteIntegerBackend,
) -> bool:
    """Test whether the subgroup has generators within the support envelope.

    For every allowed site subset ``J``, ``U_J`` is the exact image in the
    finite quotient of centralizer operators supported on ``J``.  A candidate
    subgroup ``H`` has an in-bound generating set exactly when

        H = sum_U (H intersect U),

    where ``U`` traverses the deduplicated complete finite orbit of every
    anchor support image under the supplied microscopic tangent translations.
    The support test is independent of the period condition ``T_i^p_i H = H``:
    different sublattice offsets may carry independent local seeds.
    """

    subgroup = _candidate_subgroup(candidate, group, backend)
    generated = group.trivial_subgroup(backend)
    for support_image in support_images:
        generated = generated.sum(
            subgroup.intersection(support_image, backend), backend
        )
    return (
        generated.contains_subgroup(subgroup, backend)
        and subgroup.contains_subgroup(generated, backend)
    )


def _evaluate_candidate(
    candidate: E1SubgroupCandidate,
    group: FiniteAbelianGroup,
    actions: Sequence[E2TangentAction],
    domain: BoundedPeriodicSearchDomain,
    support_images,
    backend: FiniteIntegerBackend,
) -> E2CandidateDecision:
    fundamental, translation_compatible = _fundamental_periods(
        candidate,
        group,
        actions,
        domain.unit_cell_period,
        backend,
    )
    support_generable = _support_generable(
        candidate,
        group,
        support_images,
        backend,
    )
    return E2CandidateDecision(
        candidate,
        support_generable,
        fundamental,
        translation_compatible and support_generable,
    )


def _result_from_decision(
    decision: E2CandidateDecision,
    domain: BoundedPeriodicSearchDomain,
    action_names: Sequence[str],
) -> E2TranslationInvariantCandidate:
    if not decision.accepted or any(
        value is None for value in decision.fundamental_period
    ):
        raise ValueError("cannot construct an E2 result from a rejected decision")
    return E2TranslationInvariantCandidate(
        decision.e1_candidate,
        domain.unit_cell_period,
        tuple(int(value) for value in decision.fundamental_period),
        tuple(action_names),
    )


def _unsupported_reasons(
    domain: BoundedPeriodicSearchDomain,
) -> Tuple[str, ...]:
    reasons = []
    if domain.ancilla_bound.max_sites_per_unit_cell != 0:
        reasons.append(
            "ancilla enumeration is not implemented; "
            "max_sites_per_unit_cell must be zero"
        )
    supported_families = frozenset(("translation_compatible_submodules",))
    unsupported = tuple(
        family
        for family in domain.candidate_families
        if family not in supported_families
    )
    if unsupported:
        reasons.append(
            "candidate families not implemented by the E2 core: "
            + ", ".join(unsupported)
        )
    return tuple(reasons)


def enumerate_e2_bounded_periodic(
    algebra: FiniteBoundaryAlgebra,
    domain: BoundedPeriodicSearchDomain,
    actions: Sequence[E2TangentAction],
    backend: FiniteIntegerBackend,
    site_coordinates: Sequence[E2SiteCoordinate],
    budget: EnumerationBudget = EnumerationBudget(),
    checkpoint: Optional[E2EnumerationCheckpoint] = None,
) -> E2EnumerationPage:
    """Enumerate one resumable page of bounded-periodic isotropic candidates."""

    values = tuple(actions)
    realization = bind_bounded_periodic_algebra(
        algebra, domain, values, backend, site_coordinates
    )
    realization_hash = canonical_hash("e2-algebra-realization-v1", realization)
    anchor_support_images = _compile_anchor_support_images(
        algebra, domain, realization.site_coordinates, backend
    )
    if tuple(
        (
            site_subset,
            canonical_hash("e2-support-quotient-image-v1", subgroup),
        )
        for site_subset, subgroup in anchor_support_images
    ) != realization.support_image_hashes:
        raise ArithmeticError("E2 support coverage witness failed replay")
    paired_for_support = paired_boundary_presentation(algebra, backend)
    support_images = _compile_translated_support_images(
        anchor_support_images,
        values,
        paired_for_support.group,
        backend,
    )
    if tuple(
        canonical_hash("e2-translated-support-image-v1", subgroup)
        for subgroup in support_images
    ) != realization.translated_support_image_hashes:
        raise ArithmeticError(
            "E2 translated support-image orbit failed replay"
        )
    reasons = _unsupported_reasons(domain)
    if reasons:
        certificate = E2CompletenessCertificate(
            domain=domain,
            realization=realization,
            e1_certificate=None,
            termination=E2Termination.UNSUPPORTED,
            processed_e1_candidates=0,
            accepted_candidates=0,
            candidate_transcript_hash="",
            output_transcript_hash="",
            page_work_units=0,
            total_work_units=0,
            unsupported_reasons=reasons,
            exactness=Exactness.UNSUPPORTED,
            verification=(
                "unsupported bounds were rejected before candidate enumeration",
            ),
        )
        return E2EnumerationPage((), None, certificate)

    if checkpoint is None:
        candidate_hash = _candidate_genesis(
            realization.domain_hash, realization_hash
        )
        checkpoint = E2EnumerationCheckpoint(
            domain_hash=realization.domain_hash,
            realization_hash=realization_hash,
            candidate_transcript_hash=candidate_hash,
            output_transcript_hash=_output_genesis(
                realization.domain_hash, realization_hash
            ),
        )
    else:
        paired = paired_boundary_presentation(algebra, backend)
        _validate_checkpoint(
            checkpoint,
            realization,
            domain,
            values,
            paired.group,
            support_images,
            backend,
        )

    e1_checkpoint = checkpoint.e1_checkpoint
    e1_certificate = checkpoint.e1_certificate
    e1_complete = checkpoint.e1_complete
    pending = list(checkpoint.pending_e1_candidates)
    transcript = list(checkpoint.candidate_transcript)
    candidate_transcript_hash = checkpoint.candidate_transcript_hash
    output_prefix = list(checkpoint.accepted_output_prefix)
    output_transcript_hash = checkpoint.output_transcript_hash
    page_candidates = []
    work = 0
    paired = paired_boundary_presentation(algebra, backend)

    while work < budget.max_work_units:
        if pending:
            if len(page_candidates) >= budget.max_results:
                break
            candidate = pending[0]
            # One transcript/output decision plus one exact subgroup-invariance
            # test per possible divisor plus one support-intersection test per
            # deduplicated translated support image.  The conservative divisor
            # reservation avoids splitting a decision when an earlier divisor works.
            candidate_cost = 1 + len(support_images) + sum(
                len(_divisors(period)) for period in domain.unit_cell_period
            )
            if work + candidate_cost > budget.max_work_units:
                break
            pending.pop(0)
            decision = _evaluate_candidate(
                candidate,
                paired.group,
                values,
                domain,
                support_images,
                backend,
            )
            work += candidate_cost
            source_hash = _candidate_hash(candidate)
            transcript.append(decision)
            candidate_transcript_hash = _candidate_step(
                candidate_transcript_hash,
                len(transcript) - 1,
                decision,
            )
            if decision.accepted:
                result = _result_from_decision(
                    decision, domain, realization.action_names
                )
                result_hash = canonical_hash("e2-candidate-output-v1", result)
                output_entry = (source_hash, result_hash)
                output_prefix.append(output_entry)
                output_transcript_hash = _output_step(
                    output_transcript_hash,
                    len(output_prefix) - 1,
                    output_entry,
                )
                page_candidates.append(result)
            continue

        if e1_complete:
            break

        remaining = budget.max_work_units - work
        e1_budget = replace(
            budget,
            max_work_units=remaining,
            max_results=max(1, budget.max_results),
        )
        e1_page = enumerate_e1_subgroups(
            algebra, backend, e1_budget, e1_checkpoint
        )
        consumed = e1_page.certificate.page_work_units
        if consumed < 0 or consumed > remaining:
            raise ArithmeticError("E1 resource accounting exceeded the E2 budget")
        work += consumed
        e1_checkpoint = e1_page.checkpoint
        e1_certificate = e1_page.certificate
        e1_complete = e1_page.certificate.certified_complete
        pending.extend(e1_page.candidates)
        if consumed == 0 and not pending:
            break

    complete = e1_complete and not pending and realization.verified
    if e1_certificate is not None:
        issued_e1_candidates = tuple(
            decision.e1_candidate for decision in transcript
        ) + tuple(pending)
        if replay_e1_output_transcript(
            realization.algebra_input_hash,
            e1_certificate.candidate_transcript_hash,
            issued_e1_candidates,
        ) != e1_certificate.output_transcript_hash:
            raise ArithmeticError(
                "E2 state failed the certified E1 output transcript replay"
            )
    if complete and e1_certificate is not None:
        if len(transcript) != e1_certificate.isotropic_subgroups:
            raise ArithmeticError(
                "E2 exhaustion did not consume every certified E1 candidate"
            )
    accepted_source_hashes = tuple(
        _candidate_hash(decision.e1_candidate)
        for decision in transcript
        if decision.accepted
    )
    if tuple(entry[0] for entry in output_prefix) != accepted_source_hashes:
        raise ArithmeticError("E2 accepted output prefix is inconsistent")
    if candidate_transcript_hash != _replay_candidate_transcript(
        realization.domain_hash, realization_hash, transcript
    ):
        raise ArithmeticError("E2 candidate transcript failed replay")
    if output_transcript_hash != _replay_output(
        realization.domain_hash, realization_hash, output_prefix
    ):
        raise ArithmeticError("E2 output transcript failed replay")

    termination = (
        E2Termination.EXHAUSTED
        if complete
        else E2Termination.RESOURCE_LIMIT
    )
    exactness = (
        Exactness.BOUNDED_EXACT if complete else Exactness.EXPERIMENTAL
    )
    verification = [
        "explicit adapted site coordinates cover the finite window and are bound to a replayed finite-FGA support-image certificate",
        "the coefficient-domain capability key matches the finite Pauli module",
        "all tangent actions are pairing-preserving automorphisms",
        "all tangent actions commute on the finite quotient",
        "divisors were tested in ascending order until the first invariant period",
        "every accepted subgroup is generated by intersections with the deduplicated complete microscopic-translation orbit of exact anchor support images",
        "E1 and E2 filtering work units share one page budget",
    ]
    if complete:
        verification.extend(
            (
                "the certified-complete E1 output was consumed exactly once",
                "every accepted subgroup is invariant under each declared period translation",
            )
        )
    total_work = checkpoint.total_work_units + work
    certificate = E2CompletenessCertificate(
        domain=domain,
        realization=realization,
        e1_certificate=e1_certificate,
        termination=termination,
        processed_e1_candidates=len(transcript),
        accepted_candidates=len(output_prefix),
        candidate_transcript_hash=candidate_transcript_hash,
        output_transcript_hash=output_transcript_hash,
        page_work_units=work,
        total_work_units=total_work,
        unsupported_reasons=(),
        exactness=exactness,
        verification=tuple(verification),
    )
    next_checkpoint = None
    if not complete:
        next_checkpoint = _seal_checkpoint(E2EnumerationCheckpoint(
            domain_hash=realization.domain_hash,
            realization_hash=realization_hash,
            e1_checkpoint=e1_checkpoint,
            e1_certificate=e1_certificate,
            e1_complete=e1_complete,
            pending_e1_candidates=tuple(pending),
            candidate_transcript=tuple(transcript),
            candidate_transcript_hash=candidate_transcript_hash,
            accepted_output_prefix=tuple(output_prefix),
            output_transcript_hash=output_transcript_hash,
            total_work_units=total_work,
        ))
    return E2EnumerationPage(
        tuple(page_candidates), next_checkpoint, certificate
    )


__all__ = [
    "BoundedPeriodicAlgebraRealization",
    "E2CandidateDecision",
    "E2CompletenessCertificate",
    "E2EnumerationCheckpoint",
    "E2EnumerationPage",
    "E2TangentAction",
    "E2SiteCoordinate",
    "E2Termination",
    "E2TranslationInvariantCandidate",
    "bind_bounded_periodic_algebra",
    "bounded_periodic_search_extent",
    "enumerate_e2_bounded_periodic",
]
