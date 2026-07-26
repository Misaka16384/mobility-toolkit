"""Resource-bounded, resumable E1 enumeration for finite paired algebras.

E1 is exhaustive only for the finite paired group recorded in
``E1SearchDomain``.  It makes no claim about larger support windows or a
thermodynamic boundary.  The implementation intentionally favors transparent
certificates over asymptotic performance; later backends may replace the
subgroup traversal without changing these contracts.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Dict, Iterable, Optional, Sequence, Tuple

from sympy import Matrix as SympyMatrix

from mobility_toolkit.boundary.algebra import FiniteBoundaryAlgebra
from mobility_toolkit.core import Exactness, PauliOperator, PresentedModule, SparseIntMatrix
from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FiniteGroupHomomorphism,
    FiniteIntegerBackend,
    PairedFiniteAbelianGroup,
    StabilizerValidation,
    validate_stabilizer_generators,
)


ElementKey = Tuple[Tuple[int, int], ...]
IndexSubgroup = Tuple[int, ...]
CandidateTranscriptEntry = Tuple[IndexSubgroup, str]
OutputPrefixEntry = Tuple[IndexSubgroup, str]

_ISOTROPIC = "isotropic"
_NOT_ISOTROPIC = "not_isotropic"
_CANDIDATE_OUTCOMES = frozenset((_ISOTROPIC, _NOT_ISOTROPIC))


def _plain_positive(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _columns(matrix: SparseIntMatrix) -> Tuple[Tuple[int, ...], ...]:
    rows = matrix.to_rows()
    return tuple(
        tuple(rows[row][column] for row in range(matrix.nrows))
        for column in range(matrix.ncols)
    )


def _matrix_from_columns(columns: Sequence[Sequence[int]], nrows: int) -> SparseIntMatrix:
    columns = tuple(tuple(column) for column in columns)
    return SparseIntMatrix(
        nrows,
        len(columns),
        tuple(
            (row, column_index, value)
            for column_index, column in enumerate(columns)
            for row, value in enumerate(column)
            if value
        ),
    )


@dataclass(frozen=True)
class EnumerationBudget:
    max_work_units: int = 100_000
    max_results: int = 1_000
    max_phase_assignments: int = 100_000
    max_elements: int = 4_096
    max_subgroups: int = 100_000

    SCHEMA_ID = "mobility_toolkit.enumeration_budget.v1"

    def __post_init__(self) -> None:
        _plain_positive(self.max_work_units, "max_work_units")
        _plain_positive(self.max_results, "max_results")
        _plain_positive(self.max_phase_assignments, "max_phase_assignments")
        _plain_positive(self.max_elements, "max_elements")
        _plain_positive(self.max_subgroups, "max_subgroups")

    def to_canonical_dict(self) -> dict:
        return {
            "max_phase_assignments": self.max_phase_assignments,
            "max_elements": self.max_elements,
            "max_results": self.max_results,
            "max_subgroups": self.max_subgroups,
            "max_work_units": self.max_work_units,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class E1SearchDomain:
    algebra_input_hash: str
    invariant_factors: Tuple[int, ...]
    group_order: int
    exponent: int
    presentation_rank: int
    pairing_modulus: int
    equivalence_relation: str = "raw_subgroups"
    finite_window_id: str = ""
    finite_window_site_ids: Tuple[str, ...] = ()
    finite_window_search_extent: Tuple[Tuple[str, int], ...] = ()

    SCHEMA_ID = "mobility_toolkit.e1_search_domain.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "algebra_input_hash": self.algebra_input_hash,
            "equivalence_relation": self.equivalence_relation,
            "exponent": self.exponent,
            "finite_window_id": self.finite_window_id,
            "finite_window_search_extent": self.finite_window_search_extent,
            "finite_window_site_ids": self.finite_window_site_ids,
            "group_order": self.group_order,
            "invariant_factors": self.invariant_factors,
            "pairing_modulus": self.pairing_modulus,
            "presentation_rank": self.presentation_rank,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class E1CompletenessCertificate:
    domain: E1SearchDomain
    elements_complete: bool
    subgroup_search_complete: bool
    output_complete: bool
    coordinate_tuples_scanned: int
    distinct_elements: int
    subgroup_join_tests: int
    distinct_subgroups: int
    candidate_subgroups_scanned: int
    isotropic_subgroups: int
    output_prefix_length: int
    candidate_transcript_hash: str
    output_transcript_hash: str
    page_work_units: int
    exactness: Exactness
    verification: Tuple[str, ...]
    theorem_scope: str = (
        "exhaustion of the recorded finite paired group only; no larger-window or "
        "thermodynamic completeness follows"
    )

    SCHEMA_ID = "mobility_toolkit.e1_completeness_certificate.v2"

    @property
    def certified_complete(self) -> bool:
        return (
            self.elements_complete
            and self.subgroup_search_complete
            and self.output_complete
        )

    def to_canonical_dict(self) -> dict:
        return {
            "certified_complete": self.certified_complete,
            "candidate_subgroups_scanned": self.candidate_subgroups_scanned,
            "candidate_transcript_hash": self.candidate_transcript_hash,
            "coordinate_tuples_scanned": self.coordinate_tuples_scanned,
            "distinct_elements": self.distinct_elements,
            "distinct_subgroups": self.distinct_subgroups,
            "domain": self.domain,
            "elements_complete": self.elements_complete,
            "exactness": self.exactness,
            "isotropic_subgroups": self.isotropic_subgroups,
            "output_complete": self.output_complete,
            "output_prefix_length": self.output_prefix_length,
            "output_transcript_hash": self.output_transcript_hash,
            "page_work_units": self.page_work_units,
            "schema": self.SCHEMA_ID,
            "subgroup_join_tests": self.subgroup_join_tests,
            "subgroup_search_complete": self.subgroup_search_complete,
            "verification": self.verification,
            "theorem_scope": self.theorem_scope,
        }


@dataclass(frozen=True)
class E1EnumerationCheckpoint:
    algebra_input_hash: str
    element_cursor: int = 0
    element_vectors: Tuple[Tuple[int, ...], ...] = ()
    pending_subgroups: Tuple[IndexSubgroup, ...] = ()
    seen_subgroups: Tuple[IndexSubgroup, ...] = ()
    active_subgroup: Optional[IndexSubgroup] = None
    active_element_cursor: int = 0
    subgroup_join_tests: int = 0
    subgroup_search_complete: bool = False
    candidate_scan_cursor: int = 0
    candidate_transcript: Tuple[CandidateTranscriptEntry, ...] = ()
    candidate_transcript_hash: str = ""
    output_cursor: int = 0
    output_prefix: Tuple[OutputPrefixEntry, ...] = ()
    output_transcript_hash: str = ""
    checkpoint_hash: str = ""

    SCHEMA_ID = "mobility_toolkit.e1_enumeration_checkpoint.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "active_element_cursor": self.active_element_cursor,
            "active_subgroup": self.active_subgroup,
            "algebra_input_hash": self.algebra_input_hash,
            "candidate_scan_cursor": self.candidate_scan_cursor,
            "candidate_transcript": self.candidate_transcript,
            "candidate_transcript_hash": self.candidate_transcript_hash,
            "checkpoint_hash": self.checkpoint_hash,
            "element_cursor": self.element_cursor,
            "element_vectors": self.element_vectors,
            "output_cursor": self.output_cursor,
            "output_prefix": self.output_prefix,
            "output_transcript_hash": self.output_transcript_hash,
            "pending_subgroups": self.pending_subgroups,
            "schema": self.SCHEMA_ID,
            "seen_subgroups": self.seen_subgroups,
            "subgroup_join_tests": self.subgroup_join_tests,
            "subgroup_search_complete": self.subgroup_search_complete,
        }


@dataclass(frozen=True)
class E1SubgroupCandidate:
    algebra_input_hash: str
    element_indices: IndexSubgroup
    generator_indices: Tuple[int, ...]
    generator_vectors: Tuple[Tuple[int, ...], ...]
    invariant_factors: Tuple[int, ...]
    order: int
    isotropic: bool
    maximal_isotropic: bool
    self_orthogonal_lagrangian: bool

    SCHEMA_ID = "mobility_toolkit.e1_subgroup_candidate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "element_indices": self.element_indices,
            "algebra_input_hash": self.algebra_input_hash,
            "generator_indices": self.generator_indices,
            "generator_vectors": self.generator_vectors,
            "invariant_factors": self.invariant_factors,
            "isotropic": self.isotropic,
            "maximal_isotropic": self.maximal_isotropic,
            "order": self.order,
            "schema": self.SCHEMA_ID,
            "self_orthogonal_lagrangian": self.self_orthogonal_lagrangian,
        }


@dataclass(frozen=True)
class E1EnumerationPage:
    domain: E1SearchDomain
    candidates: Tuple[E1SubgroupCandidate, ...]
    checkpoint: Optional[E1EnumerationCheckpoint]
    certificate: E1CompletenessCertificate

    SCHEMA_ID = "mobility_toolkit.e1_enumeration_page.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidates": self.candidates,
            "certificate": self.certificate,
            "checkpoint": self.checkpoint,
            "domain": self.domain,
            "schema": self.SCHEMA_ID,
        }


class _ElementSpace:
    def __init__(self, paired: PairedFiniteAbelianGroup) -> None:
        self.paired = paired
        rows = paired.group.relation_lattice_basis.to_rows()
        self._inverse = SympyMatrix(rows).inv() if rows else SympyMatrix.zeros(0, 0)
        self._pairing = paired.pairing_matrix.to_rows()

    def key(self, vector: Sequence[int]) -> ElementKey:
        if not vector:
            return ()
        coordinates = self._inverse * SympyMatrix(tuple(vector))
        result = []
        for value in coordinates:
            rational = Fraction(int(value.p), int(value.q))
            reduced = rational - math.floor(rational)
            result.append((reduced.numerator, reduced.denominator))
        return tuple(result)

    def pairing(self, left: Sequence[int], right: Sequence[int]) -> int:
        return sum(
            left[row] * self._pairing[row][column] * right[column]
            for row in range(len(left))
            for column in range(len(right))
        ) % self.paired.modulus


def paired_boundary_presentation(
    algebra: FiniteBoundaryAlgebra, backend: FiniteIntegerBackend
) -> PairedFiniteAbelianGroup:
    quotient = algebra.paired_algebra
    rank = quotient.quotient.inclusion_matrix.nrows
    group = FiniteAbelianGroup.from_presentation(
        PresentedModule(rank, quotient.quotient.inclusion_matrix), backend
    )
    return PairedFiniteAbelianGroup.create(
        group, quotient.modulus, quotient.presentation_pairing_matrix
    )


def _domain(algebra: FiniteBoundaryAlgebra, paired: PairedFiniteAbelianGroup) -> E1SearchDomain:
    input_hash = canonical_hash(
        "e1-finite-paired-algebra-v1",
        {"paired": paired, "window": algebra.window},
    )
    order = 1
    for factor in paired.group.invariant_factors:
        order *= factor
    exponent = paired.group.invariant_factors[-1] if paired.group.invariant_factors else 1
    return E1SearchDomain(
        input_hash,
        paired.group.invariant_factors,
        order,
        exponent,
        paired.group.presentation_rank,
        paired.modulus,
        finite_window_id=algebra.window.window_id,
        finite_window_site_ids=algebra.window.site_ids,
        finite_window_search_extent=algebra.window.search_extent,
    )


def _digits(index: int, base: int, length: int) -> Tuple[int, ...]:
    values = []
    for _ in range(length):
        values.append(index % base)
        index //= base
    return tuple(values)


def _closure(
    subgroup: IndexSubgroup,
    element_index: int,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> IndexSubgroup:
    if element_index in subgroup:
        return subgroup
    zero = keys[space.key((0,) * len(vectors[0]))] if vectors else 0
    cyclic = [zero]
    current = vectors[element_index]
    while space.key(current) != space.key((0,) * len(current)):
        cyclic.append(keys[space.key(current)])
        current = tuple(
            current[index] + vectors[element_index][index]
            for index in range(len(current))
        )
    members = set()
    for left_index in subgroup:
        for right_index in cyclic:
            total = tuple(
                vectors[left_index][index] + vectors[right_index][index]
                for index in range(len(vectors[left_index]))
            )
            members.add(keys[space.key(total)])
    return tuple(sorted(members))


def _canonical_generators(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> Tuple[int, ...]:
    zero = keys[space.key((0,) * (len(vectors[0]) if vectors else 0))]
    generated: IndexSubgroup = (zero,)
    generators = []
    for element in subgroup:
        if element in generated:
            continue
        generators.append(element)
        generated = _closure(generated, element, vectors, keys, space)
        if generated == subgroup:
            break
    return tuple(generators)


def _isotropic(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    space: _ElementSpace,
) -> bool:
    return all(
        space.pairing(vectors[left], vectors[right]) == 0
        for left in subgroup
        for right in subgroup
    )


def _orthogonal(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    space: _ElementSpace,
) -> IndexSubgroup:
    return tuple(
        index
        for index, vector in enumerate(vectors)
        if all(space.pairing(vector, vectors[item]) == 0 for item in subgroup)
    )


def _candidate_record(
    subgroup: IndexSubgroup,
    isotropic_subgroups: Sequence[IndexSubgroup],
    vectors: Sequence[Tuple[int, ...]],
    paired: PairedFiniteAbelianGroup,
    backend: FiniteIntegerBackend,
    space: _ElementSpace,
    algebra_input_hash: str,
) -> E1SubgroupCandidate:
    keys = {space.key(vector): index for index, vector in enumerate(vectors)}
    member_set = frozenset(subgroup)
    generators = _canonical_generators(subgroup, vectors, keys, space)
    generator_vectors = tuple(vectors[index] for index in generators)
    matrix = _matrix_from_columns(generator_vectors, paired.group.presentation_rank)
    finite_subgroup = paired.group.subgroup(matrix, backend)
    maximal = not any(
        member_set < frozenset(other) for other in isotropic_subgroups
    )
    return E1SubgroupCandidate(
        algebra_input_hash,
        subgroup,
        generators,
        generator_vectors,
        finite_subgroup.invariant_factors(backend),
        len(subgroup),
        True,
        maximal,
        subgroup == _orthogonal(subgroup, vectors, space),
    )


def _candidate_transcript_genesis(algebra_input_hash: str) -> str:
    return canonical_hash(
        "e1-candidate-transcript-genesis-v1",
        {"algebra_input_hash": algebra_input_hash},
    )


def _candidate_transcript_step(
    previous_hash: str,
    scan_index: int,
    entry: CandidateTranscriptEntry,
) -> str:
    subgroup, outcome = entry
    return canonical_hash(
        "e1-candidate-transcript-step-v1",
        {
            "outcome": outcome,
            "previous_hash": previous_hash,
            "scan_index": scan_index,
            "subgroup": subgroup,
        },
    )


def _replay_candidate_transcript(
    algebra_input_hash: str,
    transcript: Sequence[CandidateTranscriptEntry],
) -> str:
    digest = _candidate_transcript_genesis(algebra_input_hash)
    for scan_index, entry in enumerate(transcript):
        digest = _candidate_transcript_step(digest, scan_index, entry)
    return digest


def _output_transcript_genesis(
    algebra_input_hash: str, candidate_transcript_hash: str
) -> str:
    return canonical_hash(
        "e1-output-transcript-genesis-v1",
        {
            "algebra_input_hash": algebra_input_hash,
            "candidate_transcript_hash": candidate_transcript_hash,
        },
    )


def _output_transcript_step(
    previous_hash: str,
    output_index: int,
    entry: OutputPrefixEntry,
) -> str:
    subgroup, candidate_hash = entry
    return canonical_hash(
        "e1-output-transcript-step-v1",
        {
            "candidate_hash": candidate_hash,
            "output_index": output_index,
            "previous_hash": previous_hash,
            "subgroup": subgroup,
        },
    )


def _replay_output_transcript(
    algebra_input_hash: str,
    candidate_transcript_hash: str,
    prefix: Sequence[OutputPrefixEntry],
) -> str:
    digest = _output_transcript_genesis(
        algebra_input_hash, candidate_transcript_hash
    )
    for output_index, entry in enumerate(prefix):
        digest = _output_transcript_step(digest, output_index, entry)
    return digest


def _checkpoint_payload(checkpoint: E1EnumerationCheckpoint) -> dict:
    return {
        "active_element_cursor": checkpoint.active_element_cursor,
        "active_subgroup": checkpoint.active_subgroup,
        "algebra_input_hash": checkpoint.algebra_input_hash,
        "candidate_scan_cursor": checkpoint.candidate_scan_cursor,
        "candidate_transcript": checkpoint.candidate_transcript,
        "candidate_transcript_hash": checkpoint.candidate_transcript_hash,
        "element_cursor": checkpoint.element_cursor,
        "element_vectors": checkpoint.element_vectors,
        "output_cursor": checkpoint.output_cursor,
        "output_prefix": checkpoint.output_prefix,
        "output_transcript_hash": checkpoint.output_transcript_hash,
        "pending_subgroups": checkpoint.pending_subgroups,
        "seen_subgroups": checkpoint.seen_subgroups,
        "subgroup_join_tests": checkpoint.subgroup_join_tests,
        "subgroup_search_complete": checkpoint.subgroup_search_complete,
    }


def _seal_checkpoint(
    checkpoint: E1EnumerationCheckpoint,
) -> E1EnumerationCheckpoint:
    unsealed = replace(checkpoint, checkpoint_hash="")
    return replace(
        unsealed,
        checkpoint_hash=canonical_hash(
            "e1-enumeration-checkpoint-state-v1",
            _checkpoint_payload(unsealed),
        ),
    )


def _validate_checkpoint(
    checkpoint: E1EnumerationCheckpoint,
    domain: E1SearchDomain,
) -> None:
    if checkpoint.algebra_input_hash != domain.algebra_input_hash:
        raise ValueError("E1 checkpoint belongs to a different paired algebra")
    if not checkpoint.checkpoint_hash:
        raise ValueError("E1 checkpoint is unsealed")
    if _seal_checkpoint(checkpoint).checkpoint_hash != checkpoint.checkpoint_hash:
        raise ValueError("E1 checkpoint state hash is invalid")
    scalar_fields = (
        checkpoint.element_cursor,
        checkpoint.active_element_cursor,
        checkpoint.subgroup_join_tests,
        checkpoint.candidate_scan_cursor,
        checkpoint.output_cursor,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in scalar_fields
    ):
        raise ValueError("E1 checkpoint has an invalid cursor")
    if any(
        len(vector) != domain.presentation_rank
        for vector in checkpoint.element_vectors
    ):
        raise ValueError("E1 checkpoint has an invalid element vector")
    if checkpoint.active_element_cursor > len(checkpoint.element_vectors):
        raise ValueError("E1 checkpoint active cursor is out of range")
    if len(set(checkpoint.seen_subgroups)) != len(checkpoint.seen_subgroups):
        raise ValueError("E1 checkpoint repeats a seen subgroup")
    if len(set(checkpoint.pending_subgroups)) != len(checkpoint.pending_subgroups):
        raise ValueError("E1 checkpoint repeats pending work")
    seen = set(checkpoint.seen_subgroups)
    if any(subgroup not in seen for subgroup in checkpoint.pending_subgroups):
        raise ValueError("E1 checkpoint has unseen pending work")
    if checkpoint.active_subgroup is not None and checkpoint.active_subgroup not in seen:
        raise ValueError("E1 checkpoint has an unseen active subgroup")
    if checkpoint.subgroup_search_complete and (
        checkpoint.pending_subgroups or checkpoint.active_subgroup is not None
    ):
        raise ValueError("completed E1 checkpoint still has pending work")
    if not checkpoint.subgroup_search_complete and (
        checkpoint.candidate_scan_cursor
        or checkpoint.candidate_transcript
        or checkpoint.output_cursor
        or checkpoint.output_prefix
    ):
        raise ValueError("E1 checkpoint scanned candidates before subgroup exhaustion")
    if len(checkpoint.candidate_transcript) != checkpoint.candidate_scan_cursor:
        raise ValueError("E1 checkpoint candidate transcript disagrees with its cursor")
    if checkpoint.candidate_scan_cursor > len(seen):
        raise ValueError("E1 checkpoint candidate cursor is out of range")
    expected_subgroups = tuple(sorted(seen))[: checkpoint.candidate_scan_cursor]
    transcript_subgroups = []
    for entry in checkpoint.candidate_transcript:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError("E1 checkpoint has a malformed candidate transcript")
        subgroup, outcome = entry
        transcript_subgroups.append(subgroup)
        if outcome not in _CANDIDATE_OUTCOMES:
            raise ValueError("E1 checkpoint has an invalid isotropy outcome")
    if tuple(transcript_subgroups) != expected_subgroups:
        raise ValueError("E1 checkpoint candidate transcript is not its scan prefix")
    expected_candidate_hash = _replay_candidate_transcript(
        domain.algebra_input_hash, checkpoint.candidate_transcript
    )
    if checkpoint.candidate_transcript_hash != expected_candidate_hash:
        raise ValueError("E1 checkpoint candidate transcript hash is invalid")
    isotropic_subgroups = tuple(
        subgroup
        for subgroup, outcome in checkpoint.candidate_transcript
        if outcome == _ISOTROPIC
    )
    if checkpoint.output_cursor > len(isotropic_subgroups):
        raise ValueError("E1 checkpoint output cursor is out of range")
    if checkpoint.output_cursor and checkpoint.candidate_scan_cursor != len(seen):
        raise ValueError("E1 checkpoint emitted output before isotropy exhaustion")
    if len(checkpoint.output_prefix) != checkpoint.output_cursor:
        raise ValueError("E1 checkpoint output prefix disagrees with its cursor")
    if tuple(entry[0] for entry in checkpoint.output_prefix) != isotropic_subgroups[
        : checkpoint.output_cursor
    ]:
        raise ValueError("E1 checkpoint output prefix skips an isotropic subgroup")
    if any(not candidate_hash for _, candidate_hash in checkpoint.output_prefix):
        raise ValueError("E1 checkpoint output prefix omits a candidate hash")
    expected_output_hash = _replay_output_transcript(
        domain.algebra_input_hash,
        checkpoint.candidate_transcript_hash,
        checkpoint.output_prefix,
    )
    if checkpoint.output_transcript_hash != expected_output_hash:
        raise ValueError("E1 checkpoint output transcript hash is invalid")


def enumerate_e1_subgroups(
    algebra: FiniteBoundaryAlgebra,
    backend: FiniteIntegerBackend,
    budget: EnumerationBudget = EnumerationBudget(),
    checkpoint: Optional[E1EnumerationCheckpoint] = None,
) -> E1EnumerationPage:
    """Return one resumable page of all isotropic E1 subgroups.

    A non-``None`` checkpoint must be passed back unchanged to resume.  A
    ``certified_complete`` certificate proves exhaustion of the recorded
    finite presentation, not of larger windows.
    """

    paired = paired_boundary_presentation(algebra, backend)
    domain = _domain(algebra, paired)
    if checkpoint is None:
        candidate_hash = _candidate_transcript_genesis(
            domain.algebra_input_hash
        )
        checkpoint = E1EnumerationCheckpoint(
            algebra_input_hash=domain.algebra_input_hash,
            candidate_transcript_hash=candidate_hash,
            output_transcript_hash=_output_transcript_genesis(
                domain.algebra_input_hash, candidate_hash
            ),
        )
    else:
        _validate_checkpoint(checkpoint, domain)

    if domain.group_order > budget.max_elements:
        certificate = E1CompletenessCertificate(
            domain=domain,
            elements_complete=False,
            subgroup_search_complete=False,
            output_complete=False,
            coordinate_tuples_scanned=checkpoint.element_cursor,
            distinct_elements=len(checkpoint.element_vectors),
            subgroup_join_tests=checkpoint.subgroup_join_tests,
            distinct_subgroups=len(checkpoint.seen_subgroups),
            candidate_subgroups_scanned=checkpoint.candidate_scan_cursor,
            isotropic_subgroups=sum(
                outcome == _ISOTROPIC
                for _, outcome in checkpoint.candidate_transcript
            ),
            output_prefix_length=len(checkpoint.output_prefix),
            candidate_transcript_hash=checkpoint.candidate_transcript_hash,
            output_transcript_hash=checkpoint.output_transcript_hash,
            page_work_units=0,
            exactness=Exactness.EXPERIMENTAL,
            verification=(f"group order exceeds max_elements={budget.max_elements}",),
        )
        return E1EnumerationPage(
            domain, (), _seal_checkpoint(checkpoint), certificate
        )

    space = _ElementSpace(paired)
    element_vectors = list(checkpoint.element_vectors)
    known_keys = {space.key(vector) for vector in element_vectors}
    if len(known_keys) != len(element_vectors):
        raise ValueError("E1 checkpoint repeats a finite-group element")
    element_cursor = checkpoint.element_cursor
    work = 0
    coordinate_limit = domain.exponent ** domain.presentation_rank
    if element_cursor > coordinate_limit:
        raise ValueError("E1 checkpoint element cursor is out of range")
    while len(element_vectors) < domain.group_order and element_cursor < coordinate_limit:
        if work >= budget.max_work_units:
            break
        vector = _digits(element_cursor, domain.exponent, domain.presentation_rank)
        element_cursor += 1
        work += 1
        key = space.key(vector)
        if key not in known_keys:
            known_keys.add(key)
            element_vectors.append(vector)
    elements_complete = len(element_vectors) == domain.group_order
    if element_cursor == coordinate_limit and not elements_complete:
        raise ArithmeticError("E1 element materialization contradicts its group order")

    pending = list(checkpoint.pending_subgroups)
    seen = set(checkpoint.seen_subgroups)
    active = checkpoint.active_subgroup
    active_cursor = checkpoint.active_element_cursor
    join_tests = checkpoint.subgroup_join_tests
    if elements_complete and not seen:
        zero_index = next(
            index
            for index, vector in enumerate(element_vectors)
            if space.key(vector) == space.key((0,) * domain.presentation_rank)
        )
        trivial = (zero_index,)
        pending = [trivial]
        seen = {trivial}
    elif not elements_complete and (seen or pending or active is not None):
        raise ValueError("E1 checkpoint traversed subgroups before materializing elements")

    keys = {space.key(vector): index for index, vector in enumerate(element_vectors)}
    subgroup_complete = checkpoint.subgroup_search_complete
    while elements_complete and not subgroup_complete and work < budget.max_work_units:
        if active is None:
            if not pending:
                subgroup_complete = True
                break
            active = pending.pop(0)
            active_cursor = 0
        while active_cursor < len(element_vectors) and work < budget.max_work_units:
            element_index = active_cursor
            active_cursor += 1
            work += 1
            join_tests += 1
            generated = _closure(active, element_index, element_vectors, keys, space)
            if generated not in seen:
                if len(seen) >= budget.max_subgroups:
                    active_cursor -= 1
                    work = budget.max_work_units
                    break
                seen.add(generated)
                pending.append(generated)
        if active_cursor == len(element_vectors):
            active = None
            active_cursor = 0
    if elements_complete and active is None and not pending:
        subgroup_complete = True

    candidate_scan_cursor = checkpoint.candidate_scan_cursor
    candidate_transcript = list(checkpoint.candidate_transcript)
    candidate_transcript_hash = checkpoint.candidate_transcript_hash
    output_cursor = checkpoint.output_cursor
    output_prefix = list(checkpoint.output_prefix)
    output_transcript_hash = checkpoint.output_transcript_hash
    page_candidates_list = []
    output_complete = False
    if subgroup_complete:
        ordered_subgroups = tuple(sorted(seen))
        while (
            candidate_scan_cursor < len(ordered_subgroups)
            and work < budget.max_work_units
        ):
            subgroup = ordered_subgroups[candidate_scan_cursor]
            work += 1
            outcome = (
                _ISOTROPIC
                if _isotropic(subgroup, tuple(element_vectors), space)
                else _NOT_ISOTROPIC
            )
            entry = (subgroup, outcome)
            candidate_transcript.append(entry)
            candidate_transcript_hash = _candidate_transcript_step(
                candidate_transcript_hash,
                candidate_scan_cursor,
                entry,
            )
            candidate_scan_cursor += 1

        isotropic_subgroups = tuple(
            subgroup
            for subgroup, outcome in candidate_transcript
            if outcome == _ISOTROPIC
        )
        candidate_scan_complete = candidate_scan_cursor == len(ordered_subgroups)
        if not output_prefix:
            output_transcript_hash = _output_transcript_genesis(
                domain.algebra_input_hash, candidate_transcript_hash
            )
        while (
            candidate_scan_complete
            and output_cursor < len(isotropic_subgroups)
            and work < budget.max_work_units
            and len(page_candidates_list) < budget.max_results
        ):
            subgroup = isotropic_subgroups[output_cursor]
            work += 1
            candidate = _candidate_record(
                subgroup,
                isotropic_subgroups,
                tuple(element_vectors),
                paired,
                backend,
                space,
                domain.algebra_input_hash,
            )
            prefix_entry = (
                subgroup,
                canonical_hash("e1-subgroup-output-v1", candidate),
            )
            output_prefix.append(prefix_entry)
            output_transcript_hash = _output_transcript_step(
                output_transcript_hash,
                output_cursor,
                prefix_entry,
            )
            output_cursor += 1
            page_candidates_list.append(candidate)
        output_complete = (
            candidate_scan_complete
            and output_cursor == len(isotropic_subgroups)
        )
    else:
        isotropic_subgroups = ()
    page_candidates = tuple(page_candidates_list)

    exactness = (
        Exactness.CERTIFIED_EXACT
        if elements_complete and subgroup_complete and output_complete
        else Exactness.EXPERIMENTAL
    )
    verification = []
    if elements_complete:
        verification.append("distinct cosets equal the certified finite group order")
    if subgroup_complete:
        verification.append("BFS closure under adjoining every finite-group element exhausted")
    if output_complete:
        verification.append(
            "every subgroup isotropy test and every maximality record generation consumed a work unit"
        )
        verification.append(
            "candidate and output prefixes were replayed against their transcript chain hashes"
        )
        verification.append("every isotropic subgroup record was emitted exactly once")
    certificate = E1CompletenessCertificate(
        domain=domain,
        elements_complete=elements_complete,
        subgroup_search_complete=subgroup_complete,
        output_complete=output_complete,
        coordinate_tuples_scanned=element_cursor,
        distinct_elements=len(element_vectors),
        subgroup_join_tests=join_tests,
        distinct_subgroups=len(seen),
        candidate_subgroups_scanned=candidate_scan_cursor,
        isotropic_subgroups=len(isotropic_subgroups),
        output_prefix_length=len(output_prefix),
        candidate_transcript_hash=candidate_transcript_hash,
        output_transcript_hash=output_transcript_hash,
        page_work_units=work,
        exactness=exactness,
        verification=tuple(verification),
    )
    next_checkpoint = None
    if not certificate.certified_complete:
        next_checkpoint = _seal_checkpoint(E1EnumerationCheckpoint(
            algebra_input_hash=domain.algebra_input_hash,
            element_cursor=element_cursor,
            element_vectors=tuple(element_vectors),
            pending_subgroups=tuple(pending),
            seen_subgroups=tuple(sorted(seen)),
            active_subgroup=active,
            active_element_cursor=active_cursor,
            subgroup_join_tests=join_tests,
            subgroup_search_complete=subgroup_complete,
            candidate_scan_cursor=candidate_scan_cursor,
            candidate_transcript=tuple(candidate_transcript),
            candidate_transcript_hash=candidate_transcript_hash,
            output_cursor=output_cursor,
            output_prefix=tuple(output_prefix),
            output_transcript_hash=output_transcript_hash,
        ))
    return E1EnumerationPage(domain, page_candidates, next_checkpoint, certificate)


@dataclass(frozen=True)
class PhaseLiftContext:
    algebra: FiniteBoundaryAlgebra
    bulk_generators: Tuple[PauliOperator, ...]

    SCHEMA_ID = "mobility_toolkit.phase_lift_context.v1"

    def __post_init__(self) -> None:
        generators = tuple(self.bulk_generators)
        if any(operator.module != self.algebra.analysis.module for operator in generators):
            raise ValueError("phase-lift bulk generators belong to a different module")
        matrix = self.algebra.analysis.coordinates.generator_matrix(generators)
        if matrix != self.algebra.analysis.validation.generator_matrix:
            raise ValueError("phase-lift bulk generators do not match the analyzed presentation")
        object.__setattr__(self, "bulk_generators", generators)

    def to_canonical_dict(self) -> dict:
        return {
            "algebra_window": self.algebra.window.window_id,
            "bulk_generators": self.bulk_generators,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PhaseLiftCheckpoint:
    candidate_hash: str
    assignment_cursor: int = 0

    SCHEMA_ID = "mobility_toolkit.phase_lift_checkpoint.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "assignment_cursor": self.assignment_cursor,
            "candidate_hash": self.candidate_hash,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PhaseLiftCompletion:
    phases: Tuple[int, ...]
    boundary_generators: Tuple[PauliOperator, ...]
    validation: StabilizerValidation

    SCHEMA_ID = "mobility_toolkit.phase_lift_completion.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_generators": self.boundary_generators,
            "phases": self.phases,
            "schema": self.SCHEMA_ID,
            "validation": self.validation,
        }


@dataclass(frozen=True)
class PhaseLiftPage:
    completions: Tuple[PhaseLiftCompletion, ...]
    checkpoint: Optional[PhaseLiftCheckpoint]
    assignments_total: int
    assignments_tested: int
    exactness: Exactness
    theorem_scope: str = (
        "all phase assignments for this candidate generator presentation and supplied "
        "finite bulk stabilizer list only"
    )

    SCHEMA_ID = "mobility_toolkit.phase_lift_page.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "assignments_tested": self.assignments_tested,
            "assignments_total": self.assignments_total,
            "checkpoint": self.checkpoint,
            "completions": self.completions,
            "exactness": self.exactness,
            "schema": self.SCHEMA_ID,
            "theorem_scope": self.theorem_scope,
        }


def enumerate_phase_lifts(
    context: PhaseLiftContext,
    candidate: E1SubgroupCandidate,
    backend: FiniteIntegerBackend,
    budget: EnumerationBudget = EnumerationBudget(),
    checkpoint: Optional[PhaseLiftCheckpoint] = None,
) -> PhaseLiftPage:
    """Enumerate compatible scalar phases for one projective completion."""

    if not candidate.isotropic:
        raise ValueError("phase lifts require an isotropic projective subgroup")
    paired = paired_boundary_presentation(context.algebra, backend)
    expected_hash = _domain(context.algebra, paired).algebra_input_hash
    if candidate.algebra_input_hash != expected_hash:
        raise ValueError("phase-lift candidate belongs to a different boundary algebra")
    candidate_hash = canonical_hash("e1-phase-lift-candidate-v1", candidate)
    cursor = 0 if checkpoint is None else checkpoint.assignment_cursor
    if checkpoint is not None and checkpoint.candidate_hash != candidate_hash:
        raise ValueError("phase-lift checkpoint belongs to a different candidate")
    algebra = context.algebra
    quotient_vectors = _matrix_from_columns(
        candidate.generator_vectors,
        algebra.local_centralizer.preimage_lattice_basis.ncols,
    )
    ambient_vectors = algebra.local_centralizer.preimage_lattice_basis.matmul(
        quotient_vectors
    )
    projective_lifts = tuple(
        algebra.analysis.coordinates.operator(vector)
        for vector in _columns(ambient_vectors)
    )
    modulus = algebra.analysis.module.phase_modulus
    total = modulus ** len(projective_lifts)
    end = min(total, cursor + budget.max_phase_assignments)
    completions = []
    processed_end = cursor
    for assignment_index in range(cursor, end):
        phases = _digits(assignment_index, modulus, len(projective_lifts))
        lifted = tuple(
            operator.with_phase(phase)
            for operator, phase in zip(projective_lifts, phases)
        )
        validation = validate_stabilizer_generators(
            algebra.analysis.module, context.bulk_generators + lifted, backend
        )
        if validation.valid:
            completions.append(PhaseLiftCompletion(phases, lifted, validation))
        processed_end = assignment_index + 1
        if len(completions) >= budget.max_results:
            break
    complete = processed_end == total
    next_checkpoint = None if complete else PhaseLiftCheckpoint(candidate_hash, processed_end)
    return PhaseLiftPage(
        tuple(completions),
        next_checkpoint,
        total,
        processed_end,
        Exactness.CERTIFIED_EXACT if complete else Exactness.EXPERIMENTAL,
    )


@dataclass(frozen=True)
class E1Orbit:
    representative: IndexSubgroup
    members: Tuple[IndexSubgroup, ...]

    SCHEMA_ID = "mobility_toolkit.e1_orbit.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "members": self.members,
            "representative": self.representative,
            "schema": self.SCHEMA_ID,
        }


def reduce_e1_orbits(
    candidates: Sequence[E1SubgroupCandidate],
    actions: Sequence[FiniteGroupHomomorphism],
    algebra: FiniteBoundaryAlgebra,
    backend: FiniteIntegerBackend,
) -> Tuple[E1Orbit, ...]:
    """Exactly reduce a complete candidate set by explicit automorphisms."""

    paired = paired_boundary_presentation(algebra, backend)
    space = _ElementSpace(paired)
    for action in actions:
        if action.source != paired.group or action.target != paired.group:
            raise ValueError("orbit action belongs to a different finite group")
        if action.kernel(backend).order(backend) != 1:
            raise ValueError("orbit action is not an automorphism")
        if action.image(backend).order(backend) != paired.group.order(backend):
            raise ValueError("orbit action is not an automorphism")
        pulled_back = (
            action.lift_matrix.transpose()
            .matmul(paired.pairing_matrix)
            .matmul(action.lift_matrix)
        )
        difference = SparseIntMatrix(
            paired.group.presentation_rank,
            paired.group.presentation_rank,
            tuple(pulled_back.entries) + tuple(paired.pairing_matrix.negate().entries),
        )
        if any(value % paired.modulus for _, _, value in difference.entries):
            raise ValueError("orbit action does not preserve the pairing")
    # Candidate vectors collectively contain every group element only when the
    # trivial/nonisotropic elements are absent, so materialize the finite group.
    exponent = paired.group.invariant_factors[-1] if paired.group.invariant_factors else 1
    vectors = []
    keys: Dict[ElementKey, int] = {}
    for values in itertools.product(range(exponent), repeat=paired.group.presentation_rank):
        key = space.key(values)
        if key not in keys:
            keys[key] = len(vectors)
            vectors.append(tuple(values))
        if len(vectors) == paired.group.order(backend):
            break
    candidate_map = {candidate.element_indices: candidate for candidate in candidates}
    remaining = set(candidate_map)
    orbits = []
    for seed in sorted(tuple(remaining)):
        if seed not in remaining:
            continue
        orbit = {seed}
        frontier = [seed]
        while frontier:
            subgroup = frontier.pop()
            for action in actions:
                mapped = tuple(
                    sorted(
                        keys[
                            space.key(
                                tuple(
                                    row[0]
                                    for row in action.lift_matrix.matmul(
                                        _matrix_from_columns((vectors[index],), len(vectors[index]))
                                    ).to_rows()
                                )
                            )
                        ]
                        for index in subgroup
                    )
                )
                if mapped not in candidate_map:
                    raise ValueError("automorphism did not preserve the candidate family")
                if mapped not in orbit:
                    orbit.add(mapped)
                    frontier.append(mapped)
        remaining.difference_update(orbit)
        members = tuple(sorted(orbit))
        orbits.append(E1Orbit(members[0], members))
    return tuple(orbits)


__all__ = [
    "E1CompletenessCertificate",
    "E1EnumerationCheckpoint",
    "E1EnumerationPage",
    "E1Orbit",
    "E1SearchDomain",
    "E1SubgroupCandidate",
    "EnumerationBudget",
    "PhaseLiftCheckpoint",
    "PhaseLiftCompletion",
    "PhaseLiftContext",
    "PhaseLiftPage",
    "enumerate_e1_subgroups",
    "enumerate_phase_lifts",
    "paired_boundary_presentation",
    "reduce_e1_orbits",
]
