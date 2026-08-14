"""Resource-bounded exhaustive enumeration of abstract anyon condensates.

The search domain is one explicitly supplied finite metric group.  Candidates
are raw subgroups, not automorphism or Morita-equivalence orbits, and every
emitted candidate is replay-checked by :mod:`mobility_toolkit.anyons2d.condensation`.
No local commuting-projector completion is constructed or implied.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, Optional, Sequence, Tuple

from sympy import Matrix as SympyMatrix

from mobility_toolkit.anyons2d.condensation import (
    CondensationCertificate,
    test_condensation,
)
from mobility_toolkit.anyons2d.metric import FiniteMetricGroup
from mobility_toolkit.core import Exactness, SparseIntMatrix
from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.finite import FiniteIntegerBackend, FiniteSubgroup


ElementKey = Tuple[Tuple[int, int], ...]
IndexSubgroup = Tuple[int, ...]
CandidateTranscriptEntry = Tuple[IndexSubgroup, str, str]
OutputPrefixEntry = Tuple[IndexSubgroup, str]

_NOT_BOSONIC = "not_bosonic"
_BOSONIC = "bosonic"
_LAGRANGIAN = "lagrangian"
_TRANSCRIPT_OUTCOMES = frozenset((_NOT_BOSONIC, _BOSONIC, _LAGRANGIAN))


def _positive(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _digits(index: int, base: int, length: int) -> Tuple[int, ...]:
    result = []
    for _ in range(length):
        result.append(index % base)
        index //= base
    return tuple(result)


def _matrix_from_columns(
    columns: Sequence[Sequence[int]], nrows: int
) -> SparseIntMatrix:
    materialized = tuple(tuple(column) for column in columns)
    return SparseIntMatrix(
        nrows,
        len(materialized),
        tuple(
            (row, column_index, value)
            for column_index, column in enumerate(materialized)
            for row, value in enumerate(column)
            if value
        ),
    )


@dataclass(frozen=True)
class CondensateEnumerationBudget:
    max_work_units: int = 100_000
    max_results: int = 1_000
    max_elements: int = 4_096
    max_subgroups: int = 100_000

    SCHEMA_ID = "mobility_toolkit.condensate_enumeration_budget.v1"

    def __post_init__(self) -> None:
        _positive(self.max_work_units, "max_work_units")
        _positive(self.max_results, "max_results")
        _positive(self.max_elements, "max_elements")
        _positive(self.max_subgroups, "max_subgroups")

    def to_canonical_dict(self) -> dict:
        return {
            "max_elements": self.max_elements,
            "max_results": self.max_results,
            "max_subgroups": self.max_subgroups,
            "max_work_units": self.max_work_units,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class CondensateSearchDomain:
    metric_hash: str
    invariant_factors: Tuple[int, ...]
    group_order: int
    exponent: int
    presentation_rank: int
    phase_modulus: int
    equivalence_relation: str = "raw_subgroups"
    candidate_definition: str = (
        "all subgroups on which the quadratic refinement vanishes; Lagrangian "
        "means equality with the symmetric-monodromy orthogonal complement"
    )

    SCHEMA_ID = "mobility_toolkit.condensate_search_domain.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidate_definition": self.candidate_definition,
            "equivalence_relation": self.equivalence_relation,
            "exponent": self.exponent,
            "group_order": self.group_order,
            "invariant_factors": self.invariant_factors,
            "metric_hash": self.metric_hash,
            "phase_modulus": self.phase_modulus,
            "presentation_rank": self.presentation_rank,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class CondensateEnumerationCheckpoint:
    metric_hash: str
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
    output_cursor: int = 0
    output_prefix: Tuple[OutputPrefixEntry, ...] = ()
    output_transcript_hash: str = ""

    SCHEMA_ID = "mobility_toolkit.condensate_enumeration_checkpoint.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "active_element_cursor": self.active_element_cursor,
            "active_subgroup": self.active_subgroup,
            "candidate_scan_cursor": self.candidate_scan_cursor,
            "candidate_transcript": self.candidate_transcript,
            "element_cursor": self.element_cursor,
            "element_vectors": self.element_vectors,
            "metric_hash": self.metric_hash,
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
class CondensateCandidate:
    metric_hash: str
    element_indices: IndexSubgroup
    generator_indices: Tuple[int, ...]
    generator_vectors: Tuple[Tuple[int, ...], ...]
    subgroup: FiniteSubgroup
    invariant_factors: Tuple[int, ...]
    condensation: CondensationCertificate

    SCHEMA_ID = "mobility_toolkit.condensate_candidate.v1"

    @property
    def order(self) -> int:
        return len(self.element_indices)

    @property
    def lagrangian(self) -> bool:
        return self.condensation.lagrangian

    def to_canonical_dict(self) -> dict:
        return {
            "condensation": self.condensation,
            "element_indices": self.element_indices,
            "generator_indices": self.generator_indices,
            "generator_vectors": self.generator_vectors,
            "invariant_factors": self.invariant_factors,
            "lagrangian": self.lagrangian,
            "metric_hash": self.metric_hash,
            "order": self.order,
            "schema": self.SCHEMA_ID,
            "subgroup": self.subgroup,
        }


@dataclass(frozen=True)
class CondensateCompletenessCertificate:
    domain: CondensateSearchDomain
    elements_complete: bool
    subgroup_search_complete: bool
    output_complete: bool
    coordinate_tuples_scanned: int
    distinct_elements: int
    subgroup_join_tests: int
    distinct_subgroups: int
    candidate_subgroups_scanned: int
    bosonic_subgroups: int
    lagrangian_subgroups: int
    output_prefix_length: int
    output_transcript_hash: str
    page_work_units: int
    exactness: Exactness
    verification: Tuple[str, ...]
    limit_reason: Optional[str] = None
    theorem_scope: str = (
        "exhaustion of raw subgroups of the recorded abstract finite metric group; "
        "no quotient by automorphisms and no local Hamiltonian completion"
    )

    SCHEMA_ID = "mobility_toolkit.condensate_completeness_certificate.v2"

    @property
    def certified_complete(self) -> bool:
        return self.elements_complete and self.subgroup_search_complete and self.output_complete

    def to_canonical_dict(self) -> dict:
        return {
            "bosonic_subgroups": self.bosonic_subgroups,
            "certified_complete": self.certified_complete,
            "coordinate_tuples_scanned": self.coordinate_tuples_scanned,
            "candidate_subgroups_scanned": self.candidate_subgroups_scanned,
            "distinct_elements": self.distinct_elements,
            "distinct_subgroups": self.distinct_subgroups,
            "domain": self.domain,
            "elements_complete": self.elements_complete,
            "exactness": self.exactness,
            "lagrangian_subgroups": self.lagrangian_subgroups,
            "limit_reason": self.limit_reason,
            "output_prefix_length": self.output_prefix_length,
            "output_transcript_hash": self.output_transcript_hash,
            "output_complete": self.output_complete,
            "page_work_units": self.page_work_units,
            "schema": self.SCHEMA_ID,
            "subgroup_join_tests": self.subgroup_join_tests,
            "subgroup_search_complete": self.subgroup_search_complete,
            "theorem_scope": self.theorem_scope,
            "verification": self.verification,
        }


@dataclass(frozen=True)
class CondensateEnumerationPage:
    domain: CondensateSearchDomain
    candidates: Tuple[CondensateCandidate, ...]
    checkpoint: Optional[CondensateEnumerationCheckpoint]
    certificate: CondensateCompletenessCertificate

    SCHEMA_ID = "mobility_toolkit.condensate_enumeration_page.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidates": self.candidates,
            "certificate": self.certificate,
            "checkpoint": self.checkpoint,
            "domain": self.domain,
            "schema": self.SCHEMA_ID,
        }


class _ElementSpace:
    def __init__(self, metric: FiniteMetricGroup) -> None:
        rows = metric.group.relation_lattice_basis.to_rows()
        self.metric = metric
        self._inverse = SympyMatrix(rows).inv() if rows else SympyMatrix.zeros(0, 0)
        # Pre-convert _inverse to a list of lists of (p, q) integers for fast pure-Python math
        self._fast_inverse = []
        for i in range(self._inverse.rows):
            row = []
            for j in range(self._inverse.cols):
                val = self._inverse[i, j]
                row.append((int(val.p), int(val.q)))
            self._fast_inverse.append(row)

    def key(self, vector: Sequence[int]) -> ElementKey:
        if not vector:
            return ()

        # Fast pure-Python matrix-vector multiplication with rationals
        result = []
        for row in self._fast_inverse:
            sum_num = 0
            sum_den = 1
            for (p, q), v in zip(row, vector):
                if v == 0 or p == 0:
                    continue
                num = p * v
                den = q

                if sum_den == den:
                    sum_num += num
                else:
                    sum_num = sum_num * den + num * sum_den
                    sum_den = sum_den * den

            if sum_den == 1:
                result.append((0, 1))
            else:
                g = math.gcd(sum_num, sum_den)
                if g > 1:
                    sum_num //= g
                    sum_den //= g

                if sum_den == 1:
                    result.append((0, 1))
                else:
                    num = sum_num % sum_den
                    result.append((num, sum_den))
        return tuple(result)


def _domain(metric: FiniteMetricGroup, backend: FiniteIntegerBackend) -> CondensateSearchDomain:
    order = metric.group.order(backend)
    exponent = metric.group.invariant_factors[-1] if metric.group.invariant_factors else 1
    return CondensateSearchDomain(
        canonical_hash("finite-metric-condensates-v1", metric),
        metric.group.invariant_factors,
        order,
        exponent,
        metric.group.presentation_rank,
        metric.phase_modulus,
    )


def _closure(
    subgroup: IndexSubgroup,
    element_index: int,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> IndexSubgroup:
    if element_index in subgroup:
        return subgroup
    rank = len(vectors[0]) if vectors else 0
    zero_key = space.key((0,) * rank)
    cyclic = [keys[zero_key]]
    current = vectors[element_index]
    while space.key(current) != zero_key:
        cyclic.append(keys[space.key(current)])
        current = tuple(
            current[index] + vectors[element_index][index] for index in range(rank)
        )
    members = set()
    for left_index in subgroup:
        for right_index in cyclic:
            total = tuple(
                vectors[left_index][index] + vectors[right_index][index]
                for index in range(rank)
            )
            members.add(keys[space.key(total)])
    return tuple(sorted(members))


def _canonical_generators(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> Tuple[int, ...]:
    rank = len(vectors[0]) if vectors else 0
    generated: IndexSubgroup = (keys[space.key((0,) * rank)],)
    result = []
    for index in subgroup:
        if index in generated:
            continue
        result.append(index)
        generated = _closure(generated, index, vectors, keys, space)
        if generated == subgroup:
            break
    return tuple(result)


def _verify_subgroup_family(
    subgroups: Sequence[IndexSubgroup],
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
    require_exhaustive: bool,
) -> None:
    family = set(subgroups)
    zero = keys[space.key((0,) * (len(vectors[0]) if vectors else 0))]
    if (zero,) not in family:
        raise ArithmeticError("subgroup search state omits the trivial subgroup")
    for subgroup in family:
        if tuple(sorted(set(subgroup))) != subgroup or zero not in subgroup:
            raise ArithmeticError("subgroup search state contains a malformed subgroup")
        if any(index < 0 or index >= len(vectors) for index in subgroup):
            raise ArithmeticError("subgroup search state has an invalid element index")
        member_set = set(subgroup)
        rank = len(vectors[0]) if vectors else 0
        for left in subgroup:
            for right in subgroup:
                total = tuple(
                    vectors[left][axis] + vectors[right][axis] for axis in range(rank)
                )
                if keys[space.key(total)] not in member_set:
                    raise ArithmeticError("subgroup search state contains a non-subgroup")
        if require_exhaustive:
            for index in range(len(vectors)):
                if _closure(subgroup, index, vectors, keys, space) not in family:
                    raise ArithmeticError("claimed subgroup exhaustion is incomplete")


def _candidate_record(
    member_indices: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
    metric: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
    metric_hash: str,
) -> Optional[CondensateCandidate]:
    generators = _canonical_generators(member_indices, vectors, keys, space)
    generator_vectors = tuple(vectors[index] for index in generators)
    subgroup = metric.group.subgroup(
        _matrix_from_columns(generator_vectors, metric.group.presentation_rank),
        backend,
    )
    condensation = test_condensation(metric, subgroup, backend)
    if not condensation.bosonic:
        return None
    return CondensateCandidate(
        metric_hash,
        member_indices,
        generators,
        generator_vectors,
        subgroup,
        subgroup.invariant_factors(backend),
        condensation,
    )


def _transcript_genesis(metric_hash: str) -> str:
    return canonical_hash(
        "condensate-output-transcript-genesis-v1",
        {"metric_hash": metric_hash},
    )


def _transcript_step(
    previous_hash: str,
    scan_index: int,
    entry: CandidateTranscriptEntry,
) -> str:
    subgroup, outcome, candidate_hash = entry
    return canonical_hash(
        "condensate-output-transcript-step-v1",
        {
            "candidate_hash": candidate_hash,
            "outcome": outcome,
            "previous_hash": previous_hash,
            "scan_index": scan_index,
            "subgroup": subgroup,
        },
    )


def _replay_transcript_hash(
    metric_hash: str,
    transcript: Sequence[CandidateTranscriptEntry],
) -> str:
    digest = _transcript_genesis(metric_hash)
    for scan_index, entry in enumerate(transcript):
        digest = _transcript_step(digest, scan_index, entry)
    return digest


def _transcript_entry(
    subgroup: IndexSubgroup,
    candidate: Optional[CondensateCandidate],
) -> CandidateTranscriptEntry:
    if candidate is None:
        return (subgroup, _NOT_BOSONIC, "")
    outcome = _LAGRANGIAN if candidate.lagrangian else _BOSONIC
    return (
        subgroup,
        outcome,
        canonical_hash("condensate-candidate-output-v1", candidate),
    )


def _output_prefix_from_transcript(
    transcript: Sequence[CandidateTranscriptEntry],
) -> Tuple[OutputPrefixEntry, ...]:
    return tuple(
        (subgroup, candidate_hash)
        for subgroup, outcome, candidate_hash in transcript
        if outcome != _NOT_BOSONIC
    )


def _validate_checkpoint(
    checkpoint: CondensateEnumerationCheckpoint,
    domain: CondensateSearchDomain,
) -> None:
    if checkpoint.metric_hash != domain.metric_hash:
        raise ValueError("condensate checkpoint belongs to a different metric group")
    scalar_fields = (
        checkpoint.element_cursor,
        checkpoint.active_element_cursor,
        checkpoint.subgroup_join_tests,
        checkpoint.candidate_scan_cursor,
        checkpoint.output_cursor,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in scalar_fields):
        raise ValueError("condensate checkpoint has an invalid cursor")
    if any(len(vector) != domain.presentation_rank for vector in checkpoint.element_vectors):
        raise ValueError("condensate checkpoint has an invalid element vector")
    if checkpoint.active_element_cursor > len(checkpoint.element_vectors):
        raise ValueError("condensate checkpoint active cursor is out of range")
    if checkpoint.subgroup_search_complete and (
        checkpoint.pending_subgroups or checkpoint.active_subgroup is not None
    ):
        raise ValueError("completed condensate checkpoint still has pending work")
    if not checkpoint.subgroup_search_complete and (
        checkpoint.candidate_scan_cursor
        or checkpoint.candidate_transcript
        or checkpoint.output_cursor
        or checkpoint.output_prefix
    ):
        raise ValueError("condensate checkpoint scanned output before search completion")
    if len(set(checkpoint.seen_subgroups)) != len(checkpoint.seen_subgroups):
        raise ValueError("condensate checkpoint repeats a seen subgroup")
    if len(set(checkpoint.pending_subgroups)) != len(checkpoint.pending_subgroups):
        raise ValueError("condensate checkpoint repeats pending work")
    seen = set(checkpoint.seen_subgroups)
    if any(subgroup not in seen for subgroup in checkpoint.pending_subgroups):
        raise ValueError("condensate checkpoint has unseen pending work")
    if checkpoint.active_subgroup is not None and checkpoint.active_subgroup not in seen:
        raise ValueError("condensate checkpoint has an unseen active subgroup")
    if checkpoint.candidate_scan_cursor > len(seen):
        raise ValueError("condensate checkpoint candidate cursor is out of range")
    if len(checkpoint.candidate_transcript) != checkpoint.candidate_scan_cursor:
        raise ValueError("condensate checkpoint transcript length disagrees with its cursor")
    expected_subgroups = tuple(sorted(seen))[: checkpoint.candidate_scan_cursor]
    transcript_subgroups = []
    for entry in checkpoint.candidate_transcript:
        if not isinstance(entry, tuple) or len(entry) != 3:
            raise ValueError("condensate checkpoint has a malformed transcript entry")
        subgroup, outcome, candidate_hash = entry
        transcript_subgroups.append(subgroup)
        if outcome not in _TRANSCRIPT_OUTCOMES:
            raise ValueError("condensate checkpoint has an invalid transcript outcome")
        if outcome == _NOT_BOSONIC and candidate_hash:
            raise ValueError("non-bosonic transcript entry carries an output hash")
        if outcome != _NOT_BOSONIC and not candidate_hash:
            raise ValueError("bosonic transcript entry omits its output hash")
    if tuple(transcript_subgroups) != expected_subgroups:
        raise ValueError("condensate checkpoint transcript does not match its scan prefix")
    expected_output_prefix = _output_prefix_from_transcript(
        checkpoint.candidate_transcript
    )
    if checkpoint.output_prefix != expected_output_prefix:
        raise ValueError("condensate checkpoint output prefix does not match its transcript")
    if checkpoint.output_cursor != len(expected_output_prefix):
        raise ValueError("condensate checkpoint output cursor does not match its prefix")
    expected_hash = _replay_transcript_hash(
        domain.metric_hash, checkpoint.candidate_transcript
    )
    if checkpoint.output_transcript_hash:
        if checkpoint.output_transcript_hash != expected_hash:
            raise ValueError("condensate checkpoint output transcript hash is invalid")
    elif checkpoint.candidate_transcript:
        raise ValueError("condensate checkpoint omits its output transcript hash")


def enumerate_condensates(
    metric: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
    budget: CondensateEnumerationBudget = CondensateEnumerationBudget(),
    checkpoint: Optional[CondensateEnumerationCheckpoint] = None,
) -> CondensateEnumerationPage:
    """Return one page of every raw bosonic subgroup of ``metric``.

    Passing the returned checkpoint resumes the exact BFS.  A page is certified
    complete only after all finite-group elements, all raw subgroups, and all
    candidate output pages have been exhausted.
    """

    domain = _domain(metric, backend)
    if checkpoint is None:
        checkpoint = CondensateEnumerationCheckpoint(domain.metric_hash)
    _validate_checkpoint(checkpoint, domain)

    if domain.group_order > budget.max_elements:
        transcript_hash = (
            checkpoint.output_transcript_hash
            or _transcript_genesis(domain.metric_hash)
        )
        checkpoint = replace(
            checkpoint, output_transcript_hash=transcript_hash
        )
        certificate = CondensateCompletenessCertificate(
            domain=domain,
            elements_complete=False,
            subgroup_search_complete=False,
            output_complete=False,
            coordinate_tuples_scanned=checkpoint.element_cursor,
            distinct_elements=len(checkpoint.element_vectors),
            subgroup_join_tests=checkpoint.subgroup_join_tests,
            distinct_subgroups=len(checkpoint.seen_subgroups),
            candidate_subgroups_scanned=checkpoint.candidate_scan_cursor,
            bosonic_subgroups=len(checkpoint.output_prefix),
            lagrangian_subgroups=sum(
                outcome == _LAGRANGIAN
                for _, outcome, _ in checkpoint.candidate_transcript
            ),
            output_prefix_length=len(checkpoint.output_prefix),
            output_transcript_hash=transcript_hash,
            page_work_units=0,
            exactness=Exactness.EXPERIMENTAL,
            verification=(),
            limit_reason=f"group order exceeds max_elements={budget.max_elements}",
        )
        return CondensateEnumerationPage(domain, (), checkpoint, certificate)

    space = _ElementSpace(metric)
    element_vectors = list(checkpoint.element_vectors)
    known_keys = {space.key(vector) for vector in element_vectors}
    if len(known_keys) != len(element_vectors):
        raise ValueError("condensate checkpoint repeats a finite-group element")
    element_cursor = checkpoint.element_cursor
    coordinate_limit = domain.exponent ** domain.presentation_rank
    if element_cursor > coordinate_limit:
        raise ValueError("condensate checkpoint element cursor is out of range")
    work = 0
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
        raise ArithmeticError("finite-group element materialization contradicts its order")

    pending = list(checkpoint.pending_subgroups)
    seen = set(checkpoint.seen_subgroups)
    active = checkpoint.active_subgroup
    active_cursor = checkpoint.active_element_cursor
    join_tests = checkpoint.subgroup_join_tests
    subgroup_complete = checkpoint.subgroup_search_complete
    if elements_complete:
        keys = {space.key(vector): index for index, vector in enumerate(element_vectors)}
        if not seen:
            trivial = (keys[space.key((0,) * domain.presentation_rank)],)
            pending = [trivial]
            seen = {trivial}
        _verify_subgroup_family(tuple(seen), element_vectors, keys, space, False)
    else:
        keys = {}
        if seen or pending or active is not None:
            raise ValueError("checkpoint started subgroup traversal before elements completed")

    hit_subgroup_limit = False
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
                    hit_subgroup_limit = True
                    work = budget.max_work_units
                    break
                seen.add(generated)
                pending.append(generated)
        if active_cursor == len(element_vectors):
            active = None
            active_cursor = 0
    if elements_complete and active is None and not pending:
        subgroup_complete = True
    if subgroup_complete:
        _verify_subgroup_family(tuple(seen), element_vectors, keys, space, True)

    scan_cursor = checkpoint.candidate_scan_cursor
    transcript = list(checkpoint.candidate_transcript)
    output_prefix = list(checkpoint.output_prefix)
    transcript_hash = (
        checkpoint.output_transcript_hash
        or _transcript_genesis(domain.metric_hash)
    )
    output_cursor = checkpoint.output_cursor
    page_candidates_list = []
    output_complete = False
    if subgroup_complete:
        ordered_subgroups = tuple(sorted(seen))
        if scan_cursor > len(ordered_subgroups):
            raise ValueError("condensate checkpoint candidate cursor is out of range")
        while (
            scan_cursor < len(ordered_subgroups)
            and work < budget.max_work_units
            and len(page_candidates_list) < budget.max_results
        ):
            member_indices = ordered_subgroups[scan_cursor]
            work += 1
            candidate = _candidate_record(
                member_indices,
                tuple(element_vectors),
                keys,
                space,
                metric,
                backend,
                domain.metric_hash,
            )
            entry = _transcript_entry(member_indices, candidate)
            transcript.append(entry)
            transcript_hash = _transcript_step(
                transcript_hash, scan_cursor, entry
            )
            scan_cursor += 1
            if candidate is not None:
                page_candidates_list.append(candidate)
                output_prefix.append((member_indices, entry[2]))
                output_cursor += 1
        output_complete = scan_cursor == len(ordered_subgroups)
    page_candidates = tuple(page_candidates_list)

    complete = elements_complete and subgroup_complete and output_complete
    verification = []
    if elements_complete:
        verification.append("distinct quotient cosets equal the exact finite-group order")
    if subgroup_complete:
        verification.append(
            "the subgroup family contains the trivial subgroup and is closed under adjoining every group element"
        )
    if output_complete:
        verification.append(
            "every subgroup was scanned exactly once and every emitted candidate was checked by its quadratic condensation certificate"
        )
        verification.append(
            "the output prefix and scan cursor are committed by the replayed transcript chain hash"
        )
        verification.append("every raw bosonic subgroup record was emitted across the checkpoint sequence")
    limit_reason = None
    if not elements_complete and work >= budget.max_work_units:
        limit_reason = f"page reached max_work_units={budget.max_work_units}"
    elif hit_subgroup_limit:
        limit_reason = f"subgroup state reached max_subgroups={budget.max_subgroups}"
    elif not subgroup_complete and work >= budget.max_work_units:
        limit_reason = f"page reached max_work_units={budget.max_work_units}"
    elif subgroup_complete and not output_complete and work >= budget.max_work_units:
        limit_reason = f"page reached max_work_units={budget.max_work_units}"
    elif subgroup_complete and not output_complete:
        limit_reason = f"page reached max_results={budget.max_results}"
    lagrangian_count = sum(
        outcome == _LAGRANGIAN for _, outcome, _ in transcript
    )
    certificate = CondensateCompletenessCertificate(
        domain=domain,
        elements_complete=elements_complete,
        subgroup_search_complete=subgroup_complete,
        output_complete=output_complete,
        coordinate_tuples_scanned=element_cursor,
        distinct_elements=len(element_vectors),
        subgroup_join_tests=join_tests,
        distinct_subgroups=len(seen),
        candidate_subgroups_scanned=scan_cursor,
        bosonic_subgroups=len(output_prefix),
        lagrangian_subgroups=lagrangian_count,
        output_prefix_length=len(output_prefix),
        output_transcript_hash=transcript_hash,
        page_work_units=work,
        exactness=Exactness.CERTIFIED_EXACT if complete else Exactness.EXPERIMENTAL,
        verification=tuple(verification),
        limit_reason=limit_reason,
    )
    next_checkpoint = None
    if not complete:
        next_checkpoint = CondensateEnumerationCheckpoint(
            metric_hash=domain.metric_hash,
            element_cursor=element_cursor,
            element_vectors=tuple(element_vectors),
            pending_subgroups=tuple(pending),
            seen_subgroups=tuple(sorted(seen)),
            active_subgroup=active,
            active_element_cursor=active_cursor,
            subgroup_join_tests=join_tests,
            subgroup_search_complete=subgroup_complete,
            candidate_scan_cursor=scan_cursor,
            candidate_transcript=tuple(transcript),
            output_cursor=output_cursor,
            output_prefix=tuple(output_prefix),
            output_transcript_hash=transcript_hash,
        )
    return CondensateEnumerationPage(
        domain, page_candidates, next_checkpoint, certificate
    )


__all__ = [
    "CondensateCandidate",
    "CondensateCompletenessCertificate",
    "CondensateEnumerationBudget",
    "CondensateEnumerationCheckpoint",
    "CondensateEnumerationPage",
    "CondensateSearchDomain",
    "enumerate_condensates",
]
